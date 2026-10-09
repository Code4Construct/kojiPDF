"""Continuous, bounded-memory PyMuPDF display shared by all PDF sizes."""
import bisect
import html
import os
import re
from collections import OrderedDict
from enum import IntEnum

import pymupdf
from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QKeySequence, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QMainWindow, QMenu, QMessageBox, QToolTip

from .pdf_jobs import PdfJob, TileRenderer

# 本文に文字として書かれているだけのURL・メールアドレス(PDFにリンクとして埋め込まれていないもの)
_TEXT_LINK_RE = re.compile(
    r"(?P<url>(?:https?://|www\.)[A-Za-z0-9\-._~:/?#\[\]@!$&'*+,;=%]+)"
    r"|(?P<mail>[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)")
_OPENABLE_SCHEMES = ("http", "https", "mailto", "file")


class ZoomMode(IntEnum):
    FitToWidth = 0
    FitInView = 1


class PdfNavigator(QObject):
    currentPageChanged = Signal(int)

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self._page = 0

    def currentPage(self):
        return self._page

    def _set_page(self, number):
        if number != self._page:
            self._page = number
            self.currentPageChanged.emit(number)

    def jump(self, number, location=QPointF()):
        if self.view._document is not None and 0 <= number < self.view.page_count:
            self._set_page(number)
            self.view._jumping = True
            page = self.view._document[number]
            point = pymupdf.Point(location.x(), location.y()) * page.rotation_matrix
            self.view.verticalScrollBar().setValue(round(
                self.view.page_offset(number) + point.y * self.view._scales[number]))
            self.view._jumping = False
            self.view.viewport().update()


class PdfPageView(QAbstractScrollArea):
    searchMatchChanged = Signal(int)
    searchProgress = Signal(str, int, bool)
    searchFailed = Signal(str, str)
    renderFailed = Signal(str)
    notePlacementRequested = Signal(int, object)
    noteActivated = Signal(str)
    notePlacementCancelled = Signal()
    CACHE_BYTES = 64 * 1024 * 1024
    TILE_SIZE = 512
    PAGE_GAP = 12
    MARGIN = 6
    WHEEL_SCROLL_MULTIPLIER = 12

    def __init__(self, pdf_path, parent=None, link_base_path=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.link_base_path = link_base_path or pdf_path
        self._document = pymupdf.open(pdf_path)
        if self._document.needs_pass:
            self._document.close()
            raise ValueError("パスワード付きPDFは開けません")
        self.page_count = self._document.page_count
        self._sizes = [(page.rect.width, page.rect.height) for page in self._document]
        self._navigator = PdfNavigator(self)
        self._zoom_mode = ZoomMode.FitToWidth
        self._zoom_factor = 1.0
        self._offsets = []
        self._scales = []
        self._content_width = 0
        self._cache = OrderedDict()
        self.cache_bytes = 0
        self._renderer = TileRenderer(pdf_path, self)
        self._renderer.ready.connect(self._tile_ready)
        self._failed_tiles = set()
        self._render_error = None
        self._chars_cache = OrderedDict()
        self._links_cache = OrderedDict()
        self._hover_link = None  # (ページ番号, リンク) マウスが乗っているリンク
        self.background_color = QColor("#808080")
        self._selection = None
        self._press = None
        self.pan_mode = False
        self._space_pressed = False
        self._pan_position = None
        self._drag_position = None
        self._drag_timer = QTimer(self)
        self._drag_timer.setInterval(30)
        self._drag_timer.timeout.connect(self._drag_scroll)
        self._jumping = False
        self._notes = {}
        self._notes_by_page = {}
        self.notes_editable = False
        self.note_placement = False
        self._note_press = None
        self._highlight_note = None
        self._highlight_timer = QTimer(self)
        self._highlight_timer.setSingleShot(True)
        self._highlight_timer.timeout.connect(self._clear_note_highlight)
        self._search_query = ""
        self._search_results = []
        self._search_rects = {}
        self.search_done = True
        self.active_search_index = -1
        self._search_anchor_page = None
        self._search_job = PdfJob(self)
        self._search_job.message.connect(self._search_message)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._launch_search)
        self.verticalScrollBar().valueChanged.connect(self._scrolled)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setMouseTracking(True)
        self._layout_pages()

    def pageNavigator(self):
        return self._navigator

    def zoomMode(self):
        return self._zoom_mode

    def setZoomMode(self, mode):
        anchor = self._view_anchor()
        self._zoom_mode = ZoomMode(int(mode))
        self._zoom_factor = 1.0
        self._layout_pages()
        self._restore_anchor(anchor)

    def _view_anchor(self):
        """いま画面の上端にあるページと、そのページ内の位置(0=上端〜1=下端)。"""
        if not self._offsets:
            return None
        number = self._navigator.currentPage()
        height = self._sizes[number][1] * self._scales[number]
        fraction = (self.verticalScrollBar().value() - self._offsets[number]) / max(1.0, height)
        return number, min(1.0, max(0.0, fraction))

    def _restore_anchor(self, anchor):
        if anchor is None or not self._offsets:
            return
        number, fraction = anchor
        number = min(number, self.page_count - 1)
        if self._zoom_mode == ZoomMode.FitInView:
            fraction = 0.0  # ページ全体表示では、そのページがちょうど画面に収まるよう上端に合わせる
        height = self._sizes[number][1] * self._scales[number]
        self._jumping = True
        self.verticalScrollBar().setValue(round(self._offsets[number] + fraction * height))
        self._jumping = False
        self._navigator._set_page(number)
        self.viewport().update()

    def page_offset(self, number):
        return self._offsets[number]

    def _layout_pages(self):
        if self._document is None:
            return
        width = max(1, self.viewport().width() - self.MARGIN * 2)
        height = max(1, self.viewport().height() - self.PAGE_GAP)
        offset = self.MARGIN
        self._offsets, self._scales = [], []
        for page_width, page_height in self._sizes:
            scale = width / page_width
            if self._zoom_mode == ZoomMode.FitInView:
                scale = min(scale, height / page_height)
            scale *= self._zoom_factor
            self._offsets.append(offset)
            self._scales.append(scale)
            offset += page_height * scale + self.PAGE_GAP
        self.verticalScrollBar().setRange(0, min(2_147_483_647, max(0, round(offset - self.PAGE_GAP + self.MARGIN - self.viewport().height()))))
        self.verticalScrollBar().setPageStep(self.viewport().height())
        content_width = max((w * s for (w, _), s in zip(self._sizes, self._scales)), default=0)
        self._content_width = content_width + self.MARGIN * 2
        self.horizontalScrollBar().setRange(0, max(0, round(content_width + self.MARGIN * 2 - self.viewport().width())))
        self.horizontalScrollBar().setPageStep(self.viewport().width())
        self.viewport().update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y() or event.pixelDelta().y()
            if delta:
                position = event.position()
                number, point = self.viewport_to_page(position)
                self._zoom_factor = max(0.25, min(8.0, self._zoom_factor * 1.15 ** (delta / 120)))
                self._layout_pages()
                if number is not None:
                    updated = self.page_to_viewport(number, point)
                    self.verticalScrollBar().setValue(round(self.verticalScrollBar().value() + updated.y() - position.y()))
                    self.horizontalScrollBar().setValue(round(self.horizontalScrollBar().value() + updated.x() - position.x()))
            event.accept()
            return
        scrollbar = self.verticalScrollBar()
        original_step = scrollbar.singleStep()
        scrollbar.setSingleStep(original_step * self.WHEEL_SCROLL_MULTIPLIER)
        try:
            super().wheelEvent(event)
        finally:
            scrollbar.setSingleStep(original_step)

    def resizeEvent(self, event):
        # ウインドウの大きさ・一覧の表示/非表示・全画面の切り替えで、見ていた位置を保つ
        anchor = self._view_anchor()
        super().resizeEvent(event)
        self._layout_pages()
        self._restore_anchor(anchor)

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()

    def _scrolled(self, *_args):
        if self._offsets and not self._jumping:
            probe = self.verticalScrollBar().value() + self.MARGIN + 1
            number = max(0, bisect.bisect_right(self._offsets, probe) - 1)
            self._navigator._set_page(min(number, self.page_count - 1))
        self.viewport().update()

    def _page_rect(self, number):
        width, height = self._sizes[number]
        scale = self._scales[number]
        content_width = max(self.viewport().width(), self._content_width)
        return QRectF((content_width - width * scale) / 2 - self.horizontalScrollBar().value(),
                      self._offsets[number] - self.verticalScrollBar().value(),
                      width * scale, height * scale)

    def viewport_to_page(self, position):
        if self._document is None or not self._offsets:
            return None, None
        number = max(0, bisect.bisect_right(self._offsets,
                     position.y() + self.verticalScrollBar().value()) - 1)
        number = min(number, self.page_count - 1)
        rect = self._page_rect(number)
        if not rect.contains(QPointF(position)):
            return None, None
        scale = self._scales[number]
        point = pymupdf.Point((position.x() - rect.x()) / scale,
                              (position.y() - rect.y()) / scale)
        return number, point * self._document[number].derotation_matrix

    def page_to_viewport(self, number, point):
        rotated = point * self._document[number].rotation_matrix
        rect = self._page_rect(number)
        scale = self._scales[number]
        return QPointF(rect.x() + rotated.x * scale, rect.y() + rotated.y * scale)

    def _overlay_rect(self, number, bbox):
        box = pymupdf.Rect(bbox) * self._document[number].rotation_matrix
        scale = self._scales[number]
        rect = self._page_rect(number)
        return QRectF(rect.x() + box.x0 * scale, rect.y() + box.y0 * scale,
                      box.width * scale, box.height * scale)

    def _tile(self, page, scale, x, y, dpr):
        key = (page.number, round(scale, 8), x, y, dpr)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        clip = pymupdf.Rect(x / scale, y / scale,
                            (x + self.TILE_SIZE) / scale, (y + self.TILE_SIZE) / scale) & page.rect
        if key not in self._failed_tiles and not self._render_error:
            self._renderer.request(key, clip)
        return None

    def _tile_ready(self, key, payload):
        if self._document is None:
            return
        if isinstance(payload, str):
            self._failed_tiles.add(key)
            if key is None:
                self._render_error = payload
            self.renderFailed.emit(payload)
            self.viewport().update()
            return
        width, height, stride, samples = payload
        image = QImage(samples, width, height, stride, QImage.Format.Format_RGB888).copy()
        dpr = key[-1]
        image.setDevicePixelRatio(dpr)
        cost = image.sizeInBytes()
        while self._cache and self.cache_bytes + cost > self.CACHE_BYTES:
            _, old = self._cache.popitem(last=False)
            self.cache_bytes -= old.sizeInBytes()
        if cost <= self.CACHE_BYTES:
            self._cache[key] = image
            self.cache_bytes += cost
        # Invalidate only the completed tile; a full repaint can thrash the LRU
        # when a very high-DPI viewport itself exceeds the cache budget.
        number, _scale, x, y, _dpr = key
        rect = self._page_rect(number)
        region = QRectF(rect.x() + x, rect.y() + y, width / dpr, height / dpr)
        self.viewport().update(region.toAlignedRect())

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setClipRegion(event.region())
        painter.fillRect(self.viewport().rect(), self.background_color)
        if self._document is None or not self._offsets:
            return
        top = self.verticalScrollBar().value()
        first = max(0, bisect.bisect_right(self._offsets, top) - 1)
        dpr = self.devicePixelRatioF()
        for number in range(first, self.page_count):
            rect = self._page_rect(number)
            if rect.top() > self.viewport().height():
                break
            visible = rect.intersected(QRectF(self.viewport().rect())).intersected(QRectF(event.rect()))
            if visible.isEmpty():
                continue
            painter.fillRect(rect, Qt.GlobalColor.white)
            if self._render_error:
                painter.setPen(Qt.GlobalColor.black)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "ページを表示できません")
                continue
            scale = self._scales[number]
            page = self._document[number]
            left = max(0, int((visible.left() - rect.left()) // self.TILE_SIZE) * self.TILE_SIZE)
            start_y = max(0, int((visible.top() - rect.top()) // self.TILE_SIZE) * self.TILE_SIZE)
            try:
                for y in range(start_y, int(visible.bottom() - rect.top()) + 1, self.TILE_SIZE):
                    for x in range(left, int(visible.right() - rect.left()) + 1, self.TILE_SIZE):
                        image = self._tile(page, scale, x, y, dpr)
                        if image is not None:
                            painter.drawImage(QPointF(rect.x() + x, rect.y() + y), image)
            except Exception as error:
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "ページを表示できません")
                self.renderFailed.emit(str(error))
            painter.setPen(Qt.PenStyle.NoPen)
            for bbox in self._search_rects.get(number, []):
                painter.setBrush(QColor(255, 230, 0, 100))
                painter.drawRect(self._overlay_rect(number, bbox))
            if 0 <= self.active_search_index < len(self._search_results):
                active_page, bbox = self._search_results[self.active_search_index]
                if active_page == number:
                    painter.setBrush(QColor(255, 140, 0, 120))
                    painter.drawRect(self._overlay_rect(number, bbox))
            if self._selection:
                start, end = sorted(self._selection)
                if start[0] <= number <= end[0]:
                    chars = self._characters(number)
                    begin = start[1] if number == start[0] else 0
                    finish = end[1] if number == end[0] else len(chars) - 1
                    painter.setBrush(QColor(70, 135, 240, 100))
                    for char in chars[begin:finish + 1]:
                        painter.drawRect(self._overlay_rect(number, char[1]))
            if self._hover_link is not None and self._hover_link[0] == number:
                painter.save()
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                for bbox in self._hover_link[1]["rects"]:
                    box = self._overlay_rect(number, bbox).adjusted(-1, -1, 1, 1)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(37, 99, 235, 36))
                    painter.drawRoundedRect(box, 2, 2)
                    painter.setPen(QPen(QColor(37, 99, 235, 230), 1.5))
                    painter.drawLine(box.bottomLeft(), box.bottomRight())
                painter.restore()
            for note in self._notes_by_page.get(number, ()):
                box = self._note_rect(note)
                if note["id"] == self._highlight_note:
                    painter.setPen(QPen(QColor("#2d6cdf"), 3))
                    painter.setBrush(QColor(70, 135, 240, 50))
                    painter.drawRoundedRect(box.adjusted(-5, -5, 5, 5), 4, 4)
                painter.setPen(QPen(QColor("#665c35"), 1))
                painter.setBrush(QColor.fromRgbF(*note["color"]))
                painter.drawRoundedRect(box, 2, 2)
                painter.setBrush(QColor(255, 255, 255, 160))
                painter.drawPolygon(QPolygonF([box.topRight() - QPointF(6, 0), box.topRight(),
                                               box.topRight() + QPointF(0, 6)]))
                painter.drawLine(box.topLeft() + QPointF(4, 7), box.topLeft() + QPointF(11, 7))
                painter.drawLine(box.topLeft() + QPointF(4, 11), box.topLeft() + QPointF(13, 11))
                count = sum(self._note_rect(other).intersects(box) for other in self._notes_by_page.get(number, ()))
                if count > 1:
                    badge = box.adjusted(8, -7, 8, -7)
                    painter.setPen(QPen(QColor("#ffffff"), 1))
                    painter.setBrush(QColor("#315caa"))
                    painter.drawEllipse(badge)
                    painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(count))

    def set_notes(self, notes):
        self._notes = notes
        self._notes_by_page = {}
        for note in notes.values():
            self._notes_by_page.setdefault(note["page"], []).append(note)
        self.viewport().update()

    def _note_rect(self, note):
        anchor = self.page_to_viewport(note["page"], pymupdf.Point(note["x"], note["y"]))
        page_rect = self._page_rect(note["page"])
        # Rotation can put an unrotated top-left anchor on a visible edge.
        x = max(page_rect.left(), min(anchor.x(), page_rect.right() - 18))
        y = max(page_rect.top(), min(anchor.y(), page_rect.bottom() - 18))
        return QRectF(x, y, 18, 18)

    def note_at(self, position):
        if self._document is None:
            return None
        number, _ = self.viewport_to_page(position)
        if number is not None:
            for note in reversed(self._notes_by_page.get(number, ())):
                if self._note_rect(note).adjusted(-2, -2, 2, 2).contains(QPointF(position)):
                    return note
        return None

    def set_note_placement(self, enabled):
        previous = self.note_placement
        self.note_placement = bool(enabled and self.notes_editable)
        self._press = None
        self._note_press = None
        self._drag_timer.stop()
        self.viewport().setCursor(Qt.CursorShape.CrossCursor if self.note_placement else Qt.CursorShape.ArrowCursor)
        if self.note_placement:
            self.setFocus()
        elif previous:
            self.notePlacementCancelled.emit()

    def navigate_note(self, note):
        if self._document is None:
            return
        self._navigator.jump(note["page"], QPointF(note["x"], note["y"]))
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - self.viewport().height() // 4)
        self._highlight_note = note["id"]
        self._highlight_timer.start(1800)
        self.viewport().update()

    def _clear_note_highlight(self):
        self._highlight_note = None
        self.viewport().update()

    def render_page(self):
        self.viewport().update()

    def _characters(self, number):
        if number in self._chars_cache:
            self._chars_cache.move_to_end(number)
            return self._chars_cache[number]
        data = self._document[number].get_text("rawdict", flags=(
            pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES))
        chars = []
        for block_index, block in enumerate(data["blocks"]):
            for line_index, line in enumerate(block.get("lines", [])):
                for span in line["spans"]:
                    for char in span["chars"]:
                        chars.append((char["c"], tuple(char["bbox"]), (block_index, line_index)))
        self._chars_cache[number] = chars
        while len(self._chars_cache) > 8:
            self._chars_cache.popitem(last=False)
        return chars

    def _character_at(self, number, point):
        chars = self._characters(number)
        if not chars:
            return None
        def distance(index):
            rect = pymupdf.Rect(chars[index][1])
            dx = max(rect.x0 - point.x, 0, point.x - rect.x1)
            dy = max(rect.y0 - point.y, 0, point.y - rect.y1)
            return dx * dx + dy * dy
        return min(range(len(chars)), key=distance)

    def select_characters(self, start, end):
        self._selection = (start, end)
        self.viewport().update()

    def selected_text(self):
        if not self._selection or self._document is None:
            return ""
        start, end = sorted(self._selection)
        pages = []
        for number in range(start[0], end[0] + 1):
            chars = self._characters(number)
            first = start[1] if number == start[0] else 0
            last = end[1] if number == end[0] else len(chars) - 1
            text, previous = [], None
            for char, _bbox, line in chars[first:last + 1]:
                if previous is not None and line != previous:
                    text.append("\n")
                text.append(char)
                previous = line
            pages.append("".join(text))
        return "\n".join(pages)

    def copy_selection(self):
        text = self.selected_text()
        if text:
            QApplication.clipboard().setText(text)

    def set_pan_mode(self, enabled):
        self.pan_mode = bool(enabled)
        self._update_pan_cursor()

    def _update_pan_cursor(self):
        self.viewport().setCursor(
            Qt.CursorShape.ClosedHandCursor if self._pan_position is not None else
            Qt.CursorShape.OpenHandCursor if self.pan_mode or self._space_pressed else
            Qt.CursorShape.CrossCursor if self.note_placement else Qt.CursorShape.ArrowCursor)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if not event.isAutoRepeat():
                self._space_pressed = False
                if not self.pan_mode:
                    self._pan_position = None
                self._update_pan_cursor()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self._space_pressed = False
        self._pan_position = None
        self._update_pan_cursor()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True
            self._update_pan_cursor()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape and self.note_placement:
            self.set_note_placement(False)
            event.accept()
        elif event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        action = menu.addAction("コピー")
        action.setEnabled(bool(self.selected_text()))
        action.triggered.connect(self.copy_selection)
        menu.exec(event.globalPos())

    def _drag_scroll(self):
        if not self._press or self._drag_position is None or self._anchor is None:
            self._drag_timer.stop()
            return
        position = self._drag_position
        delta = -30 if position.y() < 12 else 30
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta)
        number, point = self.viewport_to_page(position)
        if number is not None:
            index = self._character_at(number, point)
            if index is not None:
                self.select_characters(self._anchor, (number, index))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            if self._document is None:
                event.accept()
                return
            if self.pan_mode or self._space_pressed:
                self._pan_position = event.position()
                self._press = None
                self._note_press = None
                self._drag_timer.stop()
                self._update_pan_cursor()
                event.accept()
                return
            if self.note_placement:
                number, point = self.viewport_to_page(event.position())
                if number is not None:
                    self.set_note_placement(False)
                    self.notePlacementRequested.emit(number, QPointF(point.x, point.y))
                event.accept()
                return
            note = self.note_at(event.position())
            if note:
                self._note_press = (note["id"], event.position())
                event.accept()
                return
            number, point = self.viewport_to_page(event.position())
            self._press = (event.position(), number, point)
            self._selection = None
            if number is not None:
                index = self._character_at(number, point)
                self._anchor = (number, index) if index is not None else None
            else:
                self._anchor = None
            self.viewport().update()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_position is not None:
            delta = event.position() - self._pan_position
            self._pan_position = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - round(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - round(delta.y()))
            event.accept()
            return
        if self.pan_mode or self._space_pressed:
            QToolTip.hideText()
            self._set_hover_link(None)
            self._update_pan_cursor()
            return
        if self.note_placement:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
            return
        if self._note_press:
            return
        note = self.note_at(event.position())
        if note and not event.buttons():
            self._set_hover_link(None)
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            QToolTip.showText(event.globalPosition().toPoint(), html.escape(note["text"][:200]), self.viewport())
            return
        QToolTip.hideText()
        number, point = self.viewport_to_page(event.position())
        if event.buttons() & Qt.MouseButton.LeftButton and self._press and self._anchor:
            self._drag_position = event.position()
            if event.position().y() < 12 or event.position().y() > self.viewport().height() - 12:
                self._drag_timer.start()
            else:
                self._drag_timer.stop()
            if number is not None:
                index = self._character_at(number, point)
                if index is not None and (event.position() - self._press[0]).manhattanLength() > 3:
                    self.select_characters(self._anchor, (number, index))
        else:
            link = self._link_entry_at(number, point) if number is not None else None
            self._set_hover_link((number, link) if link else None, event.globalPosition().toPoint())
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if link else
                                      Qt.CursorShape.IBeamCursor if number is not None else Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, event):
        self._set_hover_link(None)
        super().leaveEvent(event)

    def _set_hover_link(self, hit, global_position=None):
        old = self._hover_link[1] if self._hover_link else None
        new = hit[1] if hit else None
        if old is new:
            return
        self._hover_link = hit
        window = self.window()
        status = window.statusBar() if isinstance(window, QMainWindow) else None
        if new is None:
            QToolTip.hideText()
            if status is not None and old is not None:
                status.clearMessage()
        else:
            if global_position is not None:
                QToolTip.showText(global_position, html.escape(new["label"]), self.viewport())
            if status is not None and status.isVisible():
                status.showMessage(f"リンク: {new['label']}")
        self.viewport().update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pan_position is not None:
            self._pan_position = None
            self._update_pan_cursor()
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._note_press:
            identity, start = self._note_press
            self._note_press = None
            if (event.position() - start).manhattanLength() < 4:
                self.noteActivated.emit(identity)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and self._press:
            start, number, point = self._press
            if number is not None and (event.position() - start).manhattanLength() < 4:
                self.activate_link_at(number, point)
            self._press = None
            self._drag_timer.stop()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _page_links(self, number):
        """ページ内のリンク(必要になったページだけ読む)。rectsは回転前のページ座標。"""
        if number in self._links_cache:
            self._links_cache.move_to_end(number)
            return self._links_cache[number]
        page = self._document[number]
        links = []
        # 1) PDFに埋め込まれたリンク(get_linksの矩形は回転後のページ座標)
        for link in page.get_links():
            if link.get("kind") == pymupdf.LINK_GOTO and link.get("page", -1) >= 0:
                label = f"{link['page'] + 1} ページへ移動"
            else:
                label = link.get("uri") or link.get("file")
                if not label:
                    continue
                label = label.removeprefix("mailto:")
            links.append({"rects": [pymupdf.Rect(link["from"]) * page.derotation_matrix],
                          "link": link, "url": None, "label": label})
        # 2) 本文に文字で書かれているだけのURL・メールアドレス
        chars = self._characters(number)
        text, char_index, previous = [], [], None
        for index, (char, _bbox, line) in enumerate(chars):
            if previous is not None and line != previous:
                text.append("\n")
                char_index.append(-1)
            text.append(char)
            char_index.extend([index] * len(char))
            previous = line
        text = "".join(text)
        for match in _TEXT_LINK_RE.finditer(text):
            raw = match.group(0).rstrip(".,;:!?)]}'\"")
            indexes = [char_index[i] for i in range(match.start(), match.start() + len(raw))
                       if char_index[i] >= 0]
            if not raw or not indexes:
                continue
            lines = {}
            for index in indexes:
                _char, bbox, line = chars[index]
                rect = pymupdf.Rect(bbox)
                lines[line] = lines[line] | rect if line in lines else rect
            rects = [rect for rect in lines.values() if not rect.is_empty]
            # 埋め込みリンクと重なる場合はそちらを優先する
            if not rects or any(rect.intersects(other) for rect in rects
                                for entry in links if entry["link"] for other in entry["rects"]):
                continue
            if match.group("mail"):
                url = "mailto:" + raw
            else:
                url = raw if raw.lower().startswith("http") else "http://" + raw
            links.append({"rects": rects, "link": None, "url": url, "label": raw})
        self._links_cache[number] = links
        while len(self._links_cache) > 16:
            self._links_cache.popitem(last=False)
        return links

    def _link_entry_at(self, number, point):
        if self._document is None:
            return None
        for entry in self._page_links(number):
            for rect in entry["rects"]:
                if pymupdf.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1).contains(point):
                    return entry
        return None

    def _raw_file_path(self, number, link):
        xref = link.get("xref")
        if not xref:
            return None
        obj = self._document.xref_object(xref)
        match = re.search(r"/(?:URI|UF|F)\s*<([0-9A-Fa-f]+)>", obj)
        if match:
            raw = bytes.fromhex(match.group(1))
        else:
            match = re.search(r"/(?:URI|UF|F)\s*\(((?:\\.|[^\\)])*)\)", obj)
            if not match:
                return None
            literal = match.group(1).encode("latin-1")
            def unescape(m):
                escaped = m.group(1)
                if escaped[:1] in (b"\r", b"\n"):
                    return b""
                if escaped[:1] in b"01234567":
                    return bytes((int(escaped, 8),))
                return {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}.get(escaped, escaped)
            raw = re.sub(rb"\\([0-7]{1,3}|\r?\n|.)", unescape, literal)
        encodings = ("utf-16",) if raw.startswith((b"\xfe\xff", b"\xff\xfe")) else ("utf-8", "cp932")
        for encoding in encodings:
            try:
                decoded = raw.decode(encoding)
                return QUrl(decoded).toLocalFile() if decoded.startswith("file:") else decoded
            except UnicodeError:
                pass
        return None

    def activate_link_at(self, number, point):
        entry = self._link_entry_at(number, point)
        if entry is None:
            return False
        if entry["link"] is None:
            url = QUrl(entry["url"])
            if url.scheme().lower() not in _OPENABLE_SCHEMES:
                return False
            if not QDesktopServices.openUrl(url):
                QMessageBox.warning(self, "リンクを開けません", url.toString())
            return True
        link = entry["link"]
        if link.get("kind") == pymupdf.LINK_GOTO and link.get("page", -1) >= 0:
            target = link.get("to", pymupdf.Point())
            if link["page"] >= self.page_count:
                return False
            # get_links returns the destination in its rotated page coordinates.
            target = target * self._document[link["page"]].derotation_matrix
            self._navigator.jump(link["page"], QPointF(target.x, target.y))
            return True
        target = link.get("uri") or link.get("file")
        if not target:
            return False
        url = QUrl(target)
        scheme = "file" if link.get("file") and not link.get("uri") else url.scheme().lower()
        if scheme not in _OPENABLE_SCHEMES:
            return False
        if scheme == "file":
            path = (self._raw_file_path(number, link) or url.toLocalFile() or target.removeprefix("file:")).replace("\u00a5", "\\")
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(self.link_base_path), path)
            path = os.path.abspath(path)
            if not os.path.exists(path):
                QMessageBox.warning(self, "リンク先が見つかりません", path)
                return True
            url = QUrl.fromLocalFile(path)
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "リンクを開けません", url.toString())
        return True

    def start_search(self, query):
        self._search_anchor_page = None
        self._search_job.stop()
        self._search_timer.stop()
        self._search_query = query.strip()
        self._search_results = []
        self._search_rects = {}
        self.search_done = not bool(self._search_query)
        self.active_search_index = -1
        self.viewport().update()
        if self._search_query:
            self._search_timer.start(300)
        else:
            self.searchProgress.emit("", 0, True)

    def _launch_search(self):
        if self._document is not None and self._search_query:
            try:
                self._search_job.start("search", self.pdf_path, self._search_query)
            except Exception as error:
                self.search_done = True
                self.searchFailed.emit(self._search_query, str(error))

    def _search_message(self, kind, value):
        if kind == "hits":
            number, rects = value
            self._search_rects[number] = rects
            self._search_results.extend((number, rect) for rect in rects)
            if self._search_anchor_page is not None:
                self.align_search_to_page(self._search_anchor_page)
            elif self.active_search_index == -1:
                self._show_match(0)
        elif kind in ("done", "error"):
            self.search_done = True
            if kind == "error":
                self.searchFailed.emit(self._search_query, value)
        self.searchProgress.emit(self._search_query, len(self._search_results), self.search_done)
        self.viewport().update()

    def _show_match(self, index):
        if not self._search_results:
            return
        self._search_anchor_page = None
        self.active_search_index = index % len(self._search_results)
        number, bbox = self._search_results[self.active_search_index]
        self._navigator.jump(number, QPointF(bbox[0], bbox[1]))
        self.searchMatchChanged.emit(number)
        self.viewport().update()

    def align_search_to_page(self, page):
        """Anchor match navigation to a manual jump without moving the page."""
        self._search_anchor_page = page
        first = bisect.bisect_left(self._search_results, (page,))
        if first < len(self._search_results) and self._search_results[first][0] == page:
            self.active_search_index = first
        else:
            self.active_search_index = first - 1
        self.searchMatchChanged.emit(page)
        self.viewport().update()

    def next_search_match(self):
        self._show_match(self.active_search_index + 1)

    def previous_search_match(self):
        self._show_match(self.active_search_index - 1 if self.active_search_index >= 0 else -1)

    @property
    def search_result_count(self):
        return len(self._search_results)

    def close_document(self):
        self._highlight_timer.stop()
        self._drag_timer.stop()
        self._search_timer.stop()
        self._search_job.stop()
        self._renderer.stop()
        if self._document is not None:
            self._document.close()
            self._document = None
        self._cache.clear()
        self._chars_cache.clear()
        self._links_cache.clear()
        self._hover_link = None
        self.cache_bytes = 0

    def suspend_for_note_save(self):
        self._note_saved_scroll = self.verticalScrollBar().value()
        self._note_resume_query = self._search_query if not self.search_done else ""
        self.close_document()

    def reopen_after_note_save(self, path):
        """Annotation-only commit preserves page layout and completed searches."""
        document = pymupdf.open(path)
        if document.needs_pass or document.page_count != len(self._sizes):
            document.close()
            raise ValueError("保存後のPDFのページ構成が一致しません")
        if self._document is not None:
            self.suspend_for_note_save()
        self._document = document
        self.pdf_path = path
        self.link_base_path = path
        self._renderer.path = path
        self._failed_tiles.clear()
        self._render_error = None
        self.verticalScrollBar().setValue(getattr(self, "_note_saved_scroll", self.verticalScrollBar().value()))
        if getattr(self, "_note_resume_query", ""):
            self.start_search(self._note_resume_query)
            self._note_resume_query = ""
        self.viewport().update()

    def reload_document(self):
        """Reindex may follow an external edit; replace document state atomically."""
        document = pymupdf.open(self.pdf_path)
        try:
            if document.needs_pass:
                raise ValueError("パスワード付きPDFは開けません")
            sizes = [(page.rect.width, page.rect.height) for page in document]
        except Exception:
            document.close()
            raise
        page = self._navigator.currentPage()
        query = self._search_query
        self.close_document()
        self._document = document
        self.page_count = document.page_count
        self._sizes = sizes
        self._failed_tiles.clear()
        self._render_error = None
        self._selection = None
        self._layout_pages()
        self._navigator.jump(min(page, max(0, self.page_count - 1)))
        self.start_search(query)

    def closeEvent(self, event):
        self.close_document()
        super().closeEvent(event)
