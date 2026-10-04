"""メールPDFの解析結果をSQLite(FTS5)にキャッシュし、全文検索を提供する。

PDFと同じフォルダに "<pdf名>.index.sqlite3" を作成する。
PDFのサイズ・更新日時が変わっていれば再構築する。
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass

import pymupdf

from .parser import extract_document_sections, extract_mails

MAIL_INDEX_VERSION = "4"
DOCUMENT_INDEX_VERSION = "3"

SCHEMA = """
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE mails (
    id INTEGER PRIMARY KEY,
    raw_title TEXT,
    subject TEXT,
    sender TEXT,
    sender_short TEXT,
    to_addr TEXT,
    cc TEXT,
    attachments TEXT,
    attachments_json TEXT,
    received_at TEXT,
    sent_at TEXT,
    title_datetime TEXT,
    start_page INTEGER,
    end_page INTEGER,
    body_text TEXT,
    body_indexed INTEGER NOT NULL DEFAULT 0,
    preview TEXT,
    is_read INTEGER NOT NULL DEFAULT 0,
    toc_index INTEGER,
    parent_toc_index INTEGER,
    level INTEGER NOT NULL DEFAULT 1,
    is_mail INTEGER NOT NULL DEFAULT 1
);

CREATE VIRTUAL TABLE mails_fts USING fts5(
    subject, sender, to_addr, cc, attachments, body_text,
    content='mails', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER mails_ai AFTER INSERT ON mails BEGIN
    INSERT INTO mails_fts(rowid, subject, sender, to_addr, cc, attachments, body_text)
    VALUES (new.id, new.subject, new.sender, new.to_addr, new.cc, new.attachments, new.body_text);
END;
CREATE TRIGGER mails_au AFTER UPDATE OF body_text ON mails BEGIN
    INSERT INTO mails_fts(mails_fts, rowid, subject, sender, to_addr, cc, attachments, body_text)
    VALUES ('delete', old.id, old.subject, old.sender, old.to_addr, old.cc, old.attachments, old.body_text);
    INSERT INTO mails_fts(rowid, subject, sender, to_addr, cc, attachments, body_text)
    VALUES (new.id, new.subject, new.sender, new.to_addr, new.cc, new.attachments, new.body_text);
END;
"""

SCHEMA_DOCUMENT = """
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE sections (
    id INTEGER PRIMARY KEY,
    parent_id INTEGER,
    level INTEGER,
    title TEXT,
    path_titles TEXT,
    start_page INTEGER,
    end_page INTEGER,
    body_text TEXT,
    body_indexed INTEGER NOT NULL DEFAULT 0,
    color_hex TEXT
);

CREATE VIRTUAL TABLE sections_fts USING fts5(
    title, body_text,
    content='sections', content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER sections_ai AFTER INSERT ON sections BEGIN
    INSERT INTO sections_fts(rowid, title, body_text)
    VALUES (new.id, new.title, new.body_text);
END;
CREATE TRIGGER sections_au AFTER UPDATE OF body_text ON sections BEGIN
    INSERT INTO sections_fts(sections_fts, rowid, title, body_text)
    VALUES ('delete', old.id, old.title, old.body_text);
    INSERT INTO sections_fts(rowid, title, body_text)
    VALUES (new.id, new.title, new.body_text);
END;
"""


def index_path_for(pdf_path: str, mode: str = "mail") -> str:
    suffix = ".document.index.sqlite3" if mode == "document" else ".index.sqlite3"
    return pdf_path + suffix


def _pdf_signature(pdf_path: str) -> str:
    st = os.stat(pdf_path)
    return f"{st.st_size}:{int(st.st_mtime)}"


def preserve_note_save_indexes(source, destination, old_pdf):
    """Annotation-only saves do not change text, scope, read flags or FTS rows."""
    old_signature = f"{old_pdf['size']}:{old_pdf['mtime_ns'] // 1_000_000_000}"
    for mode in ("mail", "document"):
        original = index_path_for(source, mode)
        target = index_path_for(destination, mode)
        if not os.path.isfile(original):
            continue
        with closing(sqlite3.connect(original)) as connection:
            row = connection.execute("SELECT value FROM meta WHERE key='pdf_signature'").fetchone()
            if not row or row[0] != old_signature:
                continue
            if os.path.normcase(os.path.realpath(source)) != os.path.normcase(os.path.realpath(destination)):
                # SQLite backup also handles any committed WAL pages.
                with closing(sqlite3.connect(target)) as saved:
                    connection.backup(saved)
        with closing(sqlite3.connect(target)) as connection:
            with connection:
                connection.execute("UPDATE meta SET value=? WHERE key='pdf_signature'", (_pdf_signature(destination),))


def _existing_read_ids(db_path: str) -> set[int]:
    """再構築前に既読状態を退避する(同じPDFのしおり構成が変わらなければidが一致するため)。"""
    if not os.path.exists(db_path):
        return set()
    try:
        conn = sqlite3.connect(db_path)
        try:
            rows = conn.execute("SELECT id FROM mails WHERE is_read=1").fetchall()
        finally:
            conn.close()
        return {r[0] for r in rows}
    except sqlite3.DatabaseError:
        return set()


def _build(pdf_path: str, db_path: str, include_body: bool = True) -> None:
    read_ids = _existing_read_ids(db_path)
    if os.path.exists(db_path):
        os.remove(db_path)

    mails = extract_mails(pdf_path, include_body=include_body)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        with conn:
            conn.execute("INSERT INTO meta(key, value) VALUES ('pdf_signature', ?)",
                         (_pdf_signature(pdf_path),))
            conn.execute("INSERT INTO meta(key, value) VALUES ('mode', 'mail')")
            conn.execute("INSERT INTO meta(key, value) VALUES ('body_complete', ?)",
                         ("1" if include_body else "0",))
            conn.execute("INSERT INTO meta(key, value) VALUES ('parser_version', ?)",
                         (MAIL_INDEX_VERSION,))
            conn.executemany(
                """INSERT INTO mails
                   (id, raw_title, subject, sender, sender_short, to_addr, cc, attachments, attachments_json,
                    received_at, sent_at, title_datetime, start_page, end_page, body_text, preview, is_read,
                    toc_index, parent_toc_index, level, is_mail)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (
                        m.index, m.raw_title, m.subject, m.sender, m.sender_short, m.to, m.cc,
                        " / ".join(a.name for a in m.attachments),
                        json.dumps([{"name": a.name, "start_page": a.start_page, "end_page": a.end_page}
                                    for a in m.attachments]),
                        m.received_at, m.sent_at,
                        m.sent_date_from_title.isoformat() if m.sent_date_from_title else "",
                        m.start_page, m.end_page, m.body_text, m.preview,
                        1 if m.index in read_ids else 0,
                        getattr(m, "toc_index", m.index), getattr(m, "parent_toc_index", None),
                        getattr(m, "level", 1), 1 if getattr(m, "is_mail", True) else 0,
                    )
                    for m in mails
                ],
            )
            if include_body:
                conn.execute("UPDATE mails SET body_indexed=1")
    finally:
        conn.close()


def _build_document(pdf_path: str, db_path: str, include_body: bool = True) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)

    sections = extract_document_sections(pdf_path, include_body=include_body)

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_DOCUMENT)
        with conn:
            conn.execute("INSERT INTO meta(key, value) VALUES ('pdf_signature', ?)",
                         (_pdf_signature(pdf_path),))
            conn.execute("INSERT INTO meta(key, value) VALUES ('mode', 'document')")
            conn.execute("INSERT INTO meta(key, value) VALUES ('body_complete', ?)",
                         ("1" if include_body else "0",))
            conn.execute("INSERT INTO meta(key, value) VALUES ('parser_version', ?)",
                         (DOCUMENT_INDEX_VERSION,))
            conn.executemany(
                """INSERT INTO sections
                   (id, parent_id, level, title, path_titles, start_page, end_page, body_text, color_hex)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    (s.index, s.parent_index, s.level, s.title, s.path_titles,
                     s.start_page, s.end_page, s.body_text, s.color_hex)
                    for s in sections
                ],
            )
            if include_body:
                conn.execute("UPDATE sections SET body_indexed=1")
    finally:
        conn.close()


def open_or_build(pdf_path: str, mode: str = "mail", force_rebuild: bool = False,
                  defer_body: bool = False) -> str:
    """インデックスDBのパスを返す。必要なら(再)構築する。

    mode は "mail"(メール束PDF) か "document"(一般資料PDF、しおり階層閲覧)。
    既存インデックスのmode・PDF署名がずれていれば自動的に再構築する。
    """
    db_path = index_path_for(pdf_path, mode)
    sig = _pdf_signature(pdf_path)
    builder = _build if mode == "mail" else _build_document

    if force_rebuild or not os.path.exists(db_path):
        builder(pdf_path, db_path, include_body=not defer_body)
        return db_path

    try:
        conn = sqlite3.connect(db_path)
        try:
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
            if (meta.get("pdf_signature") != sig or meta.get("mode", "mail") != mode
                    or (mode == "mail" and meta.get("parser_version") != MAIL_INDEX_VERSION)
                    or (mode == "document" and meta.get("parser_version") != DOCUMENT_INDEX_VERSION)):
                conn.close()
                builder(pdf_path, db_path, include_body=not defer_body)
                return db_path
            if mode == "mail":
                _migrate_is_read_column(conn)
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        builder(pdf_path, db_path, include_body=not defer_body)

    if not defer_body and not body_index_complete(db_path):
        complete_body_index(pdf_path, db_path, mode)
    return db_path


def _migrate_is_read_column(conn: sqlite3.Connection) -> None:
    """is_read列導入前(2026-09以前)に作成されたインデックスDBへ列を追加する。"""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(mails)")}
    if "is_read" not in columns:
        with conn:
            conn.execute("ALTER TABLE mails ADD COLUMN is_read INTEGER NOT NULL DEFAULT 0")


def body_index_complete(db_path: str) -> bool:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key='body_complete'").fetchone()
        return bool(row and row[0] == "1")


def mail_body_indexed(db_path: str, mail_id: int) -> bool:
    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute("SELECT body_indexed FROM mails WHERE id=?", (mail_id,)).fetchone()
        return bool(row and row[0])


def complete_body_index(pdf_path: str, db_path: str, mode: str, progress=None, only_row_id=None):
    """Fill pending rows in small commits without overwriting read state.

    Runs in an isolated process in the Viewer; interrupted jobs resume pending rows.
    """
    from . import parser
    table = "mails" if mode == "mail" else "sections"
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        signature = _pdf_signature(pdf_path)
        saved = conn.execute("SELECT value FROM meta WHERE key='pdf_signature'").fetchone()
        if not saved or saved[0] != signature:
            raise ValueError("PDFが更新されたため索引を再作成してください")
        rows = conn.execute(f"SELECT id, start_page, end_page FROM {table} WHERE body_indexed=0 ORDER BY id").fetchall()
        total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        done = total - len(rows)
        if only_row_id is not None:
            rows = [row for row in rows if row[0] == only_row_id]
        with pymupdf.open(pdf_path) as document:
            if mode == "mail":
                nodes = {}
                def collect(node):
                    nodes[node.toc_index] = node
                    for child in node.children:
                        collect(child)
                for root in parser.build_toc_tree(document):
                    collect(root)
                details = dict((row[0], row[1:]) for row in conn.execute(
                    "SELECT id, toc_index, is_mail FROM mails"))
            else:
                parent_ids = {row[0] for row in conn.execute("SELECT DISTINCT parent_id FROM sections WHERE parent_id IS NOT NULL")}
            for row_id, start, end in rows:
                skip = False
                if mode == "mail":
                    toc_index, is_mail = details[row_id]
                    node = nodes.get(toc_index)
                    body = parser._find_child(node, "本文") if node and is_mail else None
                    if body:
                        start, end = body.start_page, body.end_page
                    skip = bool(not is_mail and node and node.children)
                else:
                    skip = row_id in parent_ids
                text = "" if skip else "\n".join(document[number - 1].get_text()
                    for number in range(max(1, start), min(document.page_count, end) + 1))
                with conn:
                    if mode == "mail":
                        conn.execute("UPDATE mails SET body_text=?, preview=?, body_indexed=1 WHERE id=?",
                                     (text, parser._extract_preview(text), row_id))
                    else:
                        conn.execute("UPDATE sections SET body_text=?, body_indexed=1 WHERE id=?", (text, row_id))
                done += 1
                if progress:
                    progress(done, total)
        if _pdf_signature(pdf_path) != signature:
            raise ValueError("PDFが更新されたため索引を再作成してください")
        with conn:
            if conn.execute(f"SELECT COUNT(*) FROM {table} WHERE body_indexed=0").fetchone()[0] == 0:
                conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES ('body_complete','1')")
    finally:
        conn.close()


@dataclass
class AttachmentInfo:
    name: str
    start_page: int | None
    end_page: int | None = None


@dataclass
class MailRow:
    id: int
    subject: str
    sender: str
    sender_short: str
    to_addr: str
    cc: str
    attachments: str
    attachments_json: str
    received_at: str
    sent_at: str
    title_datetime: str
    start_page: int
    end_page: int
    preview: str
    is_read: bool = False
    toc_index: int = -1
    parent_toc_index: int | None = None
    level: int = 1
    is_mail: bool = True

    def attachment_list(self) -> list[AttachmentInfo]:
        if not self.attachments_json:
            return []
        return [AttachmentInfo(name=a["name"], start_page=a["start_page"], end_page=a.get("end_page"))
                for a in json.loads(self.attachments_json)]


_COLUMNS = ("id, subject, sender, sender_short, to_addr, cc, attachments, attachments_json, "
            "received_at, sent_at, title_datetime, start_page, end_page, preview, is_read, "
            "toc_index, parent_toc_index, level, is_mail")

# UIから選べる並び替えキー。値はDBの実カラム名(SQLインジェクション対策のためホワイトリスト管理)。
SORT_COLUMNS = {"date": "title_datetime", "subject": "subject", "sender": "sender_short"}


def _row_to_mail(row) -> MailRow:
    *rest, is_read, toc_index, parent_toc_index, level, is_mail = row
    return MailRow(*rest, is_read=bool(is_read), toc_index=toc_index,
                   parent_toc_index=parent_toc_index, level=level, is_mail=bool(is_mail))


def _order_by(sort_key: str, descending: bool, prefix: str = "") -> str:
    column = SORT_COLUMNS.get(sort_key, "title_datetime")
    direction = "DESC" if descending else "ASC"
    return f"ORDER BY {prefix}{column} {direction}, {prefix}id {direction}"


def list_all(db_path: str, sort_key: str = "date", descending: bool = True) -> list[MailRow]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM mails {_order_by(sort_key, descending)}"
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_mail(r) for r in rows]


def list_scoped(db_path: str, query: str, sort_key: str, descending: bool,
                scope_toc_index: int | None, include_descendants: bool) -> list[MailRow]:
    """しおり位置で絞る。ルートは従来どおり第1階層だけを返す。"""
    all_rows = list_all(db_path)
    if scope_toc_index is None:
        allowed = {row.toc_index for row in all_rows if row.level == 1}
    else:
        parents = {row.toc_index: row.parent_toc_index for row in all_rows}
        if scope_toc_index not in parents:
            return []
        allowed = set()
        for row in all_rows:
            parent = row.parent_toc_index
            if not include_descendants:
                if parent == scope_toc_index:
                    allowed.add(row.toc_index)
            else:
                while parent is not None:
                    if parent == scope_toc_index:
                        allowed.add(row.toc_index)
                        break
                    parent = parents.get(parent)
    rows = search(db_path, query, sort_key, descending) if query.strip() else list_all(db_path, sort_key, descending)
    return [row for row in rows if row.toc_index in allowed]


def list_scope_options(db_path: str) -> list[tuple[int, int, str]]:
    """TOC順の対象選択肢 (toc_index, level, title)。"""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT toc_index, level, raw_title FROM mails ORDER BY toc_index").fetchall()
    finally:
        conn.close()
    result = []
    for toc_index, level, raw_title in rows:
        parts = raw_title.rsplit("_", 2)
        title = parts[0] if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit() else raw_title
        result.append((toc_index, level, title))
    return result


def _fts_query(raw: str) -> str:
    # ユーザー入力語をFTS5クエリに変換。記号によるクエリ構文エラーを避けるため、
    # 空白区切りの各語をダブルクオートで囲いAND検索にする(前方一致含む)。
    terms = raw.strip().split()
    if not terms:
        return ""
    escaped = [f'"{t}"*' for t in terms if t]
    return " AND ".join(escaped)


def search(db_path: str, query: str, sort_key: str = "date", descending: bool = True) -> list[MailRow]:
    query = query.strip()
    if not query:
        return list_all(db_path, sort_key, descending)

    fts_query = _fts_query(query)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"""SELECT {', '.join('m.' + c for c in _COLUMNS.split(', '))}
                FROM mails_fts f JOIN mails m ON m.id = f.rowid
                WHERE mails_fts MATCH ?
                {_order_by(sort_key, descending, prefix='m.')}""",
            (fts_query,),
        ).fetchall()
    except sqlite3.OperationalError:
        # クエリ構文エラー時は素朴なLIKE検索にフォールバック
        like = f"%{query}%"
        rows = conn.execute(
            f"""SELECT {_COLUMNS} FROM mails
                WHERE subject LIKE ? OR sender LIKE ? OR to_addr LIKE ?
                   OR attachments LIKE ? OR body_text LIKE ?
                {_order_by(sort_key, descending)}""",
            (like, like, like, like, like),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_mail(r) for r in rows]


def get_body_text(db_path: str, mail_id: int) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT body_text FROM mails WHERE id=?", (mail_id,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else ""


def set_read(db_path: str, mail_id: int, read: bool = True) -> None:
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.execute("UPDATE mails SET is_read=? WHERE id=?", (1 if read else 0, mail_id))
    finally:
        conn.close()


def mark_all_read(db_path: str, read: bool = True) -> None:
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.execute("UPDATE mails SET is_read=? WHERE is_mail=1", (1 if read else 0,))
    finally:
        conn.close()


def count_unread(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) FROM mails WHERE is_mail=1 AND is_read=0").fetchone()
    finally:
        conn.close()
    return row[0] if row else 0


# --------------------------------------------------------- 一般資料PDF(しおり階層閲覧)
@dataclass
class SectionRow:
    id: int
    parent_id: int | None
    level: int
    title: str
    path_titles: str
    start_page: int
    end_page: int
    color_hex: str | None = None


_SECTION_COLUMNS = "id, parent_id, level, title, path_titles, start_page, end_page, color_hex"


def _row_to_section(row) -> SectionRow:
    return SectionRow(*row)


def list_sections(db_path: str) -> list[SectionRow]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT {_SECTION_COLUMNS} FROM sections ORDER BY start_page, id"
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_section(r) for r in rows]


def search_sections(db_path: str, query: str) -> list[SectionRow]:
    query = query.strip()
    if not query:
        return list_sections(db_path)

    fts_query = _fts_query(query)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"""SELECT {', '.join('s.' + c for c in _SECTION_COLUMNS.split(', '))}
                FROM sections_fts f JOIN sections s ON s.id = f.rowid
                WHERE sections_fts MATCH ?
                ORDER BY s.start_page, s.id""",
            (fts_query,),
        ).fetchall()
    except sqlite3.OperationalError:
        like = f"%{query}%"
        rows = conn.execute(
            f"""SELECT {_SECTION_COLUMNS} FROM sections
                WHERE title LIKE ? OR body_text LIKE ?
                ORDER BY start_page, id""",
            (like, like),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_section(r) for r in rows]
