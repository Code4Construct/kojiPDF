"""Sticky-note widgets and the session shared across bookmark/mail modes."""
from __future__ import annotations

import copy
import html
import json
import os
from pathlib import Path
import uuid

import pymupdf
from PySide6.QtCore import QObject, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QPushButton, QTextEdit, QToolButton, QVBoxLayout, QWidget, QLineEdit,
    QCheckBox, QDoubleSpinBox, QSpinBox, QInputDialog)

from .pdf_jobs import PdfJob
from . import sticky_notes as store
from . import review as reviews


def color_icon(color):
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QColor("#756b3d"))
    painter.setBrush(QColor.fromRgbF(*color))
    painter.drawRoundedRect(2, 2, 14, 14, 2, 2)
    painter.end()
    return QIcon(pixmap)


class NoteEditor(QDialog):
    deleteRequested = Signal()

    def __init__(self, note, existing=False, parent=None, comment=None, author_id=None, page_count=None):
        super().__init__(parent)
        self.setWindowTitle(f"コメント — {note['page'] + 1}ページ")
        self.setMinimumSize(330, 250)
        self.resize(420, 330)
        self.deleted = False
        self.own = comment is None or comment["author"]["id"] == author_id
        layout = QVBoxLayout(self)
        if comment:
            label = QLabel("記入者：" + (comment["author"]["name"] or "記入者未設定"))
            label.setTextFormat(Qt.TextFormat.PlainText)
            layout.addWidget(label)
        layout.addWidget(QLabel("本文"))
        self.body = QTextEdit()
        self.body.setAcceptRichText(False)
        self.body.setPlainText(note["text"])
        layout.addWidget(self.body)
        self.body.setReadOnly(not self.own)
        colors = QHBoxLayout()
        colors.addWidget(QLabel("色"))
        self.color = QComboBox()
        for name, rgb in store.COLORS.items():
            self.color.addItem(color_icon(rgb), name, list(rgb))
        if note["color"] not in [list(rgb) for rgb in store.COLORS.values()]:
            self.color.addItem(color_icon(note["color"]), "現在の色", note["color"])
        index = self.color.findData(note["color"])
        self.color.setCurrentIndex(max(0, index))
        colors.addWidget(self.color)
        colors.addStretch()
        layout.addLayout(colors)
        self.color.setEnabled(self.own)
        self.page_input = self.x_input = self.y_input = None
        if comment is not None and page_count is not None:
            placement = QHBoxLayout()
            self.page_input = QSpinBox()
            self.page_input.setRange(1, page_count)
            self.page_input.setValue(note["page"] + 1)
            placement.addWidget(QLabel("ページ"))
            placement.addWidget(self.page_input)
            for key in ("x", "y"):
                spin = QDoubleSpinBox()
                spin.setRange(-100000, 100000)
                spin.setDecimals(2)
                spin.setValue(note[key])
                spin.setEnabled(self.own)
                placement.addWidget(QLabel(key.upper()))
                placement.addWidget(spin)
                setattr(self, key + "_input", spin)
            self.page_input.setEnabled(self.own)
            layout.addLayout(placement)
        self.state_input = self.memo_input = self.excluded_input = None
        if comment is not None:
            self.state_input = QComboBox()
            self.state_input.addItems(reviews.STATUSES)
            self.state_input.setCurrentText(comment["status"])
            layout.addWidget(QLabel("状態"))
            layout.addWidget(self.state_input)
            layout.addWidget(QLabel("取りまとめメモ"))
            self.memo_input = QTextEdit()
            self.memo_input.setAcceptRichText(False)
            self.memo_input.setPlainText(comment["memo"])
            layout.addWidget(self.memo_input)
            self.excluded_input = QCheckBox("集約から除外（チェックを外すと復元）")
            self.excluded_input.setChecked(comment["excluded"])
            layout.addWidget(self.excluded_input)
            self.resize(480, 600)
        bottom = QHBoxLayout()
        if existing and self.own:
            self.delete_button = QPushButton("削除")
            self.delete_button.clicked.connect(self._delete)
            bottom.addWidget(self.delete_button)
        bottom.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("確定")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)
        self.body.setFocus()

    def _delete(self):
        if QMessageBox.question(self, "コメントを削除", "このコメントを削除しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.deleted = True
            self.accept()


class NotesPanel(QWidget):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.setObjectName("stickyNotesPanel")
        self.setMinimumWidth(290)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        heading = QHBoxLayout()
        title = QLabel("書類レビュー")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        heading.addWidget(title)
        heading.addStretch()
        close = QToolButton()
        close.setText("×")
        close.setToolTip("コメント一覧を閉じる")
        close.clicked.connect(controller.hide_panel)
        heading.addWidget(close)
        layout.addLayout(heading)
        author_row = QHBoxLayout()
        author_row.addWidget(QLabel("記入者"))
        self.author = QLineEdit()
        self.author.setPlaceholderText("名前を入力")
        self.author.editingFinished.connect(controller.set_author)
        author_row.addWidget(self.author)
        layout.addLayout(author_row)
        self.add_button = QPushButton("＋ コメント")
        self.add_button.clicked.connect(controller.begin_placement)
        layout.addWidget(self.add_button)
        exchange = QHBoxLayout()
        self.import_button = QPushButton("取り込む")
        self.import_button.setToolTip("レビューを取り込む")
        self.import_button.clicked.connect(controller.import_reviews)
        self.export_button = QPushButton("書き出す")
        self.export_button.setToolTip("レビューを書き出す")
        self.export_button.clicked.connect(controller.export_review)
        exchange.addWidget(self.import_button)
        exchange.addWidget(self.export_button)
        layout.addLayout(exchange)
        self.author_filter = QComboBox()
        self.author_filter.addItem("記入者：全員", "")
        self.status_filter = QComboBox()
        self.status_filter.addItem("状態：すべて", "")
        for value in reviews.STATUSES:
            self.status_filter.addItem(value, value)
        filters = QHBoxLayout()
        filters.addWidget(self.author_filter)
        filters.addWidget(self.status_filter)
        layout.addLayout(filters)
        self.excluded_filter = QComboBox()
        self.excluded_filter.addItem("通常のコメント", "active")
        self.excluded_filter.addItem("除外したコメント", "excluded")
        self.excluded_filter.addItem("除外を含むすべて", "all")
        layout.addWidget(self.excluded_filter)
        self.search = QLineEdit()
        self.search.setPlaceholderText("コメント・取りまとめメモを検索")
        layout.addWidget(self.search)
        for combo in (self.author_filter, self.status_filter, self.excluded_filter):
            combo.currentIndexChanged.connect(lambda: controller.refresh())
        self.search.textChanged.connect(lambda: controller.refresh())
        self.counts = QLabel()
        layout.addWidget(self.counts)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setSpacing(3)
        self.list.itemClicked.connect(lambda item: controller.navigate(item.data(Qt.ItemDataRole.UserRole)))
        self.list.itemDoubleClicked.connect(lambda item: controller.edit_note(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.list, 1)
        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(48)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.retry = QPushButton("メモの再保存")
        self.retry.clicked.connect(controller.autosave)
        layout.addWidget(self.retry)
        row = QHBoxLayout()
        self.save = QPushButton("コメント付きPDFに保存")
        self.save.clicked.connect(controller.save_as)
        row.addWidget(self.save, 1)
        self.more = QToolButton()
        self.more.setText("▼")
        self.more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.more)
        self.save_as_action = menu.addAction("名前を付けてPDFに保存")
        self.save_as_action.triggered.connect(controller.save_as)
        self.merged_action = menu.addAction("レビュー集約を保存")
        self.merged_action.triggered.connect(controller.export_merged)
        self.open_merged_action = menu.addAction("レビュー集約を開く")
        self.open_merged_action.triggered.connect(controller.open_merged)
        self.history_action = menu.addAction("レビュー履歴")
        self.history_action.triggered.connect(controller.show_history)
        menu.addSeparator()
        self.discard_action = menu.addAction("PDF未反映の変更をすべて破棄")
        self.discard_action.triggered.connect(controller.discard_all)
        self.more.setMenu(menu)
        row.addWidget(self.more)
        layout.addLayout(row)
        self.hide()


class NotesController(QObject):
    changed = Signal()
    saveFinished = Signal(bool)
    pathChanged = Signal(str, str)

    def __init__(self, tab):
        super().__init__(tab)
        self.tab = tab
        self.path = tab.pdf_path
        self.sidecar = store.sidecar_path(self.path)
        self.lock = store.EditLock(self.sidecar)
        self.destination_lock = None
        self.destination_token = None
        self.ready = False
        self.writable = False
        self.busy = False
        self.unsaved = False
        self.warning = ""
        self.stage_text = "付箋を読み込み中…"
        self.baseline = {}
        self.changes = {}
        self.durable_changes = {}
        self.pdf = None
        self.token = None
        self.transaction = None
        self.review = None
        self.durable_review = None
        self.panel = None
        self._closed = False
        self._suspended = False
        self._load_result = None
        self._save_result = None
        self._prepared = None
        self._operation = ""
        self.job = PdfJob(self)
        self.job.message.connect(self._message)
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self.autosave)
        self.attach(tab)
        self._start("notes_load", self.path)

    @property
    def pending(self):
        return bool(self.changes)

    @property
    def notes(self):
        if self.review is not None:
            return reviews.visible_notes(self.review)
        return store.merged_notes(self.baseline, self.changes)

    def attach(self, tab):
        self.tab = tab
        self.setParent(tab)
        tab.pdf_view.notePlacementRequested.connect(self.add_at)
        tab.pdf_view.noteActivated.connect(self.edit_note)
        tab.pdf_view.notePlacementCancelled.connect(self._placement_cancelled)
        self.panel = NotesPanel(self)
        self.refresh()

    def detach(self):
        view = self.tab.pdf_view
        view.notePlacementRequested.disconnect(self.add_at)
        view.noteActivated.disconnect(self.edit_note)
        view.notePlacementCancelled.disconnect(self._placement_cancelled)
        self.panel.deleteLater()
        self.panel = None
        self.setParent(None)

    def _start(self, operation, *arguments):
        self._operation = operation
        try:
            self.job.start(operation, *arguments)
        except Exception as error:
            self._failed(str(error))

    def _message(self, kind, value):
        if self._closed:
            return
        if kind == "progress":
            done, total = value
            self.stage_text = ("付箋を読み込み中" if self._operation == "notes_load" else "PDF保存準備中") + f": {done}/{total}"
            self.refresh(False)
        elif kind == "notes":
            self._load_result = value
        elif kind == "prepared":
            self._prepared = value
        elif kind == "committed":
            self._save_result = value
        elif kind == "error":
            self._failed(value)
        elif kind == "done":
            if self._operation == "notes_load":
                self._loaded(self._load_result)
            elif self._operation == "notes_prepare":
                self._commit_prepared()
            elif self._operation == "notes_commit":
                self._finish_save(self._save_result)

    def _loaded(self, result):
        if result is None:
            self._failed("付箋の読み込み結果がありません")
            return
        self.pdf = result["pdf"]
        actual_sidecar = result.get("sidecar", self.sidecar)
        if actual_sidecar != self.sidecar:
            self.lock.release()
            self.sidecar = actual_sidecar
            self.lock = store.EditLock(self.sidecar)
        self.baseline = result["notes"]
        self.changes = result["changes"]
        self.durable_changes = copy.deepcopy(self.changes)
        self.token = result["token"]
        self.warning = result["warning"]
        self.writable = result["writable"]
        self.ready = True
        self.transaction = result.get("transaction")
        self.review = copy.deepcopy(result.get("review"))
        self.durable_review = copy.deepcopy(self.review)
        self.stage_text = ""
        if result["applied"]:
            try:
                self.lock.acquire()
                if store.sidecar_token(self.sidecar) != self.token:
                    raise ValueError("付箋メモJSONが別のアプリで変更されました")
                saved = result["saved_result"]
                if store.canonical(saved["path"]) != store.canonical(self.path):
                    self.destination_lock = store.EditLock(store.sidecar_path(saved["path"]))
                    self.destination_lock.acquire()
                    if store.sidecar_token(store.sidecar_path(saved["path"])) is not None:
                        if self.review is None:
                            raise ValueError("保存先に未反映の付箋メモがあるため、復旧先を開けません")
                        target_sidecar = store.sidecar_path(saved["path"])
                        target_token = store.sidecar_token(target_sidecar)
                        self.destination_token = target_token
                        value = json.loads(Path(target_sidecar).read_text(encoding="utf-8"))
                        store.validate_sidecar(value, saved["path"], saved["pdf"]["page_count"])
                        if value["pdf"] != saved["pdf"] or "review" not in value:
                            raise ValueError("保存先のレビュー記録が一致しません")
                        target_review = reviews.restore(value["review"], saved["pdf"])
                        if target_review["review_id"] != self.review["review_id"] or not reviews.matching(target_review["document"], self.review["document"]):
                            raise ValueError("保存先に別のレビュー記録があります")
                        if store.sidecar_token(target_sidecar) != target_token:
                            raise ValueError("保存先のレビュー記録が変更されました")
                        self.review = target_review
                self._finish_save(saved)
                return
            except Exception as error:
                self.warning = f"保存済みメモの復旧を完了できません: {error}"
                self.writable = False
        elif self.review is not None:
            try:
                self.review = reviews.restore(self.review, self.pdf)
                reviews.validate_positions(self.review, self.tab.pdf_view._document)
                self.stage_text = "前回のレビューを復元しました"
            except ValueError as error:
                self.warning = str(error)
                self.writable = False
        elif self.changes:
            self.stage_text = "前回の未反映メモを復元しました"
        if self.writable and self.sidecar == store.legacy_sidecar_path(self.path):
            self._migrate_legacy()
        self.refresh()

    def refresh(self, list_changed=True):
        if self.panel is None:
            return
        editable = self.ready and self.writable and not self.busy
        if self.review is not None and self.ready:
            self.changes = reviews.pdf_changes(self.review, self.baseline)
        self.panel.add_button.setEnabled(editable)
        self.panel.save.setEnabled(editable)
        self.panel.author.setEnabled(editable)
        self.panel.import_button.setEnabled(editable)
        self.panel.export_button.setEnabled(editable)
        self.panel.merged_action.setEnabled(editable)
        self.panel.open_merged_action.setEnabled(editable)
        self.panel.history_action.setEnabled(self.review is not None and not self.busy)
        if self.review is not None and not self.panel.author.hasFocus():
            self.panel.author.setText(self.review["author"]["name"])
        self.panel.save_as_action.setEnabled(editable)
        self.panel.discard_action.setEnabled(editable and self.pending and self.review is None)
        self.panel.retry.setVisible(self.unsaved and not self.busy)
        if self.warning:
            text = self.warning
        elif self.busy or not self.ready:
            text = self.stage_text
        elif self.unsaved:
            text = "メモ保存中…"
        elif self.pending:
            prefix = self.stage_text + "\n" if self.stage_text else ""
            text = prefix + f"メモ自動保存済み\nPDF未反映：{len(self.changes)}件"
        else:
            text = self.stage_text or "PDFに保存済み"
        self.panel.status.setText(text)
        self.tab.pdf_view.notes_editable = editable
        if list_changed:
            current = self.panel.list.currentItem()
            selected = current.data(Qt.ItemDataRole.UserRole) if current else None
            self.panel.list.clear()
            visible = reviews.visible_notes(self.review, True) if self.review else self.notes
            author_selected = self.panel.author_filter.currentData()
            self.panel.author_filter.blockSignals(True)
            self.panel.author_filter.clear()
            self.panel.author_filter.addItem("記入者：全員", "")
            if self.review:
                authors = {c["author"]["id"]: c["author"]["name"] for c in self.review["comments"].values()}
                for identity, name in sorted(authors.items(), key=lambda pair: pair[1]):
                    self.panel.author_filter.addItem(name or "記入者未設定", identity)
            self.panel.author_filter.setCurrentIndex(max(0, self.panel.author_filter.findData(author_selected)))
            self.panel.author_filter.blockSignals(False)
            filtered = {}
            for note in sorted(visible.values(), key=lambda n: (n["page"], n["order"])):
                comment = self.review["comments"][note["id"]] if self.review else None
                if comment:
                    if author_selected and comment["author"]["id"] != author_selected:
                        continue
                    if self.panel.status_filter.currentData() and comment["status"] != self.panel.status_filter.currentData():
                        continue
                    excluded = self.panel.excluded_filter.currentData()
                    if (excluded == "active" and comment["excluded"]) or (excluded == "excluded" and not comment["excluded"]):
                        continue
                query = self.panel.search.text().casefold()
                if query not in (note["text"] + (comment["memo"] if comment else "")).casefold():
                    continue
                preview = " ".join(note["text"].split())[:65] or "（本文なし）"
                detail = f"　{comment['author']['name'] or '記入者未設定'}　{comment['status']}" if comment else ""
                if comment and comment["excluded"]:
                    detail += "　除外"
                item = QListWidgetItem(color_icon(note["color"]), f"{note['page'] + 1}ページ{detail}\n{preview}")
                item.setData(Qt.ItemDataRole.UserRole, note["id"])
                item.setToolTip(html.escape(note["text"]))
                self.panel.list.addItem(item)
                if note["id"] == selected:
                    self.panel.list.setCurrentItem(item)
                if not comment or not comment["excluded"]:
                    filtered[note["id"]] = note
            all_comments = [c for c in self.review["comments"].values() if not c["deleted"]] if self.review else []
            counts = "／".join(f"{s}{sum(c['status'] == s for c in all_comments)}件" for s in reviews.STATUSES) if all_comments else ""
            self.panel.counts.setText(f"表示{self.panel.list.count()}件／全{len(visible)}件\n{counts}")
            self.tab.pdf_view.set_notes(filtered)
        self.changed.emit()

    def show_panel(self):
        self.panel.show()
        self.tab.notes_splitter.setSizes([max(300, self.tab.notes_splitter.width() - 280), 280])
        self.changed.emit()

    def hide_panel(self):
        self.panel.hide()
        self.tab.pdf_view.set_note_placement(False)
        self.changed.emit()

    def _activate_review(self):
        if self.review is not None:
            return
        self.review = reviews.create(self.pdf, self.baseline)
        bindings = {v: k for k, v in self.review["bindings"].items()}
        for identity, change in self.changes.items():
            stable = bindings.get(identity, identity if identity.startswith(("koji-note:", "koji-review:")) else "koji-review:" + str(uuid.uuid4()))
            note = change["note"]
            reviews.change(self.review, stable, dict(note, id=stable, nm=stable) if note else None)
        self.unsaved = True
        self._autosave_timer.start(0)

    def _review_changed(self):
        self.unsaved = True
        self.warning = ""
        self.stage_text = ""
        self.refresh()
        self._autosave_timer.start(0)

    def _migrate_legacy(self):
        old_sidecar = self.sidecar
        new_sidecar = store.sidecar_path(self.path)
        new_lock = store.EditLock(new_sidecar)
        try:
            if not self._ensure_edit():
                return
            self._activate_review()
            self.refresh()
            new_lock.acquire()
            if store.sidecar_token(new_sidecar) is not None:
                raise ValueError("新しい作業用JSONがすでに存在します")
            store.atomic_json(new_sidecar, self._payload())
            # Verify the durable new record before releasing the legacy lock.
            store.validate_sidecar(json.loads(Path(new_sidecar).read_text(encoding="utf-8")), self.path, self.pdf["page_count"])
            self.lock.release()
            self.lock = new_lock
            self.sidecar = new_sidecar
            self.token = store.sidecar_token(new_sidecar)
            self.durable_changes = copy.deepcopy(self.changes)
            self.durable_review = copy.deepcopy(self.review)
            self.unsaved = False
            self.stage_text = "旧付箋メモを移行しました（元JSONは保持）"
        except Exception as error:
            if self.sidecar == old_sidecar:
                new_lock.release()
            self.warning = f"旧付箋メモの移行に失敗: {error}"

    def set_author(self):
        name = self.panel.author.text().strip()
        if not name or (self.review is not None and name == self.review["author"]["name"]):
            return
        if not self._ensure_edit():
            return
        self._activate_review()
        reviews.set_author(self.review, name)
        self._review_changed()

    def import_reviews(self):
        paths, _ = QFileDialog.getOpenFileNames(self.tab, "レビューを取り込む", str(Path(self.path).parent), "レビューJSON (*.json)")
        if not paths or not self._ensure_edit():
            return
        self._activate_review()
        from .review_ui import ImportDialog
        dialog = ImportDialog(self.review, paths, self.tab, document=self.tab.pdf_view._document)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                state = dialog.resolved_state()
                if state is not None and self._ensure_edit():
                    self.review = state
                    self._review_changed()
                    self.autosave()
        except Exception as error:
            self.warning = f"レビューの取り込みに失敗: {error}"
            self.refresh(False)
        finally:
            dialog.deleteLater()

    def _json_destination(self, caption, default):
        path, _ = QFileDialog.getSaveFileName(self.tab, caption, default, "レビューJSON (*.json)")
        if path and not path.lower().endswith(".json"):
            path += ".json"
        if path and store.canonical(path) in (store.canonical(self.sidecar), store.canonical(store.legacy_sidecar_path(self.path))):
            raise ValueError("提出・集約JSONは作業用JSONと別名にしてください")
        return path

    def export_review(self):
        if not self._ensure_edit():
            return
        self._activate_review()
        try:
            self.set_author()
            value = reviews.submission(self.review)
            path = self._json_destination("レビューを書き出す", reviews.output_path(self.review, self.path, "submission", ".json", value["revision"]))
            if not path:
                return
            # Reserve the revision durably before issuing an external file.
            reviews.accept_export(self.review, value)
            self._review_changed()
            if not self.autosave():
                return
            store.atomic_json(path, value)
            self.stage_text = f"提出用レビューを書き出しました：v{value['revision']:03d}"
        except Exception as error:
            self.warning = f"レビューを書き出せません: {error}"
        self.refresh(False)

    def export_merged(self):
        if not self._ensure_edit():
            return
        self._activate_review()
        try:
            path = self._json_destination("レビュー集約を保存", reviews.output_path(self.review, self.path, "merged", ".json"))
            if path and self.autosave():
                store.atomic_json(path, self.review)
                self.stage_text = "レビュー集約を保存しました"
        except Exception as error:
            self.warning = f"レビュー集約を保存できません: {error}"
        self.refresh(False)

    def open_merged(self):
        path, _ = QFileDialog.getOpenFileName(self.tab, "レビュー集約を開く", str(Path(self.path).parent), "レビューJSON (*.json)")
        if not path or not self._ensure_edit():
            return
        try:
            value = json.loads(Path(path).read_text(encoding="utf-8"))
            state = reviews.restore(value, self.pdf)
            reviews.validate_positions(state, self.tab.pdf_view._document)
            if self.review is not None or self.pending:
                if QMessageBox.question(self.tab, "レビュー集約を開く", "現在の作業内容を選択したレビュー集約で置き換えますか？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
            self.review = state
            self._review_changed()
            self.autosave()
        except Exception as error:
            self.warning = f"レビュー集約を開けません: {error}"
            self.refresh(False)

    def show_history(self):
        if self.review:
            from .review_ui import show_history
            show_history(self.review, self.tab)

    def _ensure_edit(self):
        if not self.ready or not self.writable or self.busy:
            return False
        try:
            if not store.unchanged(self.path, self.pdf):
                raise ValueError("PDFが外部で変更されました。付箋の編集を中止しました")
            self.lock.acquire()
            if store.sidecar_token(self.sidecar) != self.token:
                raise ValueError("付箋メモJSONが別のタブ・アプリで変更されました")
            return True
        except Exception as error:
            self.warning = str(error)
            self.writable = False
            self.refresh(False)
            return False

    def begin_placement(self):
        if self._ensure_edit():
            self.show_panel()
            self.warning = ""
            self.warning = ""
            self.stage_text = "配置する場所をクリックしてください／Escで取消"
            self.refresh(False)
            self.tab.pdf_view.set_note_placement(True)

    def _placement_cancelled(self):
        self.stage_text = ""
        self.refresh(False)

    def add_at(self, page, point):
        self.stage_text = ""
        if not self._ensure_edit():
            return
        identity = "koji-note:" + str(uuid.uuid4())
        note = {"id": identity, "page": page, "x": point.x(), "y": point.y(), "text": "",
                "color": list(store.COLORS["黄"]), "xref": 0, "nm": identity,
                "order": max((n["order"] for n in self.notes.values()), default=-1) + 1}
        self._editor(note, False)

    def edit_note(self, identity):
        candidates = self.tab.pdf_view._notes
        selected = candidates.get(identity)
        if selected:
            overlaps = [n for n in candidates.values() if n["page"] == selected["page"] and
                        self.tab.pdf_view._note_rect(n).intersects(self.tab.pdf_view._note_rect(selected))]
            if len(overlaps) > 1:
                labels = [f"{index + 1}. " + ((self.review['comments'][n['id']]['author']['name'] or '記入者未設定') + '：' if self.review else '') + n["text"][:60]
                          for index, n in enumerate(overlaps)]
                choice, ok = QInputDialog.getItem(self.tab, "重なったコメント", "対象のコメントを選択", labels, 0, False)
                if not ok:
                    return
                identity = overlaps[labels.index(choice)]["id"]
        note = (reviews.visible_notes(self.review, True) if self.review else self.notes).get(identity)
        if note is None or self.busy:
            return
        # Read-only PDFs and recovery errors still permit reading the full note.
        if not self.writable:
            box = QMessageBox(self.tab)
            box.setWindowTitle(f"付箋メモ — {note['page'] + 1}ページ")
            box.setTextFormat(Qt.TextFormat.PlainText)
            box.setText(note["text"])
            box.exec()
            return
        if self._ensure_edit():
            self._editor(note, True)

    def _editor(self, note, existing):
        comment = self.review["comments"].get(note["id"]) if self.review else None
        editor = NoteEditor(note, existing, self.tab, comment=comment,
            author_id=self.review["author"]["id"] if self.review else None,
            page_count=self.pdf["page_count"] if self.review else None)
        center = self.tab.pdf_view.mapToGlobal(self.tab.pdf_view.viewport().rect().center())
        editor.move(center.x() - editor.width() // 2, center.y() - editor.height() // 2)
        if editor.exec() == QDialog.DialogCode.Accepted:
            updated = None if editor.deleted else dict(note, text=editor.body.toPlainText(), color=editor.color.currentData())
            if updated is not None and editor.page_input is not None:
                updated.update(page=editor.page_input.value() - 1, x=editor.x_input.value(), y=editor.y_input.value())
            applied = True
            if comment is None or editor.own:
                applied = self.change_note(note["id"], updated)
            if applied and comment is not None and not editor.deleted and self._ensure_edit():
                status = editor.state_input.currentText()
                if editor.own and reviews.source(comment) != reviews.source(self.review["comments"][note["id"]]) and status == comment["status"]:
                    status = "未確認"
                reviews.judge(self.review, note["id"], status, editor.memo_input.toPlainText(), editor.excluded_input.isChecked())
                self._review_changed()
        editor.deleteLater()
        self.refresh(False)

    def change_note(self, identity, note):
        if not self._ensure_edit():
            return False
        original = self.baseline.get(identity)
        if note is not None:
            store.validate_note(note, self.pdf["page_count"])
            bounds = self.tab.pdf_view._document[note["page"]].rect * self.tab.pdf_view._document[note["page"]].derotation_matrix
            if not pymupdf.Point(note["x"], note["y"]) in bounds:
                self.warning = "コメントの配置位置がページ範囲外です"
                self.refresh(False)
                return False
        if self.review is not None:
            try:
                reviews.change(self.review, identity, note)
                self._review_changed()
                return True
            except ValueError as error:
                self.warning = str(error)
                self.refresh(False)
                return False
        if note == original:
            self.changes.pop(identity, None)
        else:
            self.changes[identity] = {"original": copy.deepcopy(original), "note": copy.deepcopy(note)}
        self.unsaved = True
        self.warning = ""
        self.stage_text = ""
        self.refresh()
        self._autosave_timer.start(0)
        return True

    def _payload(self):
        if self.review is not None:
            self.changes = reviews.pdf_changes(self.review, self.baseline)
        value = {"version": store.VERSION, "pdf": self.pdf, "changes": self.changes}
        if self.review is not None:
            value["review"] = self.review
        if self.transaction is not None:
            value["transaction"] = self.transaction
        return value

    def autosave(self):
        self._autosave_timer.stop()
        if self.busy or not self._ensure_edit():
            return False
        try:
            if self.pending or self.transaction is not None or self.review is not None:
                store.atomic_json(self.sidecar, self._payload())
            elif os.path.exists(self.sidecar):
                # Write an empty durable state before deletion so cleanup failure
                # cannot resurrect discarded changes.
                store.atomic_json(self.sidecar, self._payload())
                self.token = store.sidecar_token(self.sidecar)
                self.durable_changes = copy.deepcopy(self.changes)
                os.unlink(self.sidecar)
            self.token = store.sidecar_token(self.sidecar)
            self.durable_changes = copy.deepcopy(self.changes)
            self.durable_review = copy.deepcopy(self.review)
            self.unsaved = False
            self.warning = ""
            self.refresh(False)
            return True
        except Exception as error:
            self.unsaved = True
            self.warning = f"メモ自動保存に失敗: {error}"
            self.refresh(False)
            return False

    def navigate(self, identity):
        note = (reviews.visible_notes(self.review, True) if self.review else self.notes).get(identity)
        if note and not self._suspended:
            self.tab.pdf_view.navigate_note(note)

    def discard_all(self):
        if not self._ensure_edit():
            return
        if QMessageBox.question(self.tab, "未反映の変更を破棄", "PDF未反映の付箋変更をすべて破棄しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.changes = {}
        self.transaction = None
        self.unsaved = True
        self.refresh()
        self.autosave()

    def save_as(self):
        if not self._ensure_edit():
            return
        self._activate_review()
        self.refresh()
        kind = "submission" if self.review["author"]["name"] and not self.review["receipts"] else "merged"
        default = reviews.output_path(self.review, self.path, kind, ".pdf")
        path, _ = QFileDialog.getSaveFileName(self.tab, "コメント付きPDFに保存", default, "PDF Files (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.save_pdf(path)

    def save_pdf(self, destination=None):
        destination = destination or self.path
        if not self._ensure_edit():
            return False
        window = self.tab.window()
        if hasattr(window, "_find_tab_index"):
            index = window._find_tab_index(destination)
            if index >= 0 and window.tabs.widget(index) is not self.tab:
                self.warning = "保存先のPDFが別のタブで開かれています"
                self.refresh(False)
                return False
        try:
            if store.canonical(destination) != store.canonical(self.path):
                if store.canonical(store.sidecar_path(destination)) == store.canonical(self.sidecar):
                    raise ValueError("保存先と元PDFの付箋メモファイル名が重複します")
                self.destination_lock = store.EditLock(store.sidecar_path(destination))
                self.destination_lock.acquire()
                self.destination_token = store.sidecar_token(store.sidecar_path(destination))
                if self.destination_token is not None:
                    raise ValueError("保存先に未反映の付箋メモJSONがあります")
            self.transaction = None
            # Even save-as with no note changes needs a recovery transaction.
            if not self.autosave():
                raise ValueError("最新のメモをJSONへ保存できません")
            store.atomic_json(self.sidecar, self._payload())
            self.token = store.sidecar_token(self.sidecar)
            self.busy = True
            self.stage_text = "PDF保存準備中…"
            self.warning = ""
            self.tab.pdf_view.set_note_placement(False)
            self.refresh(False)
            self._prepared = self._save_result = None
            self._start("notes_prepare", self.path, destination, self._payload())
            return True
        except Exception as error:
            if self.destination_lock:
                self.destination_lock.release()
                self.destination_lock = None
            self.warning = f"PDF保存を開始できません: {error}"
            self.refresh(False)
            return False

    def _commit_prepared(self):
        try:
            if self._prepared is None:
                raise ValueError("PDF保存の準備結果がありません")
            if store.sidecar_token(self.sidecar) != self.token:
                raise ValueError("付箋メモJSONが保存中に変更されました")
            self.transaction = self._prepared
            store.atomic_json(self.sidecar, self._payload())
            self.token = store.sidecar_token(self.sidecar)
            self.tab._index_job.stop()
            self.tab._reply_job.stop()
            self.tab.pdf_view.suspend_for_note_save()
            self._suspended = True
            self.stage_text = "PDF保存中…"
            self.refresh(False)
            self._start("notes_commit", self.transaction)
        except Exception as error:
            self._failed(str(error))

    def _finish_save(self, result):
        old_path, old_sidecar = self.path, self.sidecar
        try:
            self.tab.pdf_view.reopen_after_note_save(result["path"])
            self._suspended = False
            self.path = result["path"]
            self.tab.pdf_path = self.path
            self.pdf = result["pdf"]
            self.baseline = result["notes"]
            self.changes = {}
            self.durable_changes = {}
            self.unsaved = False
            self.ready = True
            self.writable = bool(self.tab.pdf_view._document.permissions & pymupdf.PDF_PERM_ANNOTATE)
            self.busy = False
            self.warning = ""
            self.stage_text = "PDFに保存済み"
            self.transaction = None
            if self.review is not None:
                self.review["current_pdf"] = copy.deepcopy(self.pdf)
                reviews.event(self.review, "PDF保存", path=self.path)
                self.changes = reviews.pdf_changes(self.review, self.baseline)
            if result.get("index_warning"):
                self.warning = f"PDFは保存済みです。検索索引の更新に失敗: {result['index_warning']}"
            try:
                if store.sidecar_token(old_sidecar) != self.token:
                    raise ValueError("JSONが外部で変更されました")
                if self.review is None:
                    try:
                        os.unlink(old_sidecar)
                    except FileNotFoundError:
                        pass
                else:
                    # Durable output record precedes source-draft cleanup.
                    # A failure leaves the source transaction for recovery.
                    new_sidecar = store.sidecar_path(self.path)
                    if new_sidecar != old_sidecar and store.sidecar_token(new_sidecar) != self.destination_token:
                        self.writable = False
                        raise ValueError("保存先の作業用JSONが外部で変更されました")
                    store.atomic_json(new_sidecar, self._payload())
                    if new_sidecar != old_sidecar and old_sidecar != store.legacy_sidecar_path(old_path):
                        try:
                            os.unlink(old_sidecar)
                        except FileNotFoundError:
                            pass
                    self.durable_review = copy.deepcopy(self.review)
                    self.durable_changes = copy.deepcopy(self.changes)
            except Exception as error:
                self.warning = f"PDFは保存済みです。レビュー記録の保存・整理を完了できません: {error}"
                if self.review is not None:
                    self.unsaved = True
            if store.canonical(self.path) != store.canonical(old_path):
                self.lock.release()
                self.lock = self.destination_lock
                self.destination_lock = None
            self.sidecar = store.sidecar_path(self.path)
            self.token = store.sidecar_token(self.sidecar)
            self.pathChanged.emit(old_path, self.path)
            self.tab._start_body_index()
            self.refresh()
            self.saveFinished.emit(True)
        except Exception as error:
            # Keep the transaction JSON; the output hash prevents replay after
            # a committed PDF cannot be reopened in this session.
            self.writable = False
            self._failed(f"PDF保存後の再表示に失敗: {error}")

    def _failed(self, error):
        was_busy = self.busy
        self.busy = False
        self.stage_text = ""
        self.warning = f"付箋処理に失敗: {error}"
        if self.transaction and not os.path.exists(self.transaction["stage"]):
            # Replace may have succeeded before a process failure. Do not
            # replay changes against an uncertain document in this session.
            self.writable = False
            self.warning += "／保存結果はPDFを開き直して確認してください"
        if self._suspended:
            try:
                self.tab.pdf_view.reopen_after_note_save(self.path)
                self._suspended = False
                self.tab._start_body_index()
            except Exception as reopen_error:
                self.warning += f"／再表示に失敗: {reopen_error}"
                self.writable = False
        if self.destination_lock:
            self.destination_lock.release()
            self.destination_lock = None
        # A verified staging path can be retained in JSON for recovery; no
        # unmanaged output is used as the authoritative document.
        if not self.ready:
            self.writable = False
        self.refresh(False)
        if was_busy:
            self.saveFinished.emit(False)

    def can_close(self):
        if self.busy:
            return False
        if not self.unsaved:
            return True
        self._autosave_timer.stop()
        if self.autosave():
            return True
        box = QMessageBox(self.tab)
        box.setWindowTitle("メモを保存できません")
        box.setText("メモの変更をJSONに保存できていません。")
        retry = box.addButton("再保存", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("未保存の変更を破棄して閉じる", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("キャンセル", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is retry:
            return self.autosave()
        if box.clickedButton() is discard:
            self.changes = copy.deepcopy(self.durable_changes)
            self.review = copy.deepcopy(self.durable_review)
            self.unsaved = False
            self.refresh()
            return True
        return False

    def close(self):
        self._closed = True
        self._autosave_timer.stop()
        self.job.stop()
        self.lock.release()
        if self.destination_lock:
            self.destination_lock.release()
