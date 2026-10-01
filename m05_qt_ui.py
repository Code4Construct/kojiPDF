"""PySide6 UI for kojiPDF's settings, progress, and results."""
import os
import time
from html import escape

from PySide6.QtCore import Qt, QObject, QEventLoop, QTimer, Signal, QSize, QRectF
from PySide6.QtGui import QFont, QPixmap, QIcon, QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QPlainTextEdit, QProgressBar,
)

from qt_dialog_bridge import QtDialogBridge
from viewer_launcher import ViewerLauncher

from m05_ui_model import (
    BOOKMARK_VIEW_MODE_LABELS, BUILT_IN_PRESETS, DEFAULT_UI_SETTINGS,
    PAGE_NUMBER_COLOR_LABELS,
    PAGE_NUMBER_FONT_LABELS, PAGE_NUMBER_FORMAT_LABELS,
    PAGE_NUMBER_POSITION_LABELS, PRESET_CODES,
    SAVE_MODE_OPTIONS, TRANSLATIONS, settings_file_path,
    load_custom_presets, save_custom_presets, margin_setting_mm, page_number_options,
)


class ProgressEmitter(QObject):
    message = Signal(str)


def _ui_font(family, point_size, bold=False):
    font = QFont(family, point_size)
    font.setBold(bold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def _flag_pixmap(country):
    pixmap = QPixmap(80, 80)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addEllipse(4, 4, 72, 72)
    painter.setClipPath(clip)
    painter.fillPath(clip, QColor("white" if country == "ja" else "#012169"))
    if country == "ja":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#bc002d"))
        painter.drawEllipse(25, 25, 30, 30)
    else:
        painter.setPen(QPen(QColor("white"), 16))
        painter.drawLine(5, 5, 75, 75)
        painter.drawLine(75, 5, 5, 75)
        painter.setPen(QPen(QColor("#c8102e"), 7))
        painter.drawLine(5, 5, 75, 75)
        painter.drawLine(75, 5, 5, 75)
        painter.setPen(QPen(QColor("white"), 24))
        painter.drawLine(40, 0, 40, 80)
        painter.drawLine(0, 40, 80, 40)
        painter.setPen(QPen(QColor("#c8102e"), 11))
        painter.drawLine(40, 0, 40, 80)
        painter.drawLine(0, 40, 80, 40)
    painter.setClipping(False)
    painter.setPen(QPen(QColor("#67839a"), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(4, 4, 72, 72)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return pixmap


class ToggleCheckBox(QCheckBox):
    def sizeHint(self):
        metrics = self.fontMetrics()
        return QSize(metrics.horizontalAdvance(self.text()) + 30,
                     max(22, metrics.height() + 4))

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        top = (self.height() - 12) / 2
        painter.setPen(QPen(QColor("#a5abb0" if self.isEnabled() else "#c5cbd0"), 1))
        painter.setBrush(QColor("#0b749c" if self.isChecked() else "#e7e9ea"))
        painter.drawRoundedRect(QRectF(0, top, 22, 12), 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QRectF(12 if self.isChecked() else 2, top + 2, 8, 8))
        painter.setPen(QColor("#102033" if self.isEnabled() else "#a8adb2"))
        painter.drawText(QRectF(28, 0, max(0, self.width() - 28), self.height()),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        painter.end()


class FileSelectorApp(QDialog):
    """Collects the same settings as the Tk form using layout-managed widgets."""

    def __init__(self):
        super().__init__()
        self.setFont(_ui_font("Yu Gothic UI", 10))
        self.language = "ja"
        self.selected_folder = None
        self.selected_file = None
        self.retry_requested = False
        self._fields = {}
        self._labels = {}
        self.custom_presets = self._load_custom_presets()
        self.dialog_bridge = QtDialogBridge(self)
        self.viewer_launcher = ViewerLauncher(self)
        self.viewer_launcher.viewer_closed.connect(self._on_viewer_closed)
        self._waiting_for_viewer_close = False
        self.progress_emitter = ProgressEmitter()
        self.progress_emitter.message.connect(self.append_progress)
        self._action_loop = None
        self._progress_started = False
        self._user_closed = False
        self._applying_settings = False
        self.finished.connect(self._on_finished)
        self._build()
        self.apply_ui_settings(DEFAULT_UI_SETTINGS)
        self._apply_language()

    def _text(self, key):
        return TRANSLATIONS[self.language][key]

    def _build(self):
        self.setWindowTitle(self._text("window_title"))
        window_icon_path = os.path.join(os.path.dirname(__file__), "assets", "icons", "smallicon_v2.ico")
        if os.path.isfile(window_icon_path):
            self.setWindowIcon(QIcon(window_icon_path))
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        width = max(320, min(900, available.width() - 24)) if available else 900
        height = max(240, min(700, available.height() - 32)) if available else 700
        self.resize(width, height)
        compact = bool(available and available.width() < 650)
        self.setStyleSheet("""
            QDialog { background: #e2e8f0; color: #102033; }
            QGroupBox { background: #fbfdff; border: 0; margin-top: 0; color: #073f66; }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: white; }
            QScrollArea { border: 0; background: #e2e8f0; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 6, 18, 18)
        root.setSpacing(6)

        header = QWidget()
        header.setStyleSheet("background: white")
        header_layout = QGridLayout(header)
        header_layout.setContentsMargins(8, 2, 8, 2)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(1, 3)
        header_layout.setColumnStretch(2, 1)
        title = QLabel(self._text("title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = _ui_font("Segoe UI Variable Display", 13 if compact else 22, bold=True)
        title.setFont(title_font)
        title.setStyleSheet("color: #102033")
        self.viewer_button = QPushButton()
        self.viewer_button.setFont(_ui_font("Yu Gothic UI", 9))
        self.viewer_button.setFixedHeight(28)
        self.viewer_button.clicked.connect(self.open_viewer)
        header_layout.addWidget(self.viewer_button, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(title, 0, 1)
        flags = QHBoxLayout()
        flags.setSpacing(4)
        self.flag_buttons = {}
        for language in ("ja", "en"):
            button = QPushButton()
            button.setIcon(QIcon(_flag_pixmap(language)))
            button.setIconSize(QSize(34, 34))
            button.setFixedSize(40, 40)
            button.setToolTip("Japanese" if language == "ja" else "English")
            button.clicked.connect(lambda _checked=False, code=language: self._set_language(code))
            flags.addWidget(button)
            self.flag_buttons[language] = button
        header_layout.addLayout(flags, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        root.addWidget(header)

        intro = QWidget()
        if not compact:
            intro.setMinimumHeight(100)
        intro.setStyleSheet("background: white")
        intro_layout = QGridLayout(intro)
        intro_layout.setContentsMargins(8, 5, 8, 5)
        intro_layout.setColumnStretch(1, 1)
        logo = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icons", "smallicon_v2.png")
        if os.path.exists(icon_path):
            logo.setPixmap(QPixmap(icon_path).scaled(62, 62, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
        logo.setFixedSize(64, 64)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(logo, 0, 0)
        self.subtitle = QLabel()
        self.subtitle.hide()
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.notice.setFont(_ui_font("Yu Gothic UI", 9, bold=True))
        self.notice.setStyleSheet("color: #073f66")
        intro_layout.addWidget(self.notice, 0, 1)
        preset = QWidget()
        preset_layout = QGridLayout(preset)
        preset_layout.setContentsMargins(2, 0, 0, 0)
        preset_layout.setSpacing(3)
        self.preset_heading = QLabel()
        self.preset_heading.setFont(_ui_font("Yu Gothic UI", 9, bold=True))
        preset_layout.addWidget(self.preset_heading, 0, 0)
        self.preset_reset = QPushButton()
        self.preset_reset.setFont(_ui_font("Segoe UI Symbol", 12))
        self.preset_reset.setFixedWidth(30)
        self.preset_reset.clicked.connect(self.reset_saved_presets)
        preset_layout.addWidget(self.preset_reset, 0, 1)
        self.preset_combo = QComboBox()
        self.preset_combo.currentIndexChanged.connect(self.load_selected_preset)
        preset_layout.addWidget(self.preset_combo, 1, 0, 1, 2)
        self.preset_save = QPushButton()
        self.preset_save.clicked.connect(self.save_selected_preset)
        preset_layout.addWidget(self.preset_save, 2, 0, 1, 2)
        intro_layout.addWidget(preset, 0, 2)
        self.intro_panel = intro
        self.preset_row_widgets = (self.preset_combo, self.preset_save, self.preset_reset, self.preset_heading)
        root.addWidget(intro)

        paths = QWidget()
        if not compact:
            paths.setMinimumHeight(86)
        paths.setStyleSheet("background: white")
        path_grid = QGridLayout(paths)
        path_grid.setContentsMargins(10, 6, 10, 6)
        path_grid.setColumnStretch(1, 1)
        for row, (key, callback) in enumerate((("select_folder", self.select_folder), ("output", self.select_save_file))):
            button = QPushButton()
            button.clicked.connect(callback)
            value = QLineEdit()
            value.setReadOnly(True)
            value.setStyleSheet("border: 1px solid #9b9b9b; border-radius: 0; padding: 3px; background: white")
            path_grid.addWidget(button, row, 0)
            path_grid.addWidget(value, row, 1)
            self._labels[key] = button
            self._fields[key] = value
        self.run_button = QPushButton()
        self.run_button.clicked.connect(self._accept_if_ready)
        self.run_button.setDefault(True)
        self.run_button.setFixedSize(66, 66)
        run_font = _ui_font("Meiryo", 10, bold=True)
        run_font.setPixelSize(14)
        self.run_button.setFont(run_font)
        self.run_button.setStyleSheet("QPushButton { border-radius: 33px; background: #8f1d2c; color: white; }"
                                      "QPushButton:hover { background: #a92536; }")
        path_grid.addWidget(self.run_button, 0, 2, 2, 1)
        root.addWidget(paths)
        self.paths_group = paths

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        body.setObjectName("settingsBody")
        body.setStyleSheet("QWidget#settingsBody { background: #e2e8f0; }")
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setHorizontalSpacing(4)
        body_layout.setVerticalSpacing(6)
        self.settings_body_layout = body_layout
        body_layout.setColumnStretch(0, 2)
        body_layout.setColumnStretch(1, 1)
        self.sections = {}
        self.section_forms = {}
        self.section_titles = {}
        self.section_header_rows = {}
        positions = (("general_options", 0, 0, 1), ("bookmark_options", 1, 0, 1),
                     ("page_number_options", 2, 0, 1), ("scale_options", 3, 0, 1),
                     ("asp_options", 4, 0, 1)) if compact else (
                     ("general_options", 0, 0, 1), ("bookmark_options", 0, 1, 1),
                     ("page_number_options", 1, 0, 2), ("scale_options", 2, 0, 1),
                     ("asp_options", 2, 1, 1))
        for name, row, column, span in positions:
            section = QGroupBox()
            outer = QVBoxLayout(section)
            outer.setContentsMargins(8, 7, 8, 7)
            outer.setSpacing(4)
            heading = QHBoxLayout()
            heading.setSpacing(8)
            title_label = QLabel()
            heading_font = _ui_font("Yu Gothic UI", 11, bold=True)
            title_label.setFont(heading_font)
            title_label.setStyleSheet("color: #073f66")
            heading.addWidget(title_label)
            heading.addStretch()
            outer.addLayout(heading)
            content = QWidget()
            grid = QGridLayout(content)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(5)
            grid.setVerticalSpacing(3)
            outer.addWidget(content, 1)
            body_layout.addWidget(section, row, column, 1, span)
            self.sections[name] = section
            self.section_forms[name] = grid
            self.section_titles[name] = title_label
            self.section_header_rows[name] = heading
            if not compact and name in ("general_options", "bookmark_options"):
                section.setMinimumHeight(160)
            if not compact and name == "page_number_options":
                section.setMinimumHeight(114)
            if not compact and name in ("scale_options", "asp_options"):
                section.setMinimumHeight(60)
        body_layout.setRowStretch(5 if compact else 3, 1)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)
        self.settings_scroll = scroll

        for key in ("convert_office", "convert_mail", "ppt_slide_bookmarks",
                    "confirm_temp_folder_delete", "resize_pdf", "pdf_detail_check",
                    "keep_pdf_extension", "add_bookmark_page_number_and_count", "expand_all",
                    "add_pdf_page_numbers", "asper_format"):
            self._check(key)
        for key, labels in (("resize_size", {"A3": "A3", "A4": "A4", "A5": "A5", "B4": "B4", "B5": "B5"}),
                            ("save_mode", SAVE_MODE_OPTIONS),
                            ("bookmark_view_mode", BOOKMARK_VIEW_MODE_LABELS["ja"]),
                            ("page_number_position", PAGE_NUMBER_POSITION_LABELS["ja"]),
                            ("page_number_format", PAGE_NUMBER_FORMAT_LABELS["ja"]),
                            ("page_font", PAGE_NUMBER_FONT_LABELS["ja"]),
                            ("page_color", PAGE_NUMBER_COLOR_LABELS["ja"])):
            self._combo(key, labels)
        for key, low, high, decimals, step in (("collapse_level", 1, 10, 0, 1),
                                               ("base_view_width", 100, 1000, 0, 1),
                                               ("base_view_height", 100, 1000, 0, 1),
                                               ("page_start_page", 1, 9999, 0, 1),
                                               ("page_start_number", 1, 9999, 0, 1),
                                               ("page_font_size", 1, 300, 0, 1),
                                               ("page_margin_x", 0, 500, 2, 0.5),
                                               ("page_margin_y", 0, 500, 2, 0.5),
                                               ("page_opacity", 0.05, 1.0, 2, 0.05)):
            self._spin(key, low, high, decimals, step)
        self._labels["expand_all"] = (self._fields["expand_all"], "expand_all")

        general = self.section_forms["general_options"]
        general.setColumnStretch(0, 3)
        general.setColumnStretch(1, 2)
        for row, key in enumerate(("convert_office", "convert_mail", "ppt_slide_bookmarks",
                                   "confirm_temp_folder_delete")):
            if row == 0:
                general.addWidget(self._fields[key], row, 0)
            else:
                self._fields[key].setFont(_ui_font("Yu Gothic UI", 9))
                indented = QHBoxLayout()
                indented.setContentsMargins(66 if not compact else 24, 0, 0, 0)
                indented.addWidget(self._fields[key])
                general.addLayout(indented, row, 0)
        resize_row = QHBoxLayout()
        resize_row.setSpacing(10)
        resize_row.addWidget(self._fields["resize_pdf"])
        resize_row.addWidget(self._fields["resize_size"])
        self._fields["resize_size"].setMaximumWidth(78)
        resize_row.addStretch()
        general.addLayout(resize_row, 4, 0)
        self._labels["resize_size"].hide()
        self._fields["save_mode"].setMaximumWidth(105)
        save_row = self._field_row("save_mode")
        save_row.setContentsMargins(58 if not compact else 0, 0, 0, 0)
        general.addLayout(save_row, 6 if compact else 0, 0 if compact else 1)
        detail_check_row = QHBoxLayout()
        detail_check_row.setContentsMargins(29 if not compact else 0, 0, 0, 0)
        detail_check_row.addWidget(self._fields["pdf_detail_check"])
        general.addLayout(detail_check_row, 7 if compact else 2, 0 if compact else 1)
        self.detail_hint = QLabel()
        self.detail_hint.setWordWrap(True)
        self.detail_hint.setFont(_ui_font("Yu Gothic UI", 8))
        self.detail_hint.setStyleSheet("color: #52657a")
        if not compact:
            self.detail_hint.setMaximumWidth(165)
        detail_indent = QHBoxLayout()
        detail_indent.setContentsMargins(56 if not compact else 26, 0, 0, 0)
        detail_indent.addWidget(self.detail_hint)
        general.addLayout(detail_indent, 8 if compact else 3, 0 if compact else 1,
                          1 if compact else 2, 1)

        bookmark = self.section_forms["bookmark_options"]
        self._fields["add_bookmark_page_number_and_count"].setFont(_ui_font("Yu Gothic UI", 9))
        bookmark.addWidget(self._fields["add_bookmark_page_number_and_count"], 0, 0, 1, 2)
        self.bookmark_hint = QLabel()
        self.bookmark_hint.setWordWrap(True)
        self.bookmark_hint.setFont(_ui_font("Yu Gothic UI", 8))
        self.bookmark_hint.setStyleSheet("color: #52657a")
        bookmark_hint_row = QHBoxLayout()
        bookmark_hint_row.setContentsMargins(26, 0, 0, 0)
        bookmark_hint_row.addWidget(self.bookmark_hint)
        bookmark.addLayout(bookmark_hint_row, 1, 0, 1, 2)
        bookmark.addWidget(self._fields["expand_all"], 2, 0, 1, 2)
        collapse_row = QHBoxLayout()
        collapse_row.setContentsMargins(28, 0, 0, 0)
        collapse_row.addLayout(self._field_row("collapse_level"))
        bookmark.addLayout(collapse_row, 3, 0, 1, 2)
        bookmark.addWidget(self._fields["keep_pdf_extension"], 4, 0, 1, 2)

        page = self.section_forms["page_number_options"]
        if not compact:
            page.setContentsMargins(8, 0, 0, 0)
            page.setHorizontalSpacing(3)
            for key in ("page_number_position", "page_number_format", "page_start_page",
                        "page_start_number", "page_opacity", "page_font_size", "page_margin_x",
                        "page_margin_y", "page_font", "page_color"):
                self._labels[key].setFixedWidth(70)
                self._labels[key].setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._fields[key].setMaximumWidth(85)
        self.page_number_heading = self.section_titles["page_number_options"]
        self.page_number_heading.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.section_header_rows["page_number_options"].insertWidget(
            1, self._fields["add_pdf_page_numbers"])
        for key in ("page_number_position", "page_number_format", "page_font", "page_color"):
            self._fields[key].setMaximumWidth(95)
        for index, key in enumerate(("page_number_position", "page_number_format", "page_start_page",
                                     "page_start_number", "page_opacity")):
            page.addLayout(self._field_row(key, vertical=compact),
                           index // 2 if compact else 0, index % 2 if compact else index)
        for index, key in enumerate(("page_font_size", "page_margin_x", "page_margin_y",
                                     "page_font", "page_color")):
            place = index + 5
            if key == "page_font_size":
                font_row = self._field_row(key, vertical=compact)
                self.page_font_hint = QLabel()
                self.page_font_hint.setFont(_ui_font("Yu Gothic UI", 8))
                self.page_font_hint.setStyleSheet("color: #52657a")
                font_cell = QVBoxLayout()
                font_cell.setSpacing(0)
                font_cell.addLayout(font_row)
                font_cell.addWidget(self.page_font_hint, alignment=Qt.AlignmentFlag.AlignCenter)
                field_layout = font_cell
            else:
                field_layout = self._field_row(key, vertical=compact)
            page.addLayout(field_layout, place // 2 if compact else 1,
                           place % 2 if compact else index)
            page.setColumnStretch(index % 2 if compact else index, 1)
        self._fields["page_font_size"].valueChanged.connect(self._update_page_font_hint)
        self._update_page_font_hint()

        scale = self.section_forms["scale_options"]
        self._fields["bookmark_view_mode"].setMaximumWidth(145)
        view_row = QHBoxLayout()
        view_row.setSpacing(5)
        if not compact:
            view_row.setContentsMargins(25, 0, 0, 0)
        view_row.addWidget(self._labels["bookmark_view_mode"])
        view_row.addWidget(self._fields["bookmark_view_mode"])
        view_row.addStretch()
        if compact:
            scale.addLayout(view_row, 0, 0)
        else:
            self.section_header_rows["scale_options"].insertLayout(1, view_row)
        for index, key in enumerate(("base_view_width", "base_view_height"), start=1):
            scale.addLayout(self._field_row(key), index if compact else 0, 0 if compact else index)
        scale.setColumnStretch(0, 1)
        asp = self.section_forms["asp_options"]
        asp.addWidget(self._fields["asper_format"], 0, 0)

        progress_group = QGroupBox()
        progress_layout = QVBoxLayout(progress_group)
        self.progress_status = QLabel()
        progress_layout.addWidget(self.progress_status)
        self.progress_elapsed = QLabel()
        progress_layout.addWidget(self.progress_elapsed)
        self.progress_step_labels = []
        steps_row = QHBoxLayout()
        for _ in range(6):
            step_label = QLabel()
            step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            steps_row.addWidget(step_label, 1)
            self.progress_step_labels.append(step_label)
        progress_layout.addLayout(steps_row)
        self.progress_step_index = -1
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._update_elapsed)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        progress_layout.addWidget(self.progress_bar)
        self.progress_text = QPlainTextEdit()
        self.progress_text.setReadOnly(True)
        progress_layout.addWidget(self.progress_text, 1)
        self.retry_button = QPushButton()
        self.retry_button.clicked.connect(self.retry)
        self.retry_button.hide()
        progress_layout.addWidget(self.retry_button)
        progress_group.hide()
        root.addWidget(progress_group, 1)
        self.progress_group = progress_group

        footer = QWidget()
        if not compact:
            footer.setMinimumHeight(50)
        footer.setStyleSheet("background: white")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(6, 2, 6, 2)
        self.footer_notice = QLabel()
        self.footer_notice.setWordWrap(True)
        self.footer_notice.setFont(_ui_font("Yu Gothic UI", 8))
        self.footer_notice.setStyleSheet("color: #52657a")
        footer_layout.addWidget(self.footer_notice, 1)
        self.dpi_label = QLabel()
        self.dpi_label.setFont(_ui_font("Yu Gothic UI", 8))
        self.dpi_label.setStyleSheet("color: #073f66")
        footer_layout.addWidget(self.dpi_label)
        root.addWidget(footer)
        self.footer_panel = footer

        self.message_banner = QLabel()
        self.message_banner.setWordWrap(True)
        self.message_banner.setStyleSheet("background: #e8f3ff; color: #173b62; padding: 8px; border: 1px solid #a9c9e8")
        self.message_banner.hide()
        root.addWidget(self.message_banner)
        self.message_timer = QTimer(self)
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self.message_banner.hide)
        self.cancel_button = QPushButton()
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.hide()
        root.addWidget(self.cancel_button)

        self._fields["convert_office"].toggled.connect(self._refresh_states)
        self._fields["convert_office"].toggled.connect(self._office_changed)
        self._fields["add_pdf_page_numbers"].toggled.connect(self._refresh_states)
        self._fields["expand_all"].toggled.connect(self._refresh_states)
        self._fields["bookmark_view_mode"].currentIndexChanged.connect(self._refresh_states)
        self._fields["page_number_position"].currentIndexChanged.connect(self._refresh_states)

    def _check(self, key):
        widget = ToggleCheckBox()
        self._fields[key] = widget
        self._labels[key] = (widget, key)

    def _combo(self, key, labels):
        widget = QComboBox()
        for code, label in labels.items():
            widget.addItem(str(label), code)
        caption = QLabel()
        self._fields[key] = widget
        self._labels[key] = caption

    def _spin(self, key, low, high, decimals=0, step=1):
        widget = QSpinBox() if decimals == 0 else QDoubleSpinBox()
        widget.setRange(low, high)
        if decimals:
            widget.setDecimals(decimals)
        widget.setSingleStep(step)
        widget.setMaximumWidth(94)
        caption = QLabel()
        self._fields[key] = widget
        self._labels[key] = caption

    def _field_row(self, key, vertical=False):
        layout = QVBoxLayout() if vertical else QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(self._labels[key])
        layout.addWidget(self._fields[key], 1)
        return layout

    def _value(self, key):
        widget = self._fields[key]
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QComboBox):
            return widget.currentData()
        return widget.value()

    def _set_value(self, key, value):
        widget = self._fields[key]
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index < 0:
                index = widget.findData(DEFAULT_UI_SETTINGS.get(key))
            widget.setCurrentIndex(max(0, index))
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                number = widget.minimum()
            widget.setValue(number)

    def _set_language(self, language):
        self.language = language
        self._apply_language()

    def _apply_language(self):
        self.setWindowTitle(self._text("window_title"))
        self.viewer_button.setText(self._text("open_viewer"))
        self.subtitle.setText(self._text("subtitle"))
        notice_text = self._text("notice")
        marker = "\nNote:" if self.language == "en" else "\n\u6ce8\u610f\uff1a"
        summary, separator, footer_text = notice_text.partition(marker)
        if self.language == "en":
            lines = (summary if separator else notice_text).splitlines()
            self.notice.setText("".join(
                f'<p style="margin:0 0 2px 12px; text-indent:-12px">{escape(line)}</p>'
                for line in lines
            ))
        else:
            self.notice.setText(summary if separator else notice_text)
        self.footer_notice.setText(marker.lstrip("\n") + footer_text if separator else "")
        self.footer_panel.setMinimumHeight(64 if self.language == "en" else 50)
        gap = 6 if self.language == "en" else 9
        self.layout().setSpacing(gap)
        self.settings_body_layout.setVerticalSpacing(gap)
        self.sections["page_number_options"].setMinimumHeight(118 if self.language == "en" else 114)
        self.layout().setContentsMargins(18, 6, 18, 18)
        if self.language == "en":
            self._labels["page_number_position"].setFixedWidth(62)
            self._fields["page_number_position"].setMaximumWidth(105)
            for key in ("page_margin_x", "page_margin_y"):
                self._labels[key].setFixedWidth(75)
                self._fields[key].setMaximumWidth(76)
        else:
            for key in ("page_number_position", "page_margin_x", "page_margin_y"):
                self._labels[key].setFixedWidth(70)
                self._fields[key].setMaximumWidth(95 if key == "page_number_position" else 85)
        self.preset_heading.setText(self._text("preset"))
        self.detail_hint.setText(self._text("pdf_detail_check_hint"))
        self.bookmark_hint.setText(self._text("add_bookmark_page_number_and_count_hint"))
        for code, button in self.flag_buttons.items():
            border = "#8ed5f0" if code == self.language else "transparent"
            button.setStyleSheet(f"border: 2px solid {border}; border-radius: 20px; background: white")
        self.dpi_label.setText(f"{round(QApplication.primaryScreen().logicalDotsPerInch())} DPI / {round(QApplication.primaryScreen().devicePixelRatio() * 100)}%")
        for key, label in self.section_titles.items():
            label.setText(self._text(key))
        for key in ("select_folder", "output"):
            self._labels[key].setText(self._text(key))
            if not self._fields[key].text():
                self._fields[key].setPlaceholderText(self._text("not_selected"))
        for key, label in self._labels.items():
            if key in ("select_folder", "output"):
                continue
            if isinstance(label, tuple):
                widget, override = label
                if key == "add_pdf_page_numbers":
                    widget.setText("")
                    widget.setToolTip(self._text(key))
                else:
                    widget.setText(self._text(override) if override in TRANSLATIONS[self.language] else override)
            else:
                translated = {"resize_size": "resize_pdf",
                              "page_margin_x": "page_margin_right", "page_margin_y": "page_margin_bottom"}
                lookup = translated.get(key, key)
                if key == "resize_size":
                    label.setText("\u30b5\u30a4\u30ba" if self.language == "ja" else "Size")
                else:
                    label.setText(self._text(lookup) if lookup in TRANSLATIONS[self.language]
                                  else ("\u3057\u304a\u308a\u5c55\u958b\u968e\u5c64" if self.language == "ja" else "Bookmark depth"))
        self._relabel_combo("save_mode", {"ja": {"speed": "速度重視", "balanced": "バランス", "smaller_file": "圧縮重視"},
                                          "en": {"speed": "Speed", "balanced": "Balanced", "smaller_file": "Smaller File"}}[self.language])
        for key, labels in (("bookmark_view_mode", BOOKMARK_VIEW_MODE_LABELS),
                            ("page_number_position", PAGE_NUMBER_POSITION_LABELS),
                            ("page_number_format", PAGE_NUMBER_FORMAT_LABELS),
                            ("page_font", PAGE_NUMBER_FONT_LABELS),
                            ("page_color", PAGE_NUMBER_COLOR_LABELS)):
            self._relabel_combo(key, labels[self.language])
        self.preset_combo.blockSignals(True)
        selected = self.preset_combo.currentData() or "none"
        self.preset_combo.clear()
        names = ({"none": "設定なし", "paperless": "ペーパーレス会議設定", "mail": "メールデータ整理設定",
                  "asp": "工事書類検査設定", "custom1": "カスタム1", "custom2": "カスタム2"}
                 if self.language == "ja" else
                 {"none": "No preset", "paperless": "Paperless meeting", "mail": "Mail data cleanup",
                  "asp": "Construction ASP", "custom1": "Custom 1", "custom2": "Custom 2"})
        for code in PRESET_CODES:
            self.preset_combo.addItem(names[code], code)
        self.preset_combo.setCurrentIndex(max(0, self.preset_combo.findData(selected)))
        self.preset_combo.blockSignals(False)
        self.preset_save.setText(self._text("save_preset"))
        self.preset_reset.setText(self._text("reset_preset"))
        self.preset_reset.setToolTip(self._text("preset_reset_title"))
        self.cancel_button.setText("キャンセル" if self.language == "ja" else "Cancel")
        self.run_button.setText(self._text("create_short"))
        self.progress_group.setTitle(self._text("progress_title"))
        self.retry_button.setText(self._text("create"))
        self._set_progress_step(self.progress_step_index)
        self._refresh_states()

    def _relabel_combo(self, key, labels):
        widget = self._fields[key]
        for index in range(widget.count()):
            widget.setItemText(index, labels[widget.itemData(index)])

    def _update_page_font_hint(self, *_):
        millimetres = round(self._fields["page_font_size"].value() * 25.4 / 72, 2)
        self.page_font_hint.setText(f"{millimetres:g}mm")

    def _refresh_states(self, *_):
        office = self._value("convert_office")
        for key in ("convert_mail", "ppt_slide_bookmarks", "confirm_temp_folder_delete"):
            self._fields[key].setEnabled(office)
        numbered = self._value("add_pdf_page_numbers")
        for key in ("page_number_position", "page_number_format", "page_start_page",
                    "page_start_number", "page_font_size", "page_margin_x", "page_margin_y",
                    "page_font", "page_color", "page_opacity"):
            self._fields[key].setEnabled(numbered)
        position = self._value("page_number_position")
        self._fields["page_margin_x"].setEnabled(numbered and not position.endswith("_center"))
        self._labels["page_margin_x"].setText(self._text(
            "page_margin_disabled" if position.endswith("_center")
            else "page_margin_left" if position.endswith("_left") else "page_margin_right"
        ))
        self._labels["page_margin_y"].setText(self._text(
            "page_margin_top" if position.startswith("top_") else "page_margin_bottom"
        ))
        for key in ("page_margin_x", "page_margin_y"):
            label = self._labels[key]
            full_text = label.text()
            if self.language == "en":
                side = full_text.split(" ", 1)[0]
                label.setToolTip(full_text)
                label.setText(f"{side} (mm)")
            else:
                label.setToolTip("")
        self._fields["collapse_level"].setEnabled(not self._value("expand_all"))
        adjust = self._value("bookmark_view_mode") == "adjust"
        for key in ("base_view_width", "base_view_height"):
            self._fields[key].setEnabled(adjust)
            self._fields[key].setVisible(adjust)
            self._labels[key].setVisible(adjust)

    def _office_changed(self, enabled):
        if self._applying_settings:
            return
        if enabled:
            self._fields["convert_mail"].setChecked(True)
            self.show_temp_folder_notice(self.selected_file)
        else:
            self._fields["convert_mail"].setChecked(False)
            self._fields["confirm_temp_folder_delete"].setChecked(False)

    def apply_ui_settings(self, settings):
        self._applying_settings = True
        values = {**DEFAULT_UI_SETTINGS, **(settings or {})}
        mapping = {
            "pdf_detail_check": bool(values["preflight_detail_repair"]) or bool(values["preflight_confirm"]),
            "add_bookmark_page_number_and_count": bool(values["add_bookmark_page_number"]) or bool(values["add_page"]),
            "page_margin_x": margin_setting_mm(settings or {}, "page_margin_x", "page_margin_right", values["page_margin_x"]),
            "page_margin_y": margin_setting_mm(settings or {}, "page_margin_y", "page_margin_bottom", values["page_margin_y"]),
        }
        for key in self._fields:
            if key in ("select_folder", "output"):
                continue
            self._set_value(key, mapping.get(key, values.get(key, 0)))
        self._applying_settings = False
        self._refresh_states()

    def current_ui_settings(self):
        values = dict(DEFAULT_UI_SETTINGS)
        for key in self._fields:
            if key not in ("select_folder", "output", "pdf_detail_check", "add_bookmark_page_number_and_count"):
                values[key] = self._value(key)
        values["preflight_detail_repair"] = values["preflight_confirm"] = self._value("pdf_detail_check")
        values["add_bookmark_page_number"] = values["add_page"] = self._value("add_bookmark_page_number_and_count")
        values["eml_encoding"] = "auto"
        values["page_margin_right"] = values["page_margin_x"]
        values["page_margin_bottom"] = values["page_margin_y"]
        values["scale_mode"] = "absolute"
        values["scale_x"] = values["scale_y"] = 1.0
        return values

    def apply_launch_config(self, config):
        mode = getattr(config, "mode", "")
        if mode in BUILT_IN_PRESETS:
            self.apply_ui_settings(BUILT_IN_PRESETS[mode])
        self.apply_ui_settings(getattr(config, "settings", {}) or {})
        self.selected_folder = getattr(config, "input_folder", None)
        self.selected_file = getattr(config, "output_pdf", None)
        self._fields["select_folder"].setText(self.selected_folder or "")
        self._fields["output"].setText(self.selected_file or "")
        if self.selected_file:
            self.show_temp_pdf_notice(self.selected_file, self._value("convert_office"))

    def _load_custom_presets(self):
        return load_custom_presets()

    def load_selected_preset(self, *_):
        code = self.preset_combo.currentData()
        if code in self.custom_presets:
            self.apply_ui_settings(self.custom_presets[code])
        elif code in BUILT_IN_PRESETS:
            self.apply_ui_settings(BUILT_IN_PRESETS[code])
        elif code in PRESET_CODES and code != "none":
            self._timed_notice(
                self._text("preset_empty_title"),
                self._text("preset_empty_message").format(preset=self.preset_combo.currentText()),
            )

    def save_selected_preset(self):
        code = self.preset_combo.currentData()
        if code == "none":
            self._timed_notice(self._text("preset_none_title"), self._text("preset_none_message"))
            return
        if code in BUILT_IN_PRESETS and QMessageBox.question(self, self._text("preset_overwrite_title"), self._text("preset_overwrite_message").format(preset=self.preset_combo.currentText())) != QMessageBox.StandardButton.Yes:
            return
        self.custom_presets[code] = self.current_ui_settings()
        try:
            save_custom_presets(self.custom_presets)
        except OSError as exc:
            QMessageBox.critical(self, self._text("preset_error_title"), self._text("preset_error_message").format(error=exc))
            return
        self._timed_notice(
            self._text("preset_saved_title"),
            self._text("preset_saved_message").format(preset=self.preset_combo.currentText()),
        )

    def reset_saved_presets(self):
        if QMessageBox.question(self, self._text("preset_reset_title"), self._text("preset_reset_message")) != QMessageBox.StandardButton.Yes:
            return
        deleted = False
        try:
            os.remove(settings_file_path())
            deleted = True
        except FileNotFoundError:
            pass
        except OSError as exc:
            QMessageBox.critical(self, self._text("preset_error_title"), self._text("preset_error_message").format(error=exc))
            return
        self.custom_presets.clear()
        self.preset_combo.setCurrentIndex(self.preset_combo.findData("none"))
        self._timed_notice(
            self._text("preset_reset_done_title"),
            self._text("preset_reset_done_message" if deleted else "preset_reset_missing_message"),
        )

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self._text("folder_dialog"), os.path.expanduser("~/Documents"))
        if folder:
            self.selected_folder = folder
            self._fields["select_folder"].setText(folder)

    def select_save_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self._text("file_dialog"),
            os.path.join(os.path.expanduser("~/Documents"), self._text("default_output")),
            f"{self._text('pdf_filetype')} (*.pdf)",
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.selected_file = path
            self._fields["output"].setText(path)
            self.show_temp_pdf_notice(path, self._value("convert_office"))

    def _timed_notice(self, title, message):
        self.message_banner.setText(f"{title}: {message}")
        self.message_banner.show()
        self.message_timer.start(8000)

    def show_temp_pdf_notice(self, output_file_path, show_temp_folder=False):
        temp_pdf = output_file_path[:-4] + "temp.PDF"
        key = "temp_pdf_notice_message"
        values = {"pdf_path": temp_pdf}
        if show_temp_folder:
            key = "temp_pdf_and_folder_notice_message"
            values["folder_path"] = os.path.join(os.path.dirname(output_file_path), "temp_folder")
        self._timed_notice(self._text("temp_pdf_notice_title"), self._text(key).format(**values))

    def show_temp_folder_notice(self, output_file_path=None):
        folder_text = ""
        if output_file_path:
            temp_folder = os.path.join(os.path.dirname(output_file_path), "temp_folder")
            folder_text = "\n\n" + self._text("temp_folder_path_line").format(path=temp_folder)
        self._timed_notice(
            self._text("temp_folder_notice_title"),
            self._text("temp_folder_path_message").format(folder_path=folder_text),
        )

    def open_viewer(self):
        self.viewer_launcher.open(self.selected_file)

    def _on_viewer_closed(self):
        if self._waiting_for_viewer_close:
            self._waiting_for_viewer_close = False
            QTimer.singleShot(0, lambda: QDialog.reject(self))

    def reject(self):
        if not self._progress_started and self.viewer_launcher.is_open:
            self._waiting_for_viewer_close = True
            self.hide()
            return
        super().reject()

    def _accept_if_ready(self):
        if self.selected_folder and self.selected_file:
            self.accept()
        else:
            QMessageBox.warning(self, self._text("error_title"), self._text("not_selected"))

    def _update_elapsed(self):
        seconds = max(0, int(time.monotonic() - self._progress_started_at))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"
        self.progress_elapsed.setText(self._text("progress_heartbeat").format(elapsed=elapsed))

    def _set_progress_step(self, index):
        steps = self._progress_steps()
        self.progress_step_index = max(self.progress_step_index, index)
        for position, label in enumerate(self.progress_step_labels):
            if position < self.progress_step_index:
                label.setText("\u2713 " + steps[position]["label"])
                label.setStyleSheet("background: #dcefe3; color: #1e5f36; padding: 5px")
            elif position == self.progress_step_index:
                label.setText("\u25b6 " + steps[position]["label"])
                label.setStyleSheet("background: #fff3cd; color: #6b4b00; padding: 5px")
            else:
                label.setText(f"{position + 1}. " + steps[position]["label"])
                label.setStyleSheet("background: #dbe5ef; color: #33485c; padding: 5px")

    def _progress_steps(self):
        return [
            {"label": self._text("progress_step_check"), "patterns": ("問題のあるPDF", "すべてのPDFファイル")},
            {"label": self._text("progress_step_tree"), "patterns": ("フォルダー構造", "しおり順")},
            {"label": self._text("progress_step_merge"), "patterns": ("PDFファイルを結合",)},
            {"label": self._text("progress_step_pages"), "patterns": ("PDFページ", "ページ番号を追加")},
            {"label": self._text("progress_step_bookmarks"), "patterns": ("親しおり", "子しおり", "しおり名", "クリック位置")},
            {"label": self._text("progress_step_save"), "patterns": ("一時PDF", "最終PDF", "PDF作成が完了")},
        ]

    def show_progress(self):
        self._progress_started = True
        self.paths_group.hide()
        self.intro_panel.hide()
        self.footer_panel.hide()
        self.settings_scroll.hide()
        for widget in self.preset_row_widgets:
            widget.hide()
        self.run_button.hide()
        self.cancel_button.hide()
        self.progress_group.show()
        self.progress_bar.setRange(0, 0)
        self.progress_status.setText(self._text("progress_started").strip())
        self._progress_started_at = time.monotonic()
        self._update_elapsed()
        self.progress_timer.start(1000)
        self.progress_step_index = -1
        self._set_progress_step(0)
        self.retry_button.hide()
        self.show()

    def queue_progress(self, message):
        if message:
            self.progress_emitter.message.emit(message)

    def append_progress(self, message):
        if not message:
            return
        self.progress_text.moveCursor(self.progress_text.textCursor().MoveOperation.End)
        self.progress_text.insertPlainText(message)
        lines = message.strip().splitlines()
        if lines:
            self.progress_status.setText(lines[-1])
        for index, step in enumerate(self._progress_steps()):
            if any(pattern in message for pattern in step["patterns"]):
                self._set_progress_step(index)
                break

    def wait_for_worker(self, worker_thread):
        self.show_progress()
        loop = QEventLoop(self)
        timer = QTimer(self)
        timer.setInterval(50)
        timer.timeout.connect(lambda: loop.quit() if not worker_thread.is_alive() else None)
        timer.start()
        loop.exec()
        timer.stop()
        worker_thread.join()

    def finish_progress(self, success=True):
        self.progress_timer.stop()
        if success:
            self._set_progress_step(len(self.progress_step_labels) - 1)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1 if success else 0)
        self.append_progress("\n" + self._text("progress_done" if success else "progress_failed") + "\n")
        if not success:
            self.append_progress(self._text("retry_hint") + "\n")
            self.retry_button.show()
        self.cancel_button.show()

    def retry(self):
        self.retry_requested = True
        self.retry_button.hide()
        if self._action_loop is not None:
            self._action_loop.quit()

    def wait_for_action(self):
        if self._user_closed:
            return
        self._action_loop = QEventLoop(self)
        self._action_loop.exec()
        self._action_loop = None

    def _on_finished(self, _result):
        if self._progress_started:
            self._user_closed = True
            if self._action_loop is not None:
                self._action_loop.quit()
            self.dialog_bridge.close()

    def closeEvent(self, event):
        if not self._progress_started and self.viewer_launcher.is_open:
            self._waiting_for_viewer_close = True
            self.hide()
            event.ignore()
            return
        self.progress_timer.stop()
        if self._progress_started:
            self._on_finished(self.result())
        super().closeEvent(event)

    def show_error_message(self, message):
        if self._user_closed:
            return
        QMessageBox.critical(self, self._text("error_title"), message)

    def confirm_exit_after_completion(self, issue_count=0, report_path=None):
        if self._user_closed:
            return True
        message = self._text("completion_exit_message")
        if issue_count:
                        message = (
                            "PDFの作成が完了しましたが、一部のファイルを処理できませんでした。\n"
                            f"エラー/警告: {issue_count} 件\n"
                        )
                        if report_path:
                            message += f"詳細レポート:\n{report_path}\n"
                        message += "プログラムを終了しますか。"
        accepted = QMessageBox.question(
            self, self._text("completion_title"), message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        ) == QMessageBox.StandardButton.Ok
        if accepted:
            self.close()
        return accepted

    def selection_result(self):
        values = self.current_ui_settings()
        return (
            self.selected_folder, self.selected_file,
            values["add_bookmark_page_number"], values["add_page"], values["convert_office"],
            values["confirm_temp_folder_delete"], values["ppt_slide_bookmarks"],
            values["convert_mail"], "auto", values["resize_pdf"], values["resize_size"],
            values["preflight_detail_repair"], values["preflight_confirm"],
            dict(SAVE_MODE_OPTIONS[values["save_mode"]]["save_options"]),
            values["asper_format"], values["keep_pdf_extension"], values["add_pdf_page_numbers"],
            page_number_options(values),
            1.0, 1.0, True, values["bookmark_view_mode"],
            values["base_view_width"], values["base_view_height"],
            values["expand_all"], values["collapse_level"], self,
        )


def select_folder_and_file(launch_config=None):
    app = QApplication.instance() or QApplication([])
    selector = FileSelectorApp()
    selector._application = app
    if launch_config is not None:
        selector.apply_launch_config(launch_config)
    if getattr(launch_config, "auto_start", False):
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, selector._accept_if_ready)
    quit_on_last_window = app.quitOnLastWindowClosed()
    app.setQuitOnLastWindowClosed(False)
    try:
        selection_code = selector.exec()
    finally:
        app.setQuitOnLastWindowClosed(quit_on_last_window)
    if selection_code != QDialog.DialogCode.Accepted:
        return (None, None) + (None,) * 24 + (selector,)
    return selector.selection_result()

class ProgressWriter:
    def __init__(self, progress_ui, original=None):
        self.progress_ui = progress_ui
        self.original = original

    def write(self, message):
        if self.original is not None:
            self.original.write(message)
        if self.progress_ui is not None:
            self.progress_ui.queue_progress(message)

    def flush(self):
        if self.original is not None:
            self.original.flush()