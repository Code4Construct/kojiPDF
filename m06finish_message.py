"""Confirmation dialog used by the PDF worker."""

import qt_dialogs


def main(message):
    return qt_dialogs.confirm_continue(message)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    main('処理が終わりました。プログラムを続けますか？')
