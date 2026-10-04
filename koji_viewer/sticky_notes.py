"""Sticky-note persistence and process-side PDF transactions (no Qt widgets)."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

import pymupdf


VERSION = 1
COLORS = {
    "黄": (1.0, 0.85, 0.2), "青": (0.35, 0.7, 1.0),
    "緑": (0.45, 0.85, 0.45), "桃": (1.0, 0.55, 0.7),
    "橙": (1.0, 0.65, 0.25),
}


def canonical(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def sidecar_path(path):
    return str(Path(path).with_suffix("")) + "_review_draft.json"


def legacy_sidecar_path(path):
    return str(Path(path).with_suffix("")) + "_付箋メモ.json"


def stat_signature(path):
    stat = os.stat(path)
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def fingerprint(path):
    before = stat_signature(path)
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if stat_signature(path) != before:
        raise ValueError("PDFが処理中に変更されました")
    return dict(before, sha256=digest.hexdigest())


def unchanged(path, signature):
    try:
        return stat_signature(path) == {k: signature[k] for k in ("size", "mtime_ns")}
    except OSError:
        return False


def atomic_json(path, value):
    """Never truncate the last durable sidecar on failed writes."""
    fd, temporary = tempfile.mkstemp(prefix=".koji-notes-", suffix=".tmp", dir=str(Path(path).parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sidecar_token(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


class EditLock:
    """OS-owned lock, released on exit; file existence does not imply ownership."""
    _held = set()

    def __init__(self, path):
        self.path = canonical(path)
        self.stream = None

    def acquire(self):
        if self.stream is not None:
            return
        if self.path in self._held:
            raise ValueError("別のタブでこのPDFの付箋を編集中です")
        stream = open(self.path + ".lock", "a+b")
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            stream.close()
            raise ValueError("別のアプリで付箋を編集中、または保存先に書き込めません") from None
        self.stream = stream
        self._held.add(self.path)

    def release(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
            self._held.discard(self.path)


def note_from_annot(page, annot, order):
    color = annot.colors.get("stroke") or (1.0, 1.0, 0.0)
    if len(color) == 1:
        color = color * 3
    elif len(color) == 4:
        c, m, y, k = color
        color = (1 - min(1, c + k), 1 - min(1, m + k), 1 - min(1, y + k))
    info = annot.info
    nm = info.get("id", "")
    identity = nm if nm.startswith(("koji-note:", "koji-review:")) else f"existing:{page.number}:{annot.xref}"
    return {"id": identity, "page": page.number,
            "xref": annot.xref, "nm": info.get("id", ""), "order": order,
            "x": annot.rect.x0, "y": annot.rect.y0,
            "text": info.get("content", ""), "color": list(color)}


def collect_notes(document, progress=None):
    notes = {}
    order = 0
    for page in document:
        for annot in page.annots(types=[pymupdf.PDF_ANNOT_TEXT]) or ():
            note = note_from_annot(page, annot, order)
            if note["id"] in notes:
                raise ValueError("PDF内のコメントIDが重複しています")
            notes[note["id"]] = note
            order += 1
        if progress and page.number % 200 == 0:
            progress(page.number + 1, document.page_count)
    return notes


def validate_note(note, count):
    if not isinstance(note, dict) or not isinstance(note.get("id"), str) or not note["id"]:
        raise ValueError("付箋の識別情報が不正です")
    for key in ("page", "xref", "order"):
        if type(note.get(key)) is not int or note[key] < 0:
            raise ValueError("付箋のページ・識別情報が不正です")
    if note["page"] >= count or not isinstance(note.get("text"), str) or not isinstance(note.get("nm"), str):
        raise ValueError("付箋の本文・ページが不正です")
    values = [note.get("x"), note.get("y")]
    color = note.get("color")
    if not isinstance(color, list) or len(color) != 3:
        raise ValueError("付箋の色が不正です")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values + color):
        raise ValueError("付箋の座標・色が不正です")
    if any(not 0 <= v <= 1 for v in color):
        raise ValueError("付箋の色が不正です")


def validate_sidecar(value, path, count):
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != VERSION:
        raise ValueError("未対応の付箋メモJSON形式です")
    pdf = value.get("pdf")
    if not isinstance(pdf, dict) or pdf.get("path") != canonical(path) or pdf.get("page_count") != count:
        raise ValueError("付箋メモJSONとPDFが一致しません")
    if not isinstance(pdf.get("sha256"), str) or len(pdf["sha256"]) != 64 or any(
        type(pdf.get(k)) is not int or pdf[k] < 0 for k in ("size", "mtime_ns")):
        raise ValueError("付箋メモJSONのPDF識別情報が不正です")
    changes = value.get("changes")
    if not isinstance(changes, dict):
        raise ValueError("付箋メモJSONの変更内容が不正です")
    for identity, change in changes.items():
        if not isinstance(change, dict) or set(change) != {"original", "note"}:
            raise ValueError("付箋メモJSONの変更形式が不正です")
        original, note = change["original"], change["note"]
        if original is None and note is None:
            raise ValueError("空の付箋変更です")
        for item in (original, note):
            if item is not None:
                validate_note(item, count)
                if item["id"] != identity:
                    raise ValueError("付箋の識別情報が一致しません")
        if original and note and any(original[k] != note[k] for k in ("xref", "order")):
            raise ValueError("既存付箋の識別情報が変更されています")
        if original and note and note["nm"] != original["nm"] and not note["nm"].startswith(("koji-note:", "koji-review:")):
            raise ValueError("コメントの管理IDが不正です")
        if original is None and note["xref"] != 0:
            raise ValueError("新規付箋の識別情報が不正です")
    transaction = value.get("transaction")
    if transaction is not None:
        if not isinstance(transaction, dict) or not all(isinstance(transaction.get(k), str) for k in ("destination", "stage")):
            raise ValueError("付箋保存の記録が不正です")
        if not isinstance(transaction.get("output"), dict) or not isinstance(transaction["output"].get("sha256"), str):
            raise ValueError("付箋保存の出力識別情報が不正です")
    if "review" in value:
        from .review import validate
        validate(value["review"])
    return value


def load_notes(path, progress=None):
    signature = fingerprint(path)
    with pymupdf.open(path) as document:
        if document.needs_pass:
            raise ValueError("パスワード付きPDFは開けません")
        notes = collect_notes(document, progress)
        count = document.page_count
        writable = bool(document.permissions & pymupdf.PDF_PERM_ANNOTATE)
    if not unchanged(path, signature):
        raise ValueError("PDFが読み込み中に変更されました")
    pdf = dict(signature, path=canonical(path), page_count=count)
    sidecar = sidecar_path(path)
    if not os.path.exists(sidecar) and os.path.exists(legacy_sidecar_path(path)):
        sidecar = legacy_sidecar_path(path)
    result = {"pdf": pdf, "notes": notes, "changes": {}, "writable": writable,
              "sidecar": sidecar, "token": sidecar_token(sidecar), "warning": "", "applied": False}
    if result["token"] is None:
        return result
    try:
        value = json.loads(Path(sidecar).read_text(encoding="utf-8"))
        validate_sidecar(value, path, count)
        if "review" in value:
            result["review"] = value["review"]
        transaction = value.get("transaction")
        if transaction:
            destination = transaction["destination"]
            if os.path.isfile(destination) and fingerprint(destination)["sha256"] == transaction["output"]["sha256"]:
                # Saving under a different name left the source unchanged. Resume the output.
                result.update(applied=True, destination=destination, transaction=transaction)
                with pymupdf.open(destination) as saved:
                    saved_notes = collect_notes(saved)
                    saved_signature = fingerprint(destination)
                    if saved_signature["sha256"] != transaction["output"]["sha256"]:
                        raise ValueError("復旧先のPDFが読み込み中に変更されました")
                    result["saved_result"] = {"path": destination, "notes": saved_notes,
                        "pdf": dict(saved_signature, path=canonical(destination), page_count=saved.page_count)}
                return result
        if value["pdf"] != pdf:
            raise ValueError("PDFが変更されているため、付箋メモを自動復元できません")
        # Older v1 records addressed managed annotations by page/xref, while
        # current readers use their stable NM. Migrate only an exact match.
        remapped = {}
        for identity, change in value["changes"].items():
            original = change["original"]
            actual = notes.get(original.get("nm")) if original else None
            if identity not in notes and actual and dict(actual, id=identity) == original:
                identity = actual["id"]
                change = copy.deepcopy(change)
                change["original"]["id"] = identity
                if change["note"]:
                    change["note"]["id"] = identity
            remapped[identity] = change
        value["changes"] = remapped
        for identity, change in value["changes"].items():
            if change["original"] is not None and notes.get(identity) != change["original"]:
                raise ValueError("PDFの既存付箋と保存されたメモが一致しません")
        result["changes"] = value["changes"]
        result["transaction"] = transaction
        if sidecar_token(sidecar) != result["token"]:
            raise ValueError("付箋メモJSONが読み込み中に変更されました")
    except Exception as error:
        result["warning"] = f"付箋メモJSONを復元できません: {error}"
        result["writable"] = False
    return result


def merged_notes(baseline, changes):
    notes = copy.deepcopy(baseline)
    for identity, change in changes.items():
        if change["note"] is None:
            notes.pop(identity, None)
        else:
            notes[identity] = copy.deepcopy(change["note"])
    return notes


def _annotation_state(page):
    return [(a.xref, a.type, tuple(a.rect), a.info, a.colors)
            for a in page.annots() or () if a.type[0] != pymupdf.PDF_ANNOT_TEXT]


def prepare_save(source, destination, payload, progress=None):
    """Write and verify a sibling staging PDF; source is never written here."""
    validate_sidecar(payload, source, payload["pdf"]["page_count"])
    if fingerprint(source) != {k: payload["pdf"][k] for k in ("size", "mtime_ns", "sha256")}:
        raise ValueError("PDFが変更されました。保存を中止しました")
    previous = fingerprint(destination) if os.path.exists(destination) else None
    fd, stage = tempfile.mkstemp(prefix=".koji-note-save-", suffix=".tmp.pdf", dir=str(Path(destination).parent))
    os.close(fd)
    try:
        shutil.copyfile(source, stage)
        checks, expected = {}, {}
        with pymupdf.open(stage) as document:
            if not document.permissions & pymupdf.PDF_PERM_ANNOTATE:
                raise ValueError("このPDFは注釈の変更が許可されていません")
            count = document.page_count
            toc = document.get_toc(simple=False)
            metadata = document.metadata
            touched = {(c["original"]["page"], c["original"]["xref"]) for c in payload["changes"].values() if c["original"]}
            untouched = [(page.number, note_from_annot(page, a, 0)) for page in document
                         for a in page.annots(types=[pymupdf.PDF_ANNOT_TEXT]) or ()
                         if (page.number, a.xref) not in touched]
            for index, (identity, change) in enumerate(payload["changes"].items()):
                note, original = change["note"], change["original"]
                item = original or note
                page = document[item["page"]]
                target = document[note["page"]] if note else page
                bounds = target.rect * target.derotation_matrix
                if note and not pymupdf.Point(note["x"], note["y"]) in bounds:
                    raise ValueError("付箋の配置位置がページ範囲外です")
                if page.number not in checks:
                    checks[page.number] = (tuple(page.rect), page.rotation, page.get_links(), _annotation_state(page))
                if target.number not in checks:
                    checks[target.number] = (tuple(target.rect), target.rotation, target.get_links(), _annotation_state(target))
                if original:
                    annot = page.load_annot(original["xref"])
                    if annot is None or annot.type[0] != pymupdf.PDF_ANNOT_TEXT or note_from_annot(page, annot, original["order"]) != original:
                        raise ValueError("変更対象の既存付箋が一致しません")
                    if note is None:
                        page.delete_annot(annot)
                        expected[identity] = (page.number, original["xref"], None)
                        continue
                    moved = any(original[k] != note[k] for k in ("page", "x", "y"))
                    if moved:
                        page.delete_annot(annot)
                        page = target
                    else:
                        annot.set_info(content=note["text"])
                        document.xref_set_key(annot.xref, "NM", pymupdf.get_pdf_str(note["nm"]))
                else:
                    moved = False
                if original is None or moved:
                    annot = page.add_text_annot((note["x"], note["y"]), note["text"], icon="Note")
                    # PyMuPDF rotates the built-in Text icon around the passed
                    # point on rotated pages. Explicitly keep our unrotated
                    # top-left coordinate, including pages with a crop offset.
                    dx, dy = note["x"] - annot.rect.x0, note["y"] - annot.rect.y0
                    if abs(dx) > .001 or abs(dy) > .001:
                        # Text annotations ignore set_rect(). Compensate the
                        # measured icon offset, rather than assuming its size.
                        page.delete_annot(annot)
                        annot = page.add_text_annot((note["x"] + dx, note["y"] + dy), note["text"], icon="Note")
                    document.xref_set_key(annot.xref, "NM", pymupdf.get_pdf_str(note["nm"] or identity))
                annot.set_colors(stroke=note["color"])
                annot.update()
                actual = note_from_annot(page, annot, note["order"])
                if (actual["text"] != note["text"] or
                    any(abs(actual[k] - note[k]) > .01 for k in ("x", "y")) or
                    any(abs(a - b) > .001 for a, b in zip(actual["color"], note["color"]))):
                    raise ValueError("付箋の本文・色・位置を正しく保存できません")
                expected[identity] = (page.number, annot.xref, actual)
                if progress:
                    progress(index + 1, len(payload["changes"]))
            if document.can_save_incrementally():
                document.save(stage, incremental=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
            else:
                rewrite = stage + ".rewrite.pdf"
                try:
                    document.save(rewrite, garbage=0, clean=False, encryption=pymupdf.PDF_ENCRYPT_KEEP)
                except Exception:
                    if os.path.exists(rewrite):
                        os.unlink(rewrite)
                    raise
        if os.path.exists(stage + ".rewrite.pdf"):
            os.replace(stage + ".rewrite.pdf", stage)
        with pymupdf.open(stage) as document:
            if document.page_count != count or document.get_toc(simple=False) != toc or document.metadata != metadata:
                raise ValueError("保存後のページ数・しおり・情報が一致しません")
            for number, note in untouched:
                page = document[number]
                annot = page.load_annot(note["xref"])
                if annot is None or note_from_annot(page, annot, 0) != note:
                    raise ValueError("保存後の他のコメントが一致しません")
            for number, check in checks.items():
                page = document[number]
                if (tuple(page.rect), page.rotation, page.get_links(), _annotation_state(page)) != check:
                    raise ValueError("保存後のページ・リンク・他の注釈が一致しません")
            for number, xref, note in expected.values():
                page = document[number]
                annot = page.load_annot(xref) if xref in [a.xref for a in page.annots() or ()] else None
                if note is None:
                    if annot is not None:
                        raise ValueError("付箋の削除を確認できません")
                elif annot is None or note_from_annot(page, annot, note["order"]) != note:
                    raise ValueError("付箋の保存結果を確認できません")
            baseline = collect_notes(document)
        if not unchanged(source, payload["pdf"]):
            raise ValueError("保存中に元のPDFが変更されました")
        return {"destination": canonical(destination), "stage": stage, "output": fingerprint(stage),
                "previous": previous, "source": canonical(source), "pdf": payload["pdf"], "notes": baseline}
    except Exception:
        if os.path.exists(stage):
            os.unlink(stage)
        raise


def commit_save(transaction):
    """Run after the viewer releases all source/destination handles."""
    source, destination, stage = transaction["source"], transaction["destination"], transaction["stage"]
    if fingerprint(source) != {k: transaction["pdf"][k] for k in ("size", "mtime_ns", "sha256")}:
        raise ValueError("保存直前に元のPDFが変更されました")
    if (fingerprint(destination) if os.path.exists(destination) else None) != transaction["previous"]:
        raise ValueError("保存先のPDFが変更されました")
    if fingerprint(stage) != transaction["output"]:
        raise ValueError("保存用PDFが変更されました")
    with open(stage, "r+b") as stream:
        os.fsync(stream.fileno())
    os.replace(stage, destination)
    actual = fingerprint(destination)
    if actual["sha256"] != transaction["output"]["sha256"]:
        raise ValueError("保存したPDFを確認できません")
    result = {"path": destination, "pdf": dict(actual, path=destination, page_count=transaction["pdf"]["page_count"]),
              "notes": transaction["notes"], "index_warning": ""}
    try:
        from .db import preserve_note_save_indexes
        preserve_note_save_indexes(source, destination, transaction["pdf"])
    except Exception as error:
        result["index_warning"] = str(error)
    return result
