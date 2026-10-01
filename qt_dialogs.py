"""Qt dialogs shared by the PDF engine and Office conversion."""
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QVBoxLayout,
)

_bridge = None


def set_bridge(bridge):
    global _bridge
    _bridge = bridge


def _invoke(callback, default):
    if _bridge is not None:
        return _bridge.invoke(callback, default=default)
    if QApplication.instance() is None:
        raise RuntimeError("Qt dialog requested before QApplication initialization")
    return callback()


def _action_dialog(title, message, detail, actions, default):
    dialog = QDialog(QApplication.activeWindow())
    dialog.setWindowTitle(title)
    dialog.resize(940, 560 if detail else 390)
    layout = QVBoxLayout(dialog)
    if message:
        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)
    if detail:
        report = QPlainTextEdit()
        report.setPlainText(detail)
        report.setReadOnly(True)
        layout.addWidget(report, 1)
    buttons = QHBoxLayout()
    selected = {"value": default}
    for code, caption, color in actions:
        button = QPushButton(caption)
        button.setStyleSheet(f"background-color: {color}; color: white; padding: 9px")
        button.clicked.connect(lambda _checked=False, value=code: (selected.__setitem__("value", value), dialog.accept()))
        buttons.addWidget(button)
    layout.addLayout(buttons)
    dialog.exec()
    return selected["value"]


def choose_save_warning_action(warnings):
    message = (
        "PDF保存時にMuPDF警告が検出されました。\n"
        "修復は結合後PDFを garbage4 で保存し直します。\n"
        "大容量PDFでは修復に非常に時間がかかるため、通常保存PDFで続行する選択も検討してください。"
    )
    return _invoke(lambda: _action_dialog(
        "PDF保存エラーの処理", message, warnings or "MuPDF warning details were empty.",
        [("repair", "修復: garbage4", "#1976D2"), ("ignore", "無視: 続行", "#388E3C"),
         ("abort", "終了", "#D32F2F")], "abort",
    ), "abort")


def show_pdf_check_report(title, report, actions=None):
    actions = actions or [("ok", "OK", "#263849")]
    default = actions[0][0]
    return _invoke(lambda: _action_dialog(title, "", report, actions, default), default)


def confirm_continue(message):
    def ask():
        return QMessageBox.question(
            QApplication.activeWindow(), "工事検査用PDFファイル作成アプリ", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes
    return _invoke(ask, False)