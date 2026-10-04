"""Portable document review records. PDF byte identity and local stat are separate."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

from . import sticky_notes as store
import pymupdf

STATUSES = ("未確認", "確認済み", "対応不要")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def create(pdf, notes):
    state = {"version": 2, "kind": "merged",
             "document": {"name": Path(pdf["path"]).stem, "sha256": pdf["sha256"], "page_count": pdf["page_count"]},
             "current_pdf": copy.deepcopy(pdf), "author": {"id": str(uuid.uuid4()), "name": ""},
             "review_id": str(uuid.uuid4()), "revision": 0, "comments": {}, "receipts": {}, "history": [],
             "bindings": {}}
    for identity, note in notes.items():
        stable = identity if identity.startswith(("koji-note:", "koji-review:")) else "koji-review:" + str(uuid.uuid4())
        state["bindings"][stable] = identity
        change(state, stable, dict(note, id=stable, nm=stable))
        state["comments"][stable]["external"] = True
    return state


def event(state, action, **data):
    state["history"].append(dict(at=now(), action=action, **copy.deepcopy(data)))


def set_author(state, name):
    name = name.strip()
    if not name:
        raise ValueError("記入者名を入力してください")
    state["author"]["name"] = name
    for comment in state["comments"].values():
        if comment["author"]["id"] == state["author"]["id"] and not comment.get("external", False):
            comment["author"]["name"] = name
    event(state, "記入者設定", name=name)


def source(comment):
    """Semantic origin fields only; xrefs, names and judgment aren't revisions."""
    note = comment["note"]
    return {"deleted": comment["deleted"], "note": {k: note[k] for k in ("page", "x", "y", "text", "color")}}


def source_digest(comment):
    return hashlib.sha256(json.dumps(source(comment), sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def change(state, identity, note):
    old = state["comments"].get(identity)
    if old and old["author"]["id"] != state["author"]["id"]:
        raise ValueError("他の記入者の原文は変更できません")
    if note is None and old is None:
        return
    if note is not None:
        note = copy.deepcopy(dict(note, id=identity, nm=identity))
        store.validate_note(note, state["document"]["page_count"])
    updated = dict(copy.deepcopy(old) if old else {}, id=identity,
        author=copy.deepcopy(state["author"]), review_id=state["review_id"],
        revision=(old["revision"] if old else 0) + 1,
        created_at=old["created_at"] if old else now(), updated_at=now(), deleted=note is None,
        note=note if note is not None else copy.deepcopy(old["note"]))
    updated.setdefault("status", "未確認")
    updated.setdefault("memo", "")
    updated.setdefault("excluded", False)
    updated["external"] = False
    if old and source(old) == source(updated):
        return
    updated["status"] = "未確認"
    updated.setdefault("ancestors", {})
    if old:
        updated["ancestors"][str(old["revision"])] = source_digest(old)
    state["comments"][identity] = updated
    event(state, "削除" if note is None else "更新" if old else "追加", comment_id=identity,
          before=source(old) if old else None, after=source(updated))


def judge(state, identity, status, memo, excluded):
    if status not in STATUSES or not isinstance(memo, str) or type(excluded) is not bool:
        raise ValueError("状態・取りまとめメモが不正です")
    comment = state["comments"][identity]
    before = {k: comment[k] for k in ("status", "memo", "excluded")}
    after = dict(status=status, memo=memo, excluded=excluded)
    if before != after:
        comment.update(after)
        comment["external"] = False
        event(state, "確認判断", comment_id=identity, before=before, after=after)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _positive(value):
    return type(value) is int and value > 0


def validate(value):
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != 2 or value.get("kind") not in ("submission", "merged"):
        raise ValueError("未対応のレビューJSON形式です")
    document = value.get("document")
    if not isinstance(document, dict) or not _text(document.get("name")) or not _positive(document.get("page_count")) or not isinstance(document.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", document["sha256"]):
        raise ValueError("対象PDFの識別情報が不正です")
    author = value.get("author")
    if not isinstance(author, dict) or not _text(author.get("id")) or not isinstance(author.get("name"), str):
        raise ValueError("記入者情報が不正です")
    if not _text(value.get("review_id")) or type(value.get("revision")) is not int or value["revision"] < (1 if value["kind"] == "submission" else 0):
        raise ValueError("レビューの識別情報・提出版が不正です")
    comments = value.get("comments")
    if not isinstance(comments, dict):
        raise ValueError("コメント一覧が不正です")
    for identity, comment in comments.items():
        if not isinstance(comment, dict) or not isinstance(identity, str) or not identity.startswith(("koji-note:", "koji-review:")) or comment.get("id") != identity or not _positive(comment.get("revision")):
            raise ValueError("コメントの識別情報・更新番号が不正です")
        ca = comment.get("author")
        if not isinstance(ca, dict) or not _text(ca.get("id")) or not isinstance(ca.get("name"), str) or not _text(comment.get("review_id")):
            raise ValueError("コメントの記入者が不正です")
        if value["kind"] == "submission" and (ca != author or comment["review_id"] != value["review_id"]):
            raise ValueError("提出元とコメントの記入者が一致しません")
        if any(type(comment.get(k)) is not bool for k in ("deleted", "excluded")) or comment.get("status") not in STATUSES or not isinstance(comment.get("memo"), str) or any(not _text(comment.get(k)) for k in ("created_at", "updated_at")):
            raise ValueError("コメントの状態が不正です")
        store.validate_note(comment.get("note"), document["page_count"])
        if comment["note"]["id"] != identity:
            raise ValueError("コメントIDが一致しません")
        ancestors = comment.get("ancestors", {})
        if not isinstance(ancestors, dict) or any(not isinstance(k, str) or not k.isdecimal() or not 0 < int(k) < comment["revision"] or not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for k, v in ancestors.items()):
            raise ValueError("コメントの更新履歴が不正です")
        if "external" in comment and type(comment["external"]) is not bool:
            raise ValueError("コメントの管理状態が不正です")
    if value["kind"] == "merged":
        for key, cls in (("receipts", dict), ("history", list), ("bindings", dict), ("current_pdf", dict)):
            if not isinstance(value.get(key), cls):
                raise ValueError("レビュー集約の保存情報が不正です")
        pdf = value["current_pdf"]
        if pdf.get("page_count") != document["page_count"] or not isinstance(pdf.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", pdf["sha256"]):
            raise ValueError("レビュー集約の現在PDF情報が不正です")
        for identity, receipt in value["receipts"].items():
            if not _text(identity) or not isinstance(receipt, dict) or not _positive(receipt.get("revision")) or not _text(receipt.get("digest")) or not _text(receipt.get("author_id")):
                raise ValueError("取り込み履歴が不正です")
        if any(not isinstance(h, dict) or not _text(h.get("at")) or not _text(h.get("action")) for h in value["history"]):
            raise ValueError("変更履歴が不正です")
        if any(not _text(k) or not _text(v) for k, v in value["bindings"].items()):
            raise ValueError("PDF注釈の対応情報が不正です")
    return value


def submission(state):
    if not state["author"]["name"].strip():
        raise ValueError("提出前に記入者名を入力してください")
    value = {k: copy.deepcopy(state[k]) for k in ("document", "author", "review_id")}
    value.update(version=2, kind="submission", revision=state["revision"] + 1, exported_at=now(),
        comments={k: copy.deepcopy(v) for k, v in state["comments"].items() if v["author"]["id"] == state["author"]["id"] and not v.get("external", False)})
    return validate(value)


def accept_export(state, value):
    state["revision"] = value["revision"]
    state["export_digest"] = digest(value)
    event(state, "提出", revision=value["revision"])


def output_path(state, pdf_path, kind, extension, revision=None):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", state["document"]["name"]).rstrip(" .") or "書類"
    if kind == "submission":
        author = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", state["author"]["name"]).rstrip(" .") or "記入者未設定"
        if revision is None:
            revision = max(1, state["revision"])
            if state["revision"] and state.get("export_digest") and state["author"]["name"].strip():
                current = submission(state)
                current["revision"] = state["revision"]
                if digest(current) != state["export_digest"]:
                    revision += 1
        suffix = f"_review_{author}_v{revision:03d}"
    else:
        suffix = "_review_merged"
    return str(Path(pdf_path).parent / (name + suffix + extension))


def matching(document, other):
    return all(document[k] == other[k] for k in ("sha256", "page_count"))


def digest(value):
    # Export clock and xrefs do not change the logical contents of a submission.
    compact = {k: value[k] for k in ("document", "author", "review_id", "revision")}
    compact["document"] = {k: value["document"][k] for k in ("sha256", "page_count")}
    compact["comments"] = {k: dict(source(v), revision=v["revision"], author_id=v["author"]["id"], review_id=v["review_id"])
                           for k, v in value["comments"].items()}
    return hashlib.sha256(json.dumps(compact, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def merge(state, incoming, choices=None):
    validate(incoming)
    if incoming["kind"] != "submission":
        raise ValueError("集約JSONは「レビュー集約を開く」で復元してください")
    if not matching(state["document"], incoming["document"]):
        raise ValueError("対象PDFが異なります")
    choices = choices or {}
    result = dict(label="一致", added=0, updated=0, deleted=0, unchanged=0, conflicts=[])
    receipt = state["receipts"].get(incoming["review_id"])
    token = digest(incoming)
    same_version_conflict = False
    if receipt:
        if receipt["author_id"] != incoming["author"]["id"]:
            raise ValueError("同じレビューIDの記入者が変更されています")
        if incoming["revision"] < receipt["revision"]:
            result["label"] = "古い版"
            return copy.deepcopy(state), result
        if incoming["revision"] == receipt["revision"]:
            if receipt["digest"] == token:
                result["label"] = "取り込み済み"
                return copy.deepcopy(state), result
            same_version_conflict = True
    updated = copy.deepcopy(state)
    unresolved = False
    for identity, comment in incoming["comments"].items():
        current = state["comments"].get(identity)
        if current and (current["author"]["id"] != comment["author"]["id"] or current["review_id"] != comment["review_id"]):
            raise ValueError("コメントIDの記入者・提出元が一致しません")
        divergent = current and current["revision"] < comment["revision"] and str(current["revision"]) in comment.get("ancestors", {}) and comment["ancestors"][str(current["revision"])] != source_digest(current)
        conflict = (same_version_conflict and (not current or source(current) != source(comment) or current["revision"] != comment["revision"])) or (current and current["revision"] == comment["revision"] and source(current) != source(comment)) or divergent
        if conflict:
            result["conflicts"].append(identity)
            if identity not in choices:
                unresolved = True
                continue
            if choices[identity] != "incoming":
                event(updated, "競合: 現在を保持", comment_id=identity, incoming=source(comment))
                continue
            event(updated, "競合: 提出を採用", comment_id=identity, before=source(current) if current else None, after=source(comment))
        elif current and current["revision"] >= comment["revision"]:
            result["unchanged"] += 1
            continue
        adopted = copy.deepcopy(comment)
        adopted["note"].update(xref=0, nm=identity)
        if current:
            adopted.update(memo=current["memo"], excluded=current["excluded"], status=current["status"] if source(current) == source(comment) else "未確認")
        else:
            adopted.update(memo="", excluded=False, status="未確認")
        updated["comments"][identity] = adopted
        key = "deleted" if adopted["deleted"] else "updated" if current else "added"
        result[key] += 1
        event(updated, "取り込み:" + key, comment_id=identity, before=source(current) if current else None, after=source(comment))
    if unresolved:
        result["label"] = "競合あり"
        return copy.deepcopy(state), result
    if same_version_conflict and not result["conflicts"]:
        raise ValueError("同じ提出版に異なる内容があります。版番号を更新して再提出してください")
    updated["receipts"][incoming["review_id"]] = dict(revision=incoming["revision"], digest=token, author_id=incoming["author"]["id"])
    event(updated, "取り込み", review_id=incoming["review_id"], revision=incoming["revision"], author=incoming["author"]["name"])
    return updated, result


def visible_notes(state, include_excluded=False):
    return {k: copy.deepcopy(v["note"]) for k, v in state["comments"].items()
            if not v["deleted"] and (include_excluded or not v["excluded"])}


def annotation_text(comment):
    text = f"記入者：{comment['author']['name'] or '記入者未設定'}\n{comment['note']['text']}\n\n状態：{comment['status']}"
    if comment["memo"]:
        text += "\n取りまとめメモ：" + comment["memo"]
    return text


def pdf_changes(state, baseline):
    changes = {}
    by_nm = {n["nm"]: n for n in baseline.values() if n["nm"]}
    for identity, comment in state["comments"].items():
        original = by_nm.get(identity) or baseline.get(state["bindings"].get(identity, ""))
        if comment.get("external", False):
            continue
        note = None
        if not comment["deleted"] and not comment["excluded"]:
            note = dict(copy.deepcopy(comment["note"]), id=identity, nm=identity,
                        text=annotation_text(comment), xref=original["xref"] if original else 0,
                        order=original["order"] if original else comment["note"]["order"])
        if original:
            # The transaction's lookup ID can differ from the stable output NM.
            key = original["id"]
            if note:
                note["id"] = key
            same = note is not None and all(note[k] == original[k] for k in ("id", "page", "xref", "order", "nm", "text")) and all(abs(note[k] - original[k]) < .01 for k in ("x", "y")) and all(abs(a - b) < .001 for a, b in zip(note["color"], original["color"]))
            if not same:
                changes[key] = {"original": copy.deepcopy(original), "note": note}
        elif note:
            changes[identity] = {"original": None, "note": note}
    return changes


def restore(value, pdf):
    validate(value)
    if value["kind"] != "merged" or pdf["page_count"] != value["document"]["page_count"] or pdf["sha256"] not in (value["document"]["sha256"], value["current_pdf"]["sha256"]):
        raise ValueError("レビュー集約と現在のPDFが一致しません")
    result = copy.deepcopy(value)
    result["current_pdf"] = copy.deepcopy(pdf)
    return result


def validate_positions(value, document):
    bounds = {}
    for comment in value["comments"].values():
        note = comment["note"]
        if note["page"] not in bounds:
            page = document[note["page"]]
            bounds[note["page"]] = page.rect * page.derotation_matrix
        if not pymupdf.Point(note["x"], note["y"]) in bounds[note["page"]]:
            raise ValueError("コメントの配置位置がページ範囲外です")
