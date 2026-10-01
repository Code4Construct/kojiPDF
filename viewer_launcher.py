"""Open the integrated viewer without coupling it to PDF creation internals."""

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication


class ViewerLauncher(QObject):
    viewer_closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window = None

    @property
    def is_open(self):
        return self._window is not None and self._window.isVisible()

    def open(self, pdf_path=None):
        if QApplication.instance() is None:
            raise RuntimeError("The viewer requires an existing QApplication")

        if self._window is None:
            from koji_viewer.main import APP_STYLESHEET, MainWindow

            window = MainWindow()
            window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
            window.setStyleSheet(APP_STYLESHEET)
            icon_path = Path(__file__).parent / "koji_viewer" / "assets" / "icons" / "kojiPDFviewer.ico"
            if icon_path.is_file():
                window.setWindowIcon(QIcon(str(icon_path)))
            window.installEventFilter(self)
            self._window = window
            window.showMaximized()
        else:
            window = self._window
            window.showMaximized()
            window.raise_()
            window.activateWindow()

        if pdf_path:
            path = Path(pdf_path)
            if path.is_file() and path.suffix.lower() == ".pdf":
                window.load_pdf(str(path))
        return window

    def eventFilter(self, watched, event):
        if watched is self._window and event.type() == QEvent.Type.Close:
            watched.removeEventFilter(self)
            self._window = None
            QTimer.singleShot(0, self.viewer_closed.emit)
        return super().eventFilter(watched, event)
