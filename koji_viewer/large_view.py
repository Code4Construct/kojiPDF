"""On-demand PyMuPDF page display for PDFs too large for Qt PDF view."""

import bisect
import math
import os
import queue
import re
import threading

import pymupdf
from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QLabel, QMessageBox, QScrollArea


class LargePageNavigator(QObject):
    currentPageChanged = Signal(int)

    def __init__(self, view):
        super().__init__(view)
        self._view = view
        self._current_page = 0

    def currentPage(self):
        return self._current_page

    def jump(self, page: int, _location: QPointF):
        if not 0 <= page < self._view.page_count:
            return
        if page != self._current_page:
            self._current_page = page
            self.currentPageChanged.emit(page)
        self._view.render_page()


class PageImageLabel(QLabel):
    def __init__(self, view):
        super().__init__()
        self._view = view
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        cursor = (Qt.CursorShape.PointingHandCursor if
                  self._view.link_at(event.position()) else Qt.CursorShape.ArrowCursor)
        self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._view.activate_link(event.position()):
            event.accept()
            return
        super().mouseReleaseEvent(event)


class LargePdfPageView(QScrollArea):
    """Render only the requested page, keeping memory bounded."""

    searchProgress = Signal(str, int, bool)
    searchFailed = Signal(str, str)
    MAX_PIXELS = 16_000_000

    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self._document = pymupdf.open(pdf_path)
        self._links = []
        self._render_scale = 1.0
        self.page_count = self._document.page_count
        self._navigator = LargePageNavigator(self)
        self._zoom_mode = QPdfView.ZoomMode.FitToWidth
        self._label = PageImageLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("background: white")
        self.setWidget(self._label)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("QScrollArea { background: #808080; border: 0; }")
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.render_page)
        self._search_query = ""
        self._search_pages = []
        self._search_done = True
        self._search_cancel = None
        self._search_queue = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._launch_search)
        self._search_poll = QTimer(self)
        self._search_poll.setInterval(50)
        self._search_poll.timeout.connect(self._poll_search)

    def pageNavigator(self):
        return self._navigator

    def zoomMode(self):
        return self._zoom_mode

    def setZoomMode(self, mode):
        self._zoom_mode = mode
        self.render_page()

    def render_page(self):
        if self._document is None or not self.page_count:
            return
        page = self._document.load_page(self._navigator.currentPage())
        bounds = page.rect
        width = max(1, self.viewport().width() - 16)
        height = max(1, self.viewport().height() - 16)
        scale = width / bounds.width
        if self._zoom_mode == QPdfView.ZoomMode.FitInView:
            scale = min(scale, height / bounds.height)
        scale = min(scale, math.sqrt(self.MAX_PIXELS / (bounds.width * bounds.height)))
        scale = max(0.05, scale)
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale),
                                 colorspace=pymupdf.csRGB, alpha=False)
        self._render_scale = pixmap.width / bounds.width
        self._links = page.get_links()
        image = QImage(pixmap.samples, pixmap.width, pixmap.height,
                       pixmap.stride, QImage.Format.Format_RGB888).copy()
        display = QPixmap.fromImage(image)
        if self._search_query:
            painter = QPainter(display)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 230, 0, 110))
            for rect in page.search_for(self._search_query)[:200]:
                painter.drawRect(QRectF(rect.x0 * self._render_scale,
                                        rect.y0 * self._render_scale,
                                        rect.width * self._render_scale,
                                        rect.height * self._render_scale))
            painter.end()
        self._label.setPixmap(display)
        self._label.resize(image.size())

    def link_at(self, position):
        if self._document is None:
            return None
        point = pymupdf.Point(position.x() / self._render_scale,
                              position.y() / self._render_scale)
        for link in self._links:
            if point in link["from"] and (link.get("uri") or link.get("file")):
                return link
        return None

    def _raw_file_path(self, link):
        xref = link.get("xref")
        if not xref:
            return None
        obj = self._document.xref_object(xref)
        match = re.search(r"/(?:URI|UF|F)\s*<([0-9A-Fa-f]+)>", obj)
        if match is not None:
            raw = bytes.fromhex(match.group(1))
        else:
            match = re.search(r"/(?:URI|UF|F)\s*\(((?:\\.|[^\\)])*)\)", obj)
            if match is None:
                return None
            literal = match.group(1).encode("latin-1")

            def unescape(m):
                escaped = m.group(1)
                if escaped[:1] in (b"\r", b"\n"):
                    return b""
                if escaped[:1] in b"01234567":
                    return bytes((int(escaped, 8),))
                return {b"n": b"\n", b"r": b"\r", b"t": b"\t",
                        b"b": b"\b", b"f": b"\f"}.get(escaped, escaped)

            raw = re.sub(rb"\\([0-7]{1,3}|\r?\n|.)", unescape, literal)
        encodings = ("utf-16",) if raw.startswith((b"\xfe\xff", b"\xff\xfe")) else (
            "utf-8", "cp932")
        for encoding in encodings:
            try:
                decoded = raw.decode(encoding)
                return QUrl(decoded).toLocalFile() if decoded.startswith("file:") else decoded
            except UnicodeError:
                continue
        return None

    def activate_link(self, position):
        link = self.link_at(position)
        if link is None:
            return False
        target = link.get("uri") or link.get("file")
        url = QUrl(target)
        scheme = "file" if link.get("file") and not link.get("uri") else url.scheme().lower()
        if scheme not in ("http", "https", "mailto", "file"):
            return False
        if scheme == "file":
            file_path = (self._raw_file_path(link) or url.toLocalFile() or
                         target.removeprefix("file:"))
            file_path = file_path.replace("\u00a5", "\\")
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.path.dirname(self.pdf_path), file_path)
            file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "リンク先が見つかりません", file_path)
                return True
            url = QUrl.fromLocalFile(file_path)
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "リンクを開けません", url.toString())
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(100)

    def start_search(self, query: str):
        if self._search_cancel is not None:
            self._search_cancel.set()
        self._search_timer.stop()
        self._search_poll.stop()
        self._search_query = query.strip()
        self._search_pages = []
        self._search_done = not bool(self._search_query)
        self._search_queue = None
        self.render_page()
        if self._search_query:
            self._search_timer.start(300)
        else:
            self.searchProgress.emit("", 0, True)

    def _launch_search(self):
        if self._document is None or not self._search_query:
            return
        results = queue.Queue(maxsize=200)
        cancelled = threading.Event()
        self._search_queue = results
        self._search_cancel = cancelled
        query = self._search_query
        path = self.pdf_path

        def scan():
            try:
                with pymupdf.open(path) as document:
                    for page_number in range(document.page_count):
                        if cancelled.is_set():
                            return
                        if document.load_page(page_number).search_for(query):
                            while not cancelled.is_set():
                                try:
                                    results.put(("hit", page_number), timeout=0.1)
                                    break
                                except queue.Full:
                                    pass
                if not cancelled.is_set():
                    results.put(("done", None))
            except Exception as error:  # noqa: BLE001
                if not cancelled.is_set():
                    results.put(("error", str(error)))

        threading.Thread(target=scan, daemon=True, name="kojiPDF-large-search").start()
        self._search_poll.start()

    def _poll_search(self):
        if self._search_queue is None:
            return
        changed = False
        error_message = None
        for _ in range(200):
            try:
                kind, value = self._search_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "hit":
                self._search_pages.append(value)
                changed = True
            else:
                self._search_done = True
                self._search_poll.stop()
                if kind == "error":
                    error_message = value
                changed = True
                break
        if changed:
            if len(self._search_pages) == 1:
                self._navigator.jump(self._search_pages[0], QPointF(0, 0))
            self.searchProgress.emit(self._search_query, len(self._search_pages), self._search_done)
        if error_message is not None:
            self.searchFailed.emit(self._search_query, error_message)

    def next_search_match(self):
        if not self._search_pages:
            return
        current = self._navigator.currentPage()
        position = bisect.bisect_right(self._search_pages, current)
        self._navigator.jump(self._search_pages[position % len(self._search_pages)], QPointF(0, 0))

    @property
    def search_result_count(self):
        return len(self._search_pages)

    def close_document(self):
        self._resize_timer.stop()
        self._search_timer.stop()
        self._search_poll.stop()
        if self._search_cancel is not None:
            self._search_cancel.set()
        if self._document is not None:
            self._document.close()
            self._document = None
