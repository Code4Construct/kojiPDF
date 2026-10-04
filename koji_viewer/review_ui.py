"""Review import preview, explicit conflict choices and history dialogs."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout)

from . import review


def buttons(dialog, layout, accept="取り込む"):
    row = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    row.button(QDialogButtonBox.StandardButton.Ok).setText(accept)
    row.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
    row.accepted.connect(dialog.accept)
    row.rejected.connect(dialog.reject)
    layout.addWidget(row)


def describe(value):
    if value is None:
        return "（記録なし）"
    source = review.source(value) if "revision" in value else value
    if "note" not in source:
        return "\n".join(f"{dict(status='状態', memo='取りまとめメモ', excluded='除外').get(k, k)}：{v}" for k, v in source.items())
    note = source["note"]
    color = "#" + "".join(f"{round(v * 255):02x}" for v in note["color"])
    return ("【削除】\n" if source["deleted"] else "") + f"{note['page'] + 1}ページ　位置：{note['x']:g}, {note['y']:g}　色：{color}\n\n{note['text']}"


class ImportDialog(QDialog):
    def __init__(self, state, paths, parent=None, document=None):
        super().__init__(parent)
        self.setWindowTitle("レビューの取り込み")
        self.resize(740, 430)
        self.state = copy.deepcopy(state)
        self.entries = []
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("対象PDF：" + state["document"]["name"]))
        layout.addWidget(QLabel("取り込むファイルを選択してください。競合は内容を比較して採用を選びます。"))
        self.table = QTableWidget(len(paths), 3)
        self.table.setHorizontalHeaderLabels(["選択", "ファイル", "判定・内容"])
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 380)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        preview = copy.deepcopy(state)
        for row, path in enumerate(paths):
            check = QCheckBox()
            value = None
            try:
                value = json.loads(Path(path).read_text(encoding="utf-8"))
                proposed, result = review.merge(preview, value)
                if document is not None:
                    review.validate_positions(value, document)
                label = result["label"] + f"：追加{result['added']}件・更新{result['updated']}件・削除{result['deleted']}件・競合{len(result['conflicts'])}件"
                valid = result["label"] not in ("古い版", "取り込み済み")
                if not result["conflicts"]:
                    preview = proposed
            except Exception as error:
                label, valid = str(error), False
            check.setChecked(valid)
            check.setEnabled(valid)
            self.entries.append((check, value))
            self.table.setCellWidget(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem(Path(path).name))
            self.table.setItem(row, 2, QTableWidgetItem(label))
        layout.addWidget(self.table)
        buttons(self, layout)

    def resolved_state(self):
        state = copy.deepcopy(self.state)
        for check, incoming in self.entries:
            if not check.isChecked():
                continue
            proposed, result = review.merge(state, incoming)
            choices = {}
            for identity in result["conflicts"]:
                dialog = ConflictDialog(state["comments"].get(identity), incoming["comments"][identity], self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    return None
                choices[identity] = dialog.choice.currentData()
            state = review.merge(state, incoming, choices)[0] if choices else proposed
        return state


class ConflictDialog(QDialog):
    def __init__(self, current, incoming, parent=None):
        super().__init__(parent)
        self.setWindowTitle("コメントの競合")
        self.resize(740, 420)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("同じコメントに異なる変更があります。採用する内容を選択してください。"))
        columns = QHBoxLayout()
        for label, value in (("現在の内容", current), ("提出された内容", incoming)):
            column = QVBoxLayout()
            column.addWidget(QLabel(label))
            body = QTextEdit()
            body.setReadOnly(True)
            body.setPlainText(describe(value))
            column.addWidget(body)
            columns.addLayout(column)
        layout.addLayout(columns)
        self.choice = QComboBox()
        self.choice.addItem("現在の内容を保持", "current")
        self.choice.addItem("提出された内容を採用", "incoming")
        layout.addWidget(self.choice)
        buttons(self, layout, "選択を確定")


def show_history(state, parent):
    dialog = QDialog(parent)
    dialog.setWindowTitle("レビュー履歴")
    dialog.resize(700, 480)
    layout = QVBoxLayout(dialog)
    text = QTextEdit()
    text.setReadOnly(True)
    entries = []
    for item in reversed(state["history"]):
        try:
            stamp = datetime.fromisoformat(item["at"]).astimezone(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M:%S")
        except ValueError:
            stamp = item["at"]
        action = item["action"].replace(":added", "：追加").replace(":updated", "：更新").replace(":deleted", "：削除")
        lines = [stamp + "　" + action]
        if "author" in item:
            lines.append("記入者：" + item["author"])
        if "revision" in item:
            lines.append(f"提出版：v{item['revision']:03d}")
        if "name" in item:
            lines.append("記入者：" + item["name"])
        for key, label in (("before", "変更前"), ("after", "変更後"), ("incoming", "提出内容")):
            if key in item:
                lines.append(label + "\n" + describe(item[key]))
        entries.append("\n".join(lines))
    text.setPlainText("\n\n────────────────────\n\n".join(entries) or "履歴なし")
    layout.addWidget(text)
    close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    close.rejected.connect(dialog.reject)
    layout.addWidget(close)
    dialog.exec()
