import ctypes
import json
import os
import queue
import sys
import time
from datetime import datetime


def configure_tcl_tk_paths():
    candidate_roots = [
        os.path.dirname(sys.executable),
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "kojiPDFv2.dist"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "kojiPDF.dist"),
    ]

    for root in candidate_roots:
        tcl_dir = os.path.join(root, "tcl")
        tk_dir = os.path.join(root, "tk")
        if os.path.exists(os.path.join(tcl_dir, "init.tcl")) and os.path.exists(os.path.join(tk_dir, "tk.tcl")):
            os.environ.setdefault("TCL_LIBRARY", tcl_dir)
            os.environ.setdefault("TK_LIBRARY", tk_dir)
            break


configure_tcl_tk_paths()

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

import ttkbootstrap as tb
from PIL import Image, ImageDraw, ImageFont, ImageTk

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 850
CONTENT_MAX_WIDTH = 880
MIN_WINDOW_WIDTH = 860
MIN_WINDOW_HEIGHT = 560
SCREEN_MARGIN_WIDTH = 40
SCREEN_MARGIN_HEIGHT = 70
WINDOW_HEIGHT_PADDING = 12
TK_SCALING_BASELINE = 96 / 72
WINDOWS_BASELINE_DPI = 96
APP_BG = "#e2e8f0"
PANEL_BG = "#ffffff"
BAND_BG = "#fbfdff"
SUBTLE_BG = "#edf3f8"
BORDER_COLOR = "#c8d3df"
TEXT_COLOR = "#102033"
MUTED_TEXT_COLOR = "#33485c"
SECTION_TEXT_COLOR = "#073f66"
STATUS_TEXT_COLOR = "#516475"
RUN_BUTTON_FILL = "#8f1d2c"
RUN_BUTTON_FILL_HOVER = "#a92536"
SAVE_MODE_OPTIONS = {
    "speed": {"save_options": {"garbage": 1, "deflate": False, "auto_clean_on_warning": False}},
    "balanced": {"save_options": {"garbage": 1, "deflate": True, "auto_clean_on_warning": False}},
    "smaller_file": {"save_options": {"garbage": 4, "deflate": True, "auto_clean_on_warning": True}},
}
PAGE_NUMBER_FONT_LABELS = {
    "ja": {
        "helv": "ゴシック体",
        "cour": "等幅文字",
        "tiro": "明朝体",
    },
    "en": {
        "helv": "Sans serif",
        "cour": "Monospace",
        "tiro": "Serif",
    },
}
PAGE_NUMBER_COLOR_LABELS = {
    "ja": {
        "red": "赤",
        "blue": "青",
        "black": "黒",
    },
    "en": {
        "red": "Red",
        "blue": "Blue",
        "black": "Black",
    },
}
PAGE_NUMBER_COLOR_VALUES = {
    "red": (1, 0, 0),
    "blue": (0, 0, 1),
    "black": (0, 0, 0),
}
BOOKMARK_VIEW_MODE_LABELS = {
    "ja": {
        "adjust": "補正値で調整",
        "fit_width": "幅に合わせる",
        "fit_height": "高さに合わせる",
        "fit_page": "ページ全体",
    },
    "en": {
        "adjust": "Adjusted position",
        "fit_width": "Fit width",
        "fit_height": "Fit height",
        "fit_page": "Fit page",
    },
}
PRESET_CODES = ("none", "paperless", "mail", "asp", "custom1", "custom2")
BUILT_IN_PRESET_CODES = ("paperless", "mail", "asp")
DEFAULT_UI_SETTINGS = {
    "convert_office": False,
    "convert_mail": False,
    "eml_encoding": "auto",
    "ppt_slide_bookmarks": False,
    "confirm_temp_folder_delete": False,
    "resize_pdf": False,
    "resize_size": "A4",
    "preflight_detail_repair": False,
    "preflight_confirm": False,
    "save_mode": "balanced",
    "add_bookmark_page_number": False,
    "add_page": False,
    "expand_all": False,
    "collapse_level": 1,
    "keep_pdf_extension": False,
    "add_pdf_page_numbers": False,
    "page_start_number": 1,
    "page_font_size": 30,
    "page_margin_right": 10,
    "page_margin_bottom": 10,
    "page_font": "helv",
    "page_color": "red",
    "page_opacity": 0.20,
    "bookmark_view_mode": "fit_page",
    "scale_mode": "absolute",
    "scale_x": 1.00,
    "scale_y": 1.00,
    "base_view_width": 330,
    "base_view_height": 210,
    "asper_format": False,
}
BUILT_IN_PRESETS = {
    "paperless": {
        **DEFAULT_UI_SETTINGS,
        "convert_office": True,
        "resize_pdf": True,
        "resize_size": "A4",
        "save_mode": "balanced",
        "add_bookmark_page_number": True,
        "add_page": True,
        "expand_all": False,
        "collapse_level": 1,
        "add_pdf_page_numbers": True,
        "page_start_number": 1,
        "page_font_size": 30,
        "page_margin_right": 10,
        "page_margin_bottom": 10,
        "page_font": "helv",
        "page_color": "red",
        "page_opacity": 0.20,
        "scale_mode": "absolute",
    },
    "mail": {
        **DEFAULT_UI_SETTINGS,
        "convert_office": True,
        "convert_mail": True,
        "eml_encoding": "auto",
        "resize_pdf": True,
        "resize_size": "A4",
        "save_mode": "balanced",
        "add_bookmark_page_number": True,
        "add_page": True,
        "expand_all": False,
        "collapse_level": 1,
        "add_pdf_page_numbers": True,
        "page_start_number": 1,
        "page_font_size": 30,
        "page_margin_right": 10,
        "page_margin_bottom": 10,
        "page_font": "helv",
        "page_color": "red",
        "page_opacity": 0.20,
        "scale_mode": "absolute",
    },
    "asp": {
        **DEFAULT_UI_SETTINGS,
        "convert_office": False,
        "resize_pdf": False,
        "resize_size": "A4",
        "preflight_detail_repair": True,
        "save_mode": "speed",
        "add_bookmark_page_number": True,
        "add_page": True,
        "expand_all": False,
        "collapse_level": 1,
        "add_pdf_page_numbers": True,
        "page_start_number": 1,
        "page_font_size": 100,
        "page_margin_right": 10,
        "page_margin_bottom": 10,
        "page_font": "helv",
        "page_color": "red",
        "page_opacity": 0.20,
        "scale_mode": "absolute",
        "asper_format": True,
    },
}


def settings_file_path():
    base_dir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base_dir, "kojiPDF", "settings.json")


def _scaled_pixel(value, factor):
    if value == 0:
        return 0
    return max(1, int(round(value * factor)))


def get_window_dpi(window):
    if sys.platform == "win32":
        hwnd = None
        try:
            hwnd = window.winfo_id()
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            if dpi:
                return int(dpi)
        except (AttributeError, OSError, tk.TclError):
            pass

        if hwnd is not None:
            hdc = None
            try:
                hdc = ctypes.windll.user32.GetDC(hwnd)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
                if dpi:
                    return int(dpi)
            except (AttributeError, OSError):
                pass
            finally:
                if hdc:
                    ctypes.windll.user32.ReleaseDC(hwnd, hdc)

    return int(round(float(window.tk.call("tk", "scaling")) * 72))


def find_resource_path(filename):
    candidate_roots = [
        os.path.dirname(sys.executable),
        os.path.dirname(os.path.abspath(__file__)),
    ]
    for root in candidate_roots:
        for relative_path in (filename, os.path.join("assets", "icons", filename)):
            path = os.path.join(root, relative_path)
            if os.path.exists(path):
                return path
    return None


def debug_log(message):
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(local_app_data, "kojiPDF")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "kojiPDF_startup.log")
        with open(log_path, "a", encoding="utf-8") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def _circle_mask(size, scale):
    mask = Image.new("L", (size * scale, size * scale), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
    return mask


def _scaled_points(points, scale):
    return [(x * scale, y * scale) for x, y in points]


def make_flag_image(flag, state, ui_scale=1.0):
    size = 44
    flag_size = 36
    offset = 4
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (255, 255, 255, 0))
    canvas_draw = ImageDraw.Draw(canvas)
    button_fill = "#eaf6fc" if state == "hover" else "#d7eef9" if state == "checked" else "#e7ecf2"
    canvas_draw.ellipse((1 * scale, 1 * scale, 43 * scale, 43 * scale), fill=button_fill)
    flag_image = Image.new("RGBA", (flag_size * scale, flag_size * scale), (255, 255, 255, 0))
    draw = ImageDraw.Draw(flag_image)

    if flag == "jp":
        draw.ellipse((0, 0, flag_size * scale - 1, flag_size * scale - 1), fill="#ffffff")
        center = flag_size * scale // 2
        radius = 6 * scale
        draw.ellipse((center - radius, center - radius, center + radius, center + radius), fill="#bc002d")
    else:
        draw.ellipse((0, 0, flag_size * scale - 1, flag_size * scale - 1), fill="#012169")
        draw.polygon(_scaled_points([(3, 10), (26, 33), (33, 26), (10, 3)], scale), fill="#ffffff")
        draw.polygon(_scaled_points([(26, 3), (3, 26), (10, 33), (33, 10)], scale), fill="#ffffff")
        draw.polygon(_scaled_points([(5, 8), (28, 31), (31, 28), (8, 5)], scale), fill="#c8102e")
        draw.polygon(_scaled_points([(28, 5), (5, 28), (8, 31), (31, 8)], scale), fill="#c8102e")
        draw.rectangle((0, 13 * scale, flag_size * scale, 23 * scale), fill="#ffffff")
        draw.rectangle((13 * scale, 0, 23 * scale, flag_size * scale), fill="#ffffff")
        draw.rectangle((0, 16 * scale, flag_size * scale, 20 * scale), fill="#c8102e")
        draw.rectangle((16 * scale, 0, 20 * scale, flag_size * scale), fill="#c8102e")

    flag_image.putalpha(_circle_mask(flag_size, scale))
    canvas.alpha_composite(flag_image, (offset * scale, offset * scale))
    if state in {"hover", "checked"}:
        glow = Image.new("RGBA", (size * scale, size * scale), (255, 255, 255, 0))
        glow_draw = ImageDraw.Draw(glow)
        alpha = 45 if state == "hover" else 70
        glow_draw.ellipse((1 * scale, 1 * scale, 43 * scale, 43 * scale), fill=(23, 142, 200, alpha))
        glow.alpha_composite(canvas)
        canvas = glow

    display_size = _scaled_pixel(size, ui_scale)
    image = canvas.resize((display_size, display_size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)


def make_run_image(text, hover=False, ui_scale=1.0):
    size = 74
    scale = 4
    image = Image.new("RGBA", (size * scale, size * scale), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    fill = RUN_BUTTON_FILL_HOVER if hover else RUN_BUTTON_FILL
    button_fill = "#eaf6fc" if hover else SUBTLE_BG
    draw.ellipse((1 * scale, 1 * scale, 73 * scale, 73 * scale), fill=button_fill)
    draw.ellipse((6 * scale, 6 * scale, 68 * scale, 68 * scale), fill=fill)
    for font_name in ("meiryob.ttc", "meiryo.ttc", "arialbd.ttf"):
        try:
            font = ImageFont.truetype(font_name, 14 * scale)
            break
        except OSError:
            font = None
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size * scale - (bbox[2] - bbox[0])) / 2
    y = (size * scale - (bbox[3] - bbox[1])) / 2 - 2 * scale
    draw.text((x, y), text, fill="#ffffff", font=font)
    display_size = _scaled_pixel(size, ui_scale)
    image = image.resize((display_size, display_size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)


def make_intro_icon_image(ui_scale=1.0):
    icon_path = find_resource_path("smallicon_v2.png")
    if icon_path is None:
        debug_log("Intro icon not found: smallicon_v2.png")
        return None

    try:
        image = Image.open(icon_path).convert("RGBA")
        size = _scaled_pixel(62, ui_scale)
        image = image.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except (OSError, tk.TclError) as exc:
        debug_log(f"Intro icon load failed: {icon_path}: {exc}")
        return None


class FlagButton(tk.Label):
    def __init__(self, master, flag, command, tooltip_text="", ui_scale=1.0, **kwargs):
        self.bg_color = kwargs.pop("bg", "#ffffff")
        super().__init__(
            master,
            bd=0,
            bg=self.bg_color,
            cursor="hand2",
            **kwargs,
        )
        self.flag = flag
        self.command = command
        self.tooltip_text = tooltip_text
        self.ui_scale = ui_scale
        self.checked = False
        self.hover = False
        self.images = {}
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.draw()

    def set_checked(self, checked):
        self.checked = checked
        self.draw()

    def _click(self, _event):
        self.command()

    def _enter(self, _event):
        self.hover = True
        self.draw()

    def _leave(self, _event):
        self.hover = False
        self.draw()

    def draw(self):
        state = "checked" if self.checked else "hover" if self.hover else "normal"
        if state not in self.images:
            self.images[state] = make_flag_image(self.flag, state, self.ui_scale)
        self.configure(bg=self.bg_color, image=self.images[state])
        self.image = self.images[state]


class FileSelectorApp:
    def __init__(self):
        self.default_folder = os.path.expanduser("~/Documents")
        self.selected_folder = None
        self.selected_file = None
        self.accepted = False
        self.retry_requested = False
        self._progress_queue = queue.Queue()
        self._progress_poll_after_id = None
        self._progress_heartbeat_after_id = None
        self._progress_started_at = None
        self._progress_last_message_at = None
        self.language = "ja"
        self.custom_presets = self._load_custom_presets()
        self.window = tb.Window(themename="flatly")
        self.tk_scaling = float(self.window.tk.call("tk", "scaling"))
        self.ui_scale = self.tk_scaling / TK_SCALING_BASELINE
        self.current_dpi = get_window_dpi(self.window)
        self._dpi_status_after_id = None
        debug_log(
            "Tk DPI scaling initialized: "
            f"tk_scaling={self.tk_scaling:.4f}, ui_scale={self.ui_scale:.4f}, "
            f"dpi={self.current_dpi}, screen={self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}"
        )
        self.window.title("kojiPDF - Built with Python by Code4Construct")
        self.window.geometry(f"{self._px(WINDOW_WIDTH)}x{self._px(WINDOW_HEIGHT)}")
        self.window.minsize(self._px(MIN_WINDOW_WIDTH), self._px(MIN_WINDOW_HEIGHT))
        self.window.configure(bg=APP_BG)
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        self._build_window()
        self._apply_language()
        self.toggle_bookmark_view_mode()
        self.toggle_collapse_spinbox()
        self.toggle_page_number_options()
        self.toggle_office_options()
        self._update_dpi_status()
        self.window.bind("<Configure>", self._schedule_dpi_status_update, add="+")
        debug_log("Tkinter UI loaded successfully")

    def _px(self, value):
        return _scaled_pixel(int(value), self.ui_scale)

    def _pad(self, *values):
        return tuple(self._px(value) for value in values)

    def _scale_padding(self, value):
        if isinstance(value, tuple):
            return self._pad(*value)
        return self._px(value)

    def _format_dpi_status(self):
        dpi = max(1, get_window_dpi(self.window))
        percent = int(round(dpi / WINDOWS_BASELINE_DPI * 100))
        return dpi, f"{dpi} DPI / {percent}%"

    def _schedule_dpi_status_update(self, _event=None):
        if self._dpi_status_after_id is not None:
            return
        try:
            self._dpi_status_after_id = self.window.after(120, self._update_dpi_status)
        except tk.TclError:
            pass

    def _update_dpi_status(self):
        self._dpi_status_after_id = None
        if not hasattr(self, "dpi_status_text"):
            return
        try:
            dpi, status_text = self._format_dpi_status()
            self.current_dpi = dpi
            self.dpi_status_text.set(status_text)
        except tk.TclError:
            pass

    def _build_window(self):
        style = self.window.style
        style.configure("Koji.TFrame", background=APP_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)
        style.configure("Band.TFrame", background=BAND_BG)
        title_font = ("Segoe UI Variable Display", 22, "bold")
        style.configure("Title.TLabel", background=APP_BG, foreground=TEXT_COLOR, font=title_font)
        style.configure("Subtitle.TLabel", background=APP_BG, foreground=MUTED_TEXT_COLOR, font=("Yu Gothic UI", 11))
        style.configure("IntroSubtitle.TLabel", background=PANEL_BG, foreground=MUTED_TEXT_COLOR, font=("Yu Gothic UI", 11))
        style.configure("Notice.TLabel", background=PANEL_BG, foreground=SECTION_TEXT_COLOR, font=("Yu Gothic UI", 9, "bold"))
        style.configure("License.TLabel", background=PANEL_BG, foreground=MUTED_TEXT_COLOR, font=("Yu Gothic UI", 7))
        style.configure("LicensePanel.TFrame", background=SUBTLE_BG)
        style.configure("LicenseInner.TFrame", background=PANEL_BG)
        style.configure("Path.TLabel", background=PANEL_BG, foreground=TEXT_COLOR, borderwidth=1, relief="solid", padding=self._px(7))
        style.configure("Field.TLabel", background=BAND_BG, foreground=TEXT_COLOR, font=("Yu Gothic UI", 10))
        style.configure("Section.TLabel", background=BAND_BG, foreground=SECTION_TEXT_COLOR, font=("Yu Gothic UI", 11, "bold"))
        style.configure("FormLabel.TLabel", background=PANEL_BG, foreground=MUTED_TEXT_COLOR, font=("Yu Gothic UI", 10, "bold"))
        style.configure("Run.TButton", font=("Yu Gothic UI", 12, "bold"), padding=self._pad(26, 10))

        root = tb.Frame(self.window, style="Koji.TFrame", padding=self._pad(10, 8, 10, 8))
        root.place(relx=0.5, y=0, anchor="n", width=self._px(CONTENT_MAX_WIDTH))
        self.root_frame = root

        header = tk.Frame(root, bg=PANEL_BG, height=self._px(38))
        header.pack_propagate(False)
        header.pack(fill="x", pady=self._pad(0, 6))
        header.columnconfigure(0, minsize=self._px(96))
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, minsize=self._px(96))
        header_left_balance = tk.Frame(header, bg=PANEL_BG, width=self._px(96))
        header_left_balance.grid(row=0, column=0, sticky="nsew")
        self.title_label = tk.Label(
            header,
            bg=PANEL_BG,
            fg=TEXT_COLOR,
            font=title_font,
            anchor="center",
        )
        self.title_label.grid(row=0, column=1, sticky="nsew")
        flag_holder = tk.Frame(header, bg=PANEL_BG, width=self._px(96))
        flag_holder.grid(row=0, column=2, sticky="nsew")
        self.japanese_button = FlagButton(flag_holder, "jp", lambda: self._set_language("ja"), bg=PANEL_BG, ui_scale=self.ui_scale)
        self.english_button = FlagButton(flag_holder, "gb", lambda: self._set_language("en"), bg=PANEL_BG, ui_scale=self.ui_scale)
        self.english_button.pack(side="right", padx=self._pad(6, 0))
        self.japanese_button.pack(side="right", padx=self._pad(6, 0))

        intro_panel = tb.Frame(root, style="Panel.TFrame", padding=self._pad(8, 4))
        intro_panel.pack(fill="x", pady=self._pad(0, 4))

        self.subtitle_label = tb.Label(intro_panel, style="IntroSubtitle.TLabel", wraplength=self._px(720))

        notice_panel = tk.Frame(intro_panel, bg=PANEL_BG)
        notice_panel.columnconfigure(0, minsize=self._px(70))
        notice_panel.columnconfigure(1, weight=1)
        notice_panel.columnconfigure(2, minsize=self._px(238))
        notice_panel.rowconfigure(0, weight=1)
        notice_panel.pack(fill="x", expand=True)
        self.notice_panel = notice_panel
        self.intro_icon_image = make_intro_icon_image(self.ui_scale)

        if self.intro_icon_image is not None:
            self.intro_icon_label = tk.Label(
                notice_panel,
                image=self.intro_icon_image,
                bg=PANEL_BG,
                bd=0,
                width=self._px(64),
                height=self._px(64),
            )
        else:
            self.intro_icon_label = tk.Label(
                notice_panel,
                text="PDF",
                bg=RUN_BUTTON_FILL,
                fg=PANEL_BG,
                bd=0,
                font=("Segoe UI Variable Display", 16, "bold"),
                width=4,
                height=2,
            )
        self.intro_icon_label.grid(row=0, column=0, sticky="w", padx=self._pad(0, 8))
        self.notice_label = tb.Label(notice_panel, style="Notice.TLabel", wraplength=self._px(630), justify="left")
        self.notice_label.grid(row=0, column=1, sticky="ew")
        self._build_preset_controls(notice_panel)
        notice_panel.bind("<Configure>", self._sync_notice_wraplength)

        top_panel = tk.Frame(
            root,
            bg=PANEL_BG,
            padx=self._px(10),
            pady=self._px(8),
        )
        top_panel.pack(fill="x", pady=self._pad(0, 4))
        top_panel.columnconfigure(1, weight=1)
        self.top_panel = top_panel
        self.folder_button = tb.Button(top_panel, bootstyle="secondary-outline", command=self.select_folder)
        self.folder_button.grid(row=0, column=0, sticky="ew", padx=self._pad(0, 10), pady=self._px(2))
        self.folder_text = tk.StringVar()
        self.folder_label = tb.Label(top_panel, textvariable=self.folder_text, style="Path.TLabel", wraplength=self._px(560))
        self.folder_label.grid(row=0, column=1, sticky="ew", pady=self._px(2))
        self.file_button = tb.Button(top_panel, bootstyle="secondary-outline", command=self.select_save_file)
        self.file_button.grid(row=1, column=0, sticky="ew", padx=self._pad(0, 10), pady=self._px(2))
        self.file_text = tk.StringVar()
        self.file_label = tb.Label(top_panel, textvariable=self.file_text, style="Path.TLabel", wraplength=self._px(560))
        self.file_label.grid(row=1, column=1, sticky="ew", pady=self._px(2))
        self.run_button = tk.Label(
            top_panel,
            bd=0,
            bg=PANEL_BG,
            cursor="hand2",
        )
        self.run_button.grid(row=0, column=2, rowspan=2, sticky="ns", padx=self._pad(12, 0))
        self.run_button.bind("<Button-1>", lambda _event: self.finish())
        self.run_button.bind("<Enter>", lambda _event: self._draw_run_button(hover=True))
        self.run_button.bind("<Leave>", lambda _event: self._draw_run_button(hover=False))

        self.options_group = tb.Frame(root, style="Koji.TFrame")
        self.options_group.pack(fill="x")
        self.options_group.columnconfigure(0, weight=1)
        self.options_group.columnconfigure(1, weight=0, minsize=self._px(290))

        self._build_general_options()
        self._build_bookmark_options()
        self._build_page_number_options()
        self._build_scale_options()
        self._build_asp_options()

        license_notice_panel = tb.Frame(root, style="LicensePanel.TFrame", padding=self._pad(6, 5, 6, 5))
        license_notice_panel.pack(fill="x")
        self.license_notice_panel = license_notice_panel
        license_inner_panel = tb.Frame(license_notice_panel, style="LicenseInner.TFrame")
        license_inner_panel.pack(fill="both", expand=True)
        license_inner_panel.columnconfigure(0, weight=1)
        license_inner_panel.columnconfigure(1, minsize=self._px(120))
        license_inner_panel.rowconfigure(0, weight=1)
        self.license_notice_label = tb.Label(
            license_inner_panel,
            style="License.TLabel",
            wraplength=self._px(720),
            justify="left",
        )
        self.license_notice_label.grid(row=0, column=0, sticky="ew")
        self.dpi_status_text = tk.StringVar()
        self.dpi_status_label = tk.Label(
            license_inner_panel,
            textvariable=self.dpi_status_text,
            bg=PANEL_BG,
            fg=STATUS_TEXT_COLOR,
            font=("Yu Gothic UI", 8),
            anchor="se",
            padx=self._px(8),
            pady=self._px(2),
        )
        self.dpi_status_label.grid(row=0, column=1, sticky="se")
        self._draw_run_button()

    def _build_preset_controls(self, parent):
        frame = tb.Frame(parent, style="Panel.TFrame")
        frame.grid(row=0, column=2, sticky="e", padx=self._pad(10, 0))
        self.preset_label = tb.Label(frame, style="FormLabel.TLabel")
        self.preset_label.grid(row=0, column=0, sticky="w", pady=self._pad(0, 2))
        self.reset_preset_button = tb.Button(
            frame,
            width=2,
            bootstyle="secondary-outline",
            command=self.reset_saved_presets,
        )
        self.reset_preset_button.grid(row=0, column=1, sticky="e", pady=self._pad(0, 2))
        self.preset_var = tk.StringVar()
        self.preset_combo = self._make_combobox(
            frame,
            textvariable=self.preset_var,
            values=self._preset_display_values(),
            width=18,
        )
        self.preset_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_preset(), add="+")
        self.preset_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=self._px(1))
        self.save_preset_button = tb.Button(frame, bootstyle="secondary-outline", command=self.save_selected_preset)
        self.save_preset_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=self._px(2))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)
        self._set_preset_code("none")

    def _make_combobox(self, parent, **kwargs):
        kwargs.setdefault("state", "readonly")
        combo = tb.Combobox(parent, **kwargs)
        combo.bind("<<ComboboxSelected>>", self._clear_combobox_selection, add="+")
        combo.bind("<FocusIn>", self._clear_combobox_selection, add="+")
        combo.bind("<ButtonRelease-1>", self._clear_combobox_selection, add="+")
        return combo

    def _clear_combobox_selection(self, event):
        combo = event.widget
        try:
            combo.selection_clear()
            combo.icursor("end")
            self.window.focus_set()
        except tk.TclError:
            pass

    def _band(self, row, title_attr, parent=None, column=0, columnspan=1, padx=(0, 0), pady=(0, 4)):
        parent = parent or self.options_group
        frame = tb.Frame(
            parent,
            style="Band.TFrame",
            padding=self._pad(8, 7),
        )
        frame.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="nsew",
            padx=self._scale_padding(padx),
            pady=self._scale_padding(pady),
        )
        frame.columnconfigure(0, weight=1)
        title_row = tb.Frame(frame, style="Band.TFrame")
        title_row.grid(row=0, column=0, sticky="w", columnspan=8, pady=self._pad(0, 4))
        title_label = tb.Label(title_row, style="Section.TLabel")
        title_label.pack(side="left")
        setattr(self, title_attr, title_label)
        return frame

    def _build_general_options(self):
        frame = self._band(0, "general_section_label", column=0, padx=(0, 4))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)
        self.add_page_var = tk.BooleanVar(value=False)
        self.convert_office_var = tk.BooleanVar(value=False)
        self.convert_mail_var = tk.BooleanVar(value=False)
        self.eml_encoding_var = tk.StringVar(value="Auto detect")
        self.ppt_slide_bookmarks_var = tk.BooleanVar(value=False)
        self.confirm_temp_folder_delete_var = tk.BooleanVar(value=False)
        self.resize_pdf_var = tk.BooleanVar(value=False)
        self.preflight_detail_repair_var = tk.BooleanVar(value=False)
        self.preflight_confirm_var = tk.BooleanVar(value=False)
        self.asper_format_var = tk.BooleanVar(value=False)
        self.keep_pdf_extension_var = tk.BooleanVar(value=False)
        self.save_mode_var = tk.StringVar(value="balanced")
        self.convert_office_checkbox = tb.Checkbutton(
            frame,
            variable=self.convert_office_var,
            bootstyle="primary-round-toggle",
            command=self.toggle_office_options,
        )
        self.ppt_slide_bookmarks_checkbox = tb.Checkbutton(
            frame,
            variable=self.ppt_slide_bookmarks_var,
            bootstyle="primary-round-toggle",
        )
        mail_options_row = tb.Frame(frame, style="Band.TFrame")
        eml_encoding_row = tb.Frame(frame, style="Band.TFrame")
        self.convert_mail_checkbox = tb.Checkbutton(
            mail_options_row,
            variable=self.convert_mail_var,
            bootstyle="primary-round-toggle",
            command=self.toggle_mail_options,
        )
        self.eml_encoding_label = tb.Label(eml_encoding_row, style="Field.TLabel")
        self.eml_encoding_combo = self._make_combobox(
            eml_encoding_row,
            textvariable=self.eml_encoding_var,
            values=self._eml_encoding_display_values(),
            width=13,
            state="disabled",
        )
        self.confirm_temp_folder_delete_checkbox = tb.Checkbutton(
            frame,
            variable=self.confirm_temp_folder_delete_var,
            bootstyle="primary-round-toggle",
        )
        resize_row = tb.Frame(frame, style="Band.TFrame")
        save_mode_frame = tb.Frame(frame, style="Band.TFrame")
        check_options_frame = tb.Frame(frame, style="Band.TFrame")
        self.resize_pdf_checkbox = tb.Checkbutton(resize_row, variable=self.resize_pdf_var, bootstyle="primary-round-toggle")
        self.error_check_label = tb.Label(check_options_frame, style="Field.TLabel")
        self.preflight_detail_repair_checkbox = tb.Checkbutton(
            check_options_frame,
            variable=self.preflight_detail_repair_var,
            bootstyle="primary-round-toggle",
        )
        self.preflight_confirm_checkbox = tb.Checkbutton(
            check_options_frame,
            variable=self.preflight_confirm_var,
            bootstyle="primary-round-toggle",
        )
        self.save_mode_label = tb.Label(save_mode_frame, style="Field.TLabel")
        self.save_mode_combo = self._make_combobox(
            save_mode_frame,
            textvariable=self.save_mode_var,
            values=self._save_mode_display_values(),
            width=13,
        )
        self.save_mode_combo.bind("<<ComboboxSelected>>", self._on_save_mode_selected)
        self._set_save_mode_code("balanced")
        self.convert_office_checkbox.grid(row=1, column=0, sticky="w", pady=self._px(3))
        mail_options_row.grid(row=2, column=0, sticky="w", padx=self._pad(66, 0), pady=self._px(3))
        self.convert_mail_checkbox.pack(side="left")
        eml_encoding_row.grid(row=3, column=0, sticky="w", padx=self._pad(96, 0), pady=self._px(2))
        self.eml_encoding_label.pack(side="left", padx=self._pad(0, 6))
        self.eml_encoding_combo.pack(side="left")
        self.ppt_slide_bookmarks_checkbox.grid(row=4, column=0, sticky="w", padx=self._pad(66, 0), pady=self._px(3))
        self.confirm_temp_folder_delete_checkbox.grid(row=5, column=0, sticky="w", padx=self._pad(66, 0), pady=self._px(3))
        resize_row.grid(row=6, column=0, sticky="w", pady=self._px(3))
        self.resize_pdf_checkbox.pack(side="left")
        self.resize_size_var = tk.StringVar(value="A4")
        self.resize_size_combo = self._make_combobox(resize_row, textvariable=self.resize_size_var, values=["A3", "A4", "A5", "B4", "B5"], width=8)
        self.resize_size_combo.pack(side="left", padx=self._pad(12, 0))
        save_mode_frame.grid(row=1, column=1, sticky="nw", padx=self._pad(26, 0), pady=self._px(3))
        self.save_mode_label.pack(side="left", padx=self._pad(0, 6))
        self.save_mode_combo.pack(side="left")
        check_options_frame.grid(row=4, column=1, rowspan=3, sticky="sw", padx=self._pad(18, 0), pady=self._px(1))
        self.error_check_label.grid(row=0, column=0, sticky="w", pady=self._pad(6, 0))
        self.preflight_detail_repair_checkbox.grid(row=1, column=0, sticky="w", pady=self._px(2))
        self.preflight_confirm_checkbox.grid(row=2, column=0, sticky="w", pady=self._px(2))

    def _build_page_number_options(self):
        frame = self._band(1, "page_number_section_label", column=0, columnspan=2)
        frame.columnconfigure(0, weight=1)

        self.add_pdf_page_numbers_var = tk.BooleanVar(value=False)
        self.add_pdf_page_numbers_checkbox = tb.Checkbutton(
            self.page_number_section_label.master,
            variable=self.add_pdf_page_numbers_var,
            bootstyle="primary-round-toggle",
            command=self.toggle_page_number_options,
        )
        self.add_pdf_page_numbers_checkbox.pack(side="left", padx=self._pad(12, 0))

        page_fields_frame = tb.Frame(frame, style="Band.TFrame")
        page_fields_frame.grid(row=1, column=0, columnspan=8, sticky="ew", pady=self._px(1))
        for col in range(4):
            page_fields_frame.columnconfigure(col, weight=1, uniform="page_number_fields")

        def make_page_field(row, column):
            field_frame = tb.Frame(page_fields_frame, style="Band.TFrame")
            field_frame.grid(row=row, column=column, sticky="", padx=self._pad(4, 4), pady=self._px(3))
            label = tb.Label(field_frame, style="Field.TLabel", width=13, anchor="e")
            label.pack(side="left", padx=self._pad(0, 6))
            return field_frame, label

        start_field, self.page_start_number_label = make_page_field(0, 0)
        self.page_start_number_spinbox = self._make_spinbox(start_field, 1, 9999, 1, 1, integer=True)
        self.page_start_number_spinbox.pack(side="left")
        font_size_field, self.page_font_size_label = make_page_field(0, 1)
        self.page_font_size_spinbox = self._make_spinbox(font_size_field, 1, 300, 1, 30, integer=True)
        self.page_font_size_spinbox.pack(side="left")
        margin_right_field, self.page_margin_right_label = make_page_field(0, 2)
        self.page_margin_right_spinbox = self._make_spinbox(margin_right_field, 0, 1000, 1, 10, integer=True)
        self.page_margin_right_spinbox.pack(side="left")
        margin_bottom_field, self.page_margin_bottom_label = make_page_field(0, 3)
        self.page_margin_bottom_spinbox = self._make_spinbox(margin_bottom_field, 0, 1000, 1, 10, integer=True)
        self.page_margin_bottom_spinbox.pack(side="left")

        font_field, self.page_font_label = make_page_field(1, 0)
        self.page_font_var = tk.StringVar(value=self._page_number_font_labels()["helv"])
        self.page_font_combo = self._make_combobox(
            font_field,
            textvariable=self.page_font_var,
            values=self._page_number_font_display_values(),
            width=10,
        )
        self.page_font_combo.pack(side="left")
        color_field, self.page_color_label = make_page_field(1, 1)
        self.page_color_var = tk.StringVar(value=self._page_number_color_labels()["red"])
        self.page_color_combo = self._make_combobox(
            color_field,
            textvariable=self.page_color_var,
            values=self._page_number_color_display_values(),
            width=10,
        )
        self.page_color_combo.pack(side="left")
        opacity_field, self.page_opacity_label = make_page_field(1, 2)
        self.page_opacity_spinbox = self._make_spinbox(opacity_field, 0.05, 1.00, 0.05, 0.20, integer=False)
        self.page_opacity_spinbox.pack(side="left")

    def _build_scale_options(self, parent=None):
        frame = self._band(2, "scale_section_label", parent=parent, column=0, padx=(0, 4))
        self.scale_section_label.master.grid_configure(columnspan=1, pady=0)
        frame.columnconfigure(0, minsize=self._px(144), weight=0)
        frame.columnconfigure(1, minsize=self._px(72), weight=0)
        frame.columnconfigure(2, minsize=self._px(104), weight=0)
        frame.columnconfigure(3, minsize=self._px(30), weight=0)
        frame.columnconfigure(4, minsize=self._px(76), weight=0)
        frame.columnconfigure(5, minsize=self._px(30), weight=0)
        frame.columnconfigure(6, weight=1)
        self.bookmark_view_mode_var = tk.StringVar(value=self._bookmark_view_mode_labels()["fit_page"])
        self.bookmark_view_mode_label = tb.Label(frame, style="Field.TLabel")
        self.bookmark_view_mode_combo = self._make_combobox(
            frame,
            textvariable=self.bookmark_view_mode_var,
            values=self._bookmark_view_mode_display_values(),
            width=12,
        )
        self.bookmark_view_mode_combo.bind("<<ComboboxSelected>>", lambda _event: self.toggle_bookmark_view_mode(), add="+")
        self.scale_mode_var = tk.StringVar(value="absolute")
        self.relative_scale_radio = tb.Radiobutton(
            frame,
            variable=self.scale_mode_var,
            value="relative",
            command=self.toggle_scale_mode,
            bootstyle="primary",
        )
        self.absolute_scale_radio = tb.Radiobutton(
            frame,
            variable=self.scale_mode_var,
            value="absolute",
            command=self.toggle_scale_mode,
            bootstyle="primary",
        )
        self.horizontal_scale_label = tb.Label(frame, style="Field.TLabel")
        self.vertical_scale_label = tb.Label(frame, style="Field.TLabel")
        self.base_view_width_label = tb.Label(frame, style="Field.TLabel")
        self.base_view_height_label = tb.Label(frame, style="Field.TLabel")
        self.scale_x_spinbox = self._make_spinbox(frame, 0.10, 2.00, 0.05, 1.00, integer=False)
        self.scale_y_spinbox = self._make_spinbox(frame, 0.10, 2.00, 0.05, 1.00, integer=False)
        self.base_view_width_spinbox = self._make_spinbox(frame, 100, 1000, 10, 330, integer=True)
        self.base_view_height_spinbox = self._make_spinbox(frame, 100, 1000, 10, 210, integer=True)
        self.base_view_width_spinbox.configure(width=6)
        self.base_view_height_spinbox.configure(width=6)
        self.bookmark_view_mode_label.grid(row=0, column=1, sticky="e", padx=self._pad(0, 4), pady=self._px(2))
        self.bookmark_view_mode_combo.grid(row=0, column=2, sticky="w", pady=self._px(2))
        self.base_view_width_label.grid(row=0, column=3, sticky="e", padx=self._pad(4, 4), pady=self._px(2))
        self.base_view_width_spinbox.grid(row=0, column=4, sticky="w", pady=self._px(2))
        self.base_view_height_label.grid(row=0, column=5, sticky="e", padx=self._pad(4, 4), pady=self._px(2))
        self.base_view_height_spinbox.grid(row=0, column=6, sticky="w", pady=self._px(2))

    def _build_bookmark_options(self, parent=None):
        frame = self._band(0, "bookmark_section_label", parent=parent, column=1, padx=(4, 0))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=0)
        frame.columnconfigure(2, weight=0)
        self.add_bookmark_page_number_var = tk.BooleanVar(value=False)
        self.add_page_checkbox = tb.Checkbutton(frame, variable=self.add_page_var, bootstyle="primary-round-toggle")
        self.add_bookmark_page_number_checkbox = tb.Checkbutton(
            frame,
            variable=self.add_bookmark_page_number_var,
            bootstyle="primary-round-toggle",
        )
        self.keep_pdf_extension_checkbox = tb.Checkbutton(
            frame,
            variable=self.keep_pdf_extension_var,
            bootstyle="primary-round-toggle",
        )
        self.expand_all_var = tk.BooleanVar(value=False)
        self.expand_all_checkbox = tb.Checkbutton(
            frame,
            variable=self.expand_all_var,
            bootstyle="primary-round-toggle",
            command=self.toggle_collapse_spinbox,
        )
        collapse_row = tb.Frame(frame, style="Band.TFrame")
        self.add_bookmark_page_number_checkbox.grid(row=1, column=0, sticky="w", pady=self._px(3))
        self.add_page_checkbox.grid(row=2, column=0, columnspan=3, sticky="w", pady=self._px(3))
        self.expand_all_checkbox.grid(row=3, column=0, sticky="w", pady=self._px(3))
        collapse_row.grid(row=4, column=0, columnspan=3, sticky="w", padx=self._pad(28, 0), pady=self._px(3))
        self.bookmark_open_level_label = tb.Label(collapse_row, style="Field.TLabel")
        self.bookmark_open_level_label.pack(side="left", padx=self._pad(0, 8))
        self.collapse_spinbox = self._make_spinbox(collapse_row, 1, 10, 1, 1, integer=True)
        self.collapse_spinbox.pack(side="left")
        self.keep_pdf_extension_checkbox.grid(row=5, column=0, columnspan=3, sticky="w", pady=self._px(3))

    def _build_asp_options(self):
        frame = self._band(2, "asp_section_label", column=1, padx=(4, 0))
        self.asper_format_checkbox = tb.Checkbutton(
            frame,
            variable=self.asper_format_var,
            bootstyle="primary-round-toggle",
        )
        self.asper_format_checkbox.grid(row=1, column=0, sticky="w", pady=self._px(3))

    def _make_spinbox(self, master, minimum, maximum, increment, value, integer):
        textvariable = tk.StringVar(value=str(int(value)) if integer else f"{value:.2f}")
        spinbox = tb.Spinbox(
            master,
            from_=minimum,
            to=maximum,
            increment=increment,
            textvariable=textvariable,
            width=8,
            justify="right",
        )
        spinbox._koji_var = textvariable
        spinbox._koji_integer = integer
        spinbox._koji_min = minimum
        spinbox._koji_max = maximum
        spinbox.bind("<FocusOut>", lambda _event, widget=spinbox: self._normalize_spinbox(widget))
        return spinbox

    def _draw_run_button(self, hover=False):
        if not self._widget_exists("run_button"):
            return
        key = "run_hover_image" if hover else "run_image"
        image = make_run_image(self._text("create_short"), hover, self.ui_scale)
        setattr(self, key, image)
        self.run_button.configure(bg=PANEL_BG, image=image)
        self.run_button.image = image

    def _spinbox_value(self, spinbox):
        self._normalize_spinbox(spinbox)
        value = float(spinbox._koji_var.get())
        return int(value) if spinbox._koji_integer else value

    def _set_spinbox_value(self, spinbox, value):
        spinbox._koji_var.set(str(value))
        self._normalize_spinbox(spinbox)

    def _normalize_spinbox(self, spinbox):
        try:
            value = float(spinbox._koji_var.get())
        except ValueError:
            value = spinbox._koji_min
        value = max(spinbox._koji_min, min(spinbox._koji_max, value))
        if spinbox._koji_integer:
            spinbox._koji_var.set(str(int(round(value))))
        else:
            spinbox._koji_var.set(f"{value:.2f}")

    def _set_language(self, language):
        self.language = language
        if self._widget_exists("japanese_button"):
            self.japanese_button.set_checked(language == "ja")
        if self._widget_exists("english_button"):
            self.english_button.set_checked(language == "en")
        self._apply_language()

    def _widget_exists(self, attr_name):
        widget = getattr(self, attr_name, None)
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False

    EML_ENCODING_CODES = ("auto", "utf-8", "cp932", "iso-2022-jp", "euc-jp", "utf-16")

    def _eml_encoding_labels(self):
        auto_label = "自動判定" if self.language == "ja" else "Auto detect"
        return {
            "auto": auto_label,
            "utf-8": "UTF-8",
            "cp932": "Shift-JIS",
            "iso-2022-jp": "ISO-2022-JP",
            "euc-jp": "EUC-JP",
            "utf-16": "UTF-16",
        }

    def _eml_encoding_display_values(self):
        labels = self._eml_encoding_labels()
        return [labels[code] for code in self.EML_ENCODING_CODES]

    def _set_eml_encoding_code(self, code):
        labels = self._eml_encoding_labels()
        self.eml_encoding_var.set(labels.get(code, labels["auto"]))

    def _current_eml_encoding_code(self):
        selected = self.eml_encoding_var.get()
        labels = self._eml_encoding_labels()
        for code, label in labels.items():
            if selected == label:
                return code
        legacy_labels = {
            "Auto detect": "auto",
            "自動判定": "auto",
            "UTF-8": "utf-8",
            "Shift-JIS": "cp932",
            "ISO-2022-JP": "iso-2022-jp",
            "EUC-JP": "euc-jp",
            "UTF-16": "utf-16",
        }
        return legacy_labels.get(selected, "auto")

    PAGE_NUMBER_FONT_CODES = ("helv", "cour", "tiro")

    def _page_number_font_labels(self):
        return PAGE_NUMBER_FONT_LABELS.get(self.language, PAGE_NUMBER_FONT_LABELS["en"])

    def _page_number_font_display_values(self):
        labels = self._page_number_font_labels()
        return [labels[code] for code in self.PAGE_NUMBER_FONT_CODES]

    def _set_page_number_font_code(self, code):
        labels = self._page_number_font_labels()
        self.page_font_var.set(labels.get(code, labels["helv"]))

    def _current_page_number_font_code(self):
        selected = self.page_font_var.get()
        labels = self._page_number_font_labels()
        for code, label in labels.items():
            if selected == label:
                return code
        legacy_labels = {
            "helv": "helv",
            "cour": "cour",
            "tiro": "tiro",
            "ゴシック体": "helv",
            "等幅文字": "cour",
            "明朝体": "tiro",
            "Sans serif": "helv",
            "Monospace": "cour",
            "Serif": "tiro",
        }
        return legacy_labels.get(selected, "helv")

    PAGE_NUMBER_COLOR_CODES = ("red", "blue", "black")

    def _page_number_color_labels(self):
        return PAGE_NUMBER_COLOR_LABELS.get(self.language, PAGE_NUMBER_COLOR_LABELS["en"])

    def _page_number_color_display_values(self):
        labels = self._page_number_color_labels()
        return [labels[code] for code in self.PAGE_NUMBER_COLOR_CODES]

    def _set_page_number_color_code(self, code):
        labels = self._page_number_color_labels()
        self.page_color_var.set(labels.get(code, labels["red"]))

    def _current_page_number_color_code(self):
        selected = self.page_color_var.get()
        labels = self._page_number_color_labels()
        for code, label in labels.items():
            if selected == label:
                return code
        legacy_labels = {
            "Red": "red",
            "Blue": "blue",
            "Black": "black",
            "赤": "red",
            "青": "blue",
            "黒": "black",
        }
        return legacy_labels.get(selected, "red")

    BOOKMARK_VIEW_MODE_CODES = ("fit_page", "fit_width", "fit_height", "adjust")

    def _bookmark_view_mode_labels(self):
        return BOOKMARK_VIEW_MODE_LABELS.get(self.language, BOOKMARK_VIEW_MODE_LABELS["en"])

    def _bookmark_view_mode_display_values(self):
        labels = self._bookmark_view_mode_labels()
        return [labels[code] for code in self.BOOKMARK_VIEW_MODE_CODES]

    def _set_bookmark_view_mode_code(self, code):
        labels = self._bookmark_view_mode_labels()
        self.bookmark_view_mode_var.set(labels.get(code, labels["fit_page"]))

    def _current_bookmark_view_mode_code(self):
        selected = self.bookmark_view_mode_var.get()
        labels = self._bookmark_view_mode_labels()
        for code, label in labels.items():
            if selected == label:
                return code
        legacy_labels = {
            "補正値で調整": "adjust",
            "幅に合わせる": "fit_width",
            "高さに合わせる": "fit_height",
            "ページ全体": "fit_page",
            "Adjusted position": "adjust",
            "Fit width": "fit_width",
            "Fit height": "fit_height",
            "Fit page": "fit_page",
        }
        return legacy_labels.get(selected, "adjust")

    def _preset_labels(self):
        if self.language == "ja":
            return {
                "none": "設定なし",
                "paperless": "ペーパーレス会議設定",
                "mail": "メールデータ整理設定",
                "asp": "工事情報共有システム設定",
                "custom1": "カスタム1",
                "custom2": "カスタム2",
            }
        return {
            "none": "No preset",
            "paperless": "Paperless meeting",
            "mail": "Mail data cleanup",
            "asp": "Construction ASP",
            "custom1": "Custom 1",
            "custom2": "Custom 2",
        }

    def _preset_display_values(self):
        labels = self._preset_labels()
        return [labels[code] for code in PRESET_CODES]

    def _set_preset_code(self, code):
        labels = self._preset_labels()
        self.preset_var.set(labels.get(code, labels["paperless"]))

    def _current_preset_code(self):
        selected = self.preset_var.get()
        labels = self._preset_labels()
        for code, label in labels.items():
            if selected == label:
                return code
        legacy_labels = {
            "設定なし": "none",
            "ペーパーレス会議設定": "paperless",
            "メールデータ整理設定": "mail",
            "工事情報共有システム設定": "asp",
            "カスタム1": "custom1",
            "カスタム2": "custom2",
            "No preset": "none",
            "Paperless meeting": "paperless",
            "Mail data cleanup": "mail",
            "Construction ASP": "asp",
            "Custom 1": "custom1",
            "Custom 2": "custom2",
        }
        return legacy_labels.get(selected, "paperless")

    def _load_custom_presets(self):
        path = settings_file_path()
        try:
            with open(path, "r", encoding="utf-8-sig") as settings_file:
                data = json.load(settings_file)
        except (OSError, json.JSONDecodeError):
            return {}

        presets = data.get("custom_presets", {})
        if not isinstance(presets, dict):
            return {}
        return {
            code: presets[code]
            for code in PRESET_CODES
            if isinstance(presets.get(code), dict)
        }

    def _save_custom_presets(self):
        path = settings_file_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "version": 1,
            "custom_presets": {
                code: self.custom_presets[code]
                for code in PRESET_CODES
                if code in self.custom_presets
            },
        }
        with open(path, "w", encoding="utf-8") as settings_file:
            json.dump(data, settings_file, ensure_ascii=False, indent=2)

    def _preset_settings(self, code):
        if code in self.custom_presets:
            return dict(self.custom_presets[code])
        if code in BUILT_IN_PRESETS:
            return dict(BUILT_IN_PRESETS[code])
        return None

    SAVE_MODE_CODES = ("speed", "balanced", "smaller_file")

    def _save_mode_labels(self):
        if self.language == "ja":
            return {
                "speed": "速度重視",
                "balanced": "バランス",
                "smaller_file": "圧縮重視",
            }
        return {
            "speed": "Speed",
            "balanced": "Balanced",
            "smaller_file": "Smaller File",
        }

    def _save_mode_display_values(self):
        labels = self._save_mode_labels()
        return [labels[code] for code in self.SAVE_MODE_CODES]

    def _set_save_mode_code(self, code):
        labels = self._save_mode_labels()
        self.save_mode_var.set(labels.get(code, labels["balanced"]))

    def _current_save_mode_code(self):
        selected = self.save_mode_var.get()
        labels = self._save_mode_labels()
        for code, label in labels.items():
            if selected == label:
                return code
        legacy_labels = {
            "Fast": "speed",
            "高速": "speed",
            "Speed": "speed",
            "速度重視": "speed",
            "Balanced": "balanced",
            "バランス": "balanced",
            "Smaller File": "smaller_file",
            "圧縮重視": "smaller_file",
        }
        return legacy_labels.get(selected, "balanced")

    def _on_save_mode_selected(self, _event=None):
        self._set_save_mode_code(self._current_save_mode_code())

    def _text(self, key):
        translations = {
            "en": {
                "window_title": "kojiPDF - Built with Python by Code4Construct",
                "title": "kojiPDF v2.2.0",
                "subtitle": "Select a folder and output PDF file, then create a structured inspection PDF.",
                "notice": (
                    "- Merge PDFs and create bookmarks from file and folder names\n"
                    "- Convert Office files, add page numbers with adjustable opacity, and resize pages\n"
                    "Uses: inspection records and paperless meeting materials.\n"
                    "Note: This app uses Python modules licensed under AGPL-3.0.\n"
                    "Commercial use is allowed. If modified, redistributed, or provided over a network, "
                    "the source code must be published under AGPL-3.0.\n"
                    "If this obligation is not met, permission to use the app cannot be granted."
                ),
                "select_folder": "Select folder",
                "output": "Output PDF",
                "create": "Create PDF",
                "create_short": "Run",
                "not_selected": "Not selected",
                "general_options": "Merge options",
                "page_number_options": "Print page numbers at bottom right",
                "scale_options": "Bookmark view adjust",
                "bookmark_options": "Bookmark display",
                "asp_options": "Construction info-sharing (ASP)",
                "progress_title": "Progress",
                "progress_started": "Starting PDF creation...\n",
                "progress_heartbeat": "Working... elapsed {elapsed}. Large final saves can take several minutes.",
                "progress_done": "Done.",
                "progress_failed": "Stopped because an error occurred.",
                "retry_hint": "Close the file or fix the issue, then press Run again.",
                "progress_step_check": "Check",
                "progress_step_tree": "Analyze",
                "progress_step_merge": "Merge",
                "progress_step_pages": "Pages",
                "progress_step_bookmarks": "Bookmarks",
                "progress_step_save": "Save",
                "completion_title": "Done",
                "completion_exit_message": "PDF creation is complete.\nExit the program?",
                "error_title": "Error",
                "add_bookmark_page_number": "Add page number",
                "add_page": "Add page count",
                "keep_pdf_extension": "Keep .pdf",
                "convert_office": "Convert Office, image, text/code files to PDF before merging",
                "convert_mail": "Convert .msg/.eml email and zip files to PDF",
                "eml_encoding": "eml encoding",
                "confirm_temp_folder_delete": "Confirm temp folder delete",
                "ppt_slide_bookmarks": "Add PowerPoint slide bookmarks",
                "resize_pdf": "Resize all PDFs to selected page size",
                "save_mode": "Save Mode",
                "error_check": "Error check",
                "preflight_detail_repair": "Detailed check",
                "preflight_confirm": "Step confirm",
                "asper_format": "Apply Dennoh ASPer bookmark name rules",
                "add_pdf_page_numbers": "Add page numbers to merged PDF pages",
                "page_start_number": "Start number",
                "page_font_size": "Font size",
                "page_margin_right": "Right margin",
                "page_margin_bottom": "Bottom margin",
                "page_font": "Font",
                "page_color": "Color",
                "page_opacity": "Opacity",
                "preset": "Preset",
                "save_preset": "Save",
                "reset_preset": "↺",
                "preset_saved_title": "Preset saved",
                "preset_saved_message": "Current settings were saved to {preset}.",
                "preset_overwrite_title": "Overwrite preset?",
                "preset_overwrite_message": "Overwrite {preset} with the current settings?",
                "preset_empty_title": "No custom preset",
                "preset_empty_message": "{preset} has not been saved yet.",
                "preset_none_title": "Select a preset",
                "preset_none_message": "Select a preset before saving settings.",
                "preset_reset_title": "Reset saved presets?",
                "preset_reset_message": "Delete saved preset settings and restore built-in defaults?",
                "preset_reset_done_title": "Presets reset",
                "preset_reset_done_message": "Saved preset settings were deleted.",
                "preset_reset_missing_message": "There were no saved preset settings.",
                "preset_error_title": "Preset error",
                "preset_error_message": "Could not save preset settings.\n{error}",
                "relative_scale": "Relative",
                "absolute_scale": "Absolute",
                "bookmark_view_mode": "View mode",
                "horizontal_scale": "Width corr.",
                "vertical_scale": "Height corr.",
                "base_view_width": "Width",
                "base_view_height": "Height",
                "expand_all": "Expand all",
                "bookmark_level": "Open level",
                "folder_dialog": "Select folder",
                "file_dialog": "Select output PDF",
                "default_output": "one_pdf_with_bookmarks.pdf",
                "pdf_filetype": "PDF files",
                "temp_pdf_notice_title": "Temporary PDF",
                "temp_pdf_notice_message": "The following temporary PDF file will be created while creating the merged file.\n{pdf_path}",
                "temp_pdf_and_folder_notice_message": "The following temporary file and folder will be created while creating the merged file.\n{pdf_path}\n{folder_path}",
                "temp_folder_notice_message": "\nTemporary folder: {path}",
                "temp_folder_notice_title": "Office Conversion",
                "temp_folder_path_message": "Please close Word, Excel, and PowerPoint during conversion. These apps may shut down or conversion errors may occur.{folder_path}",
                "temp_folder_path_line": "The following temporary folder will be created during conversion.\n{path}",
            },
            "ja": {
                "window_title": "kojiPDF - Built with Python by Code4Construct",
                "title": "kojiPDF v2.2.0",
                "subtitle": "フォルダとPDF保存先を選択し、工事検査用PDFファイルを作成します。",
                "notice": (
                    "・選択フォルダ内のPDFを結合し、ファイル名をしおり、フォルダ名を親しおりとして追加した構造化PDFを作成\n"
                    "・Microsoft OfficeファイルのPDF自動変換、不透明度を設定できるページ番号付与、ページサイズ変更などに対応\n"
                    "用途：工事検査資料の整理、情報共有システムの電子データ確認、"
                    "ペーパーレス会議資料の作成\n"
                    "注意：本アプリは、使用しているPythonモジュールによりAGPL-3.0 Licenseが適用されます。\n"
                    "商用利用は可能ですが、改変・再配布・ネットワーク経由で提供する場合はソースコード公開が必要です。\n"
                    "この義務を遵守しない場合、AGPL-3.0に基づく利用許諾を受けられません。"
                ),
                "select_folder": "フォルダ選択",
                "output": "出力PDF",
                "create": "PDFを作成",
                "create_short": "作成",
                "not_selected": "未選択",
                "general_options": "結合設定",
                "page_number_options": "右下にページ番号を印字",
                "scale_options": "しおり表示位置補正",
                "bookmark_options": "しおり表示",
                "asp_options": "工事情報共有システム（ASP）",
                "progress_title": "作成状況",
                "progress_started": "PDF作成を開始します...\n",
                "progress_heartbeat": "処理中です... 経過 {elapsed}。大きいPDFの最終保存は数分かかることがあります。",
                "progress_done": "完了しました。",
                "progress_failed": "エラーにより停止しました。",
                "retry_hint": "ファイルを閉じるなど原因を解消してから、もう一度作成ボタンを押してください。",
                "progress_step_check": "確認",
                "progress_step_tree": "解析",
                "progress_step_merge": "結合",
                "progress_step_pages": "ページ加工",
                "progress_step_bookmarks": "しおり",
                "progress_step_save": "保存",
                "completion_title": "完了",
                "completion_exit_message": "PDFの作成が完了しました。\nプログラムを終了しますか。",
                "error_title": "エラー",
                "add_bookmark_page_number": "しおり名にページを追加",
                "add_page": "しおり名に含まれるページ数を追加",
                "keep_pdf_extension": "しおり名に.pdfを残す",
                "convert_office": "Word・Excel・PowerPoint・画像・テキスト/コードをPDFに変換してから結合",
                "convert_mail": "msg・emlメール及びzipファイルをPDF化する",
                "eml_encoding": "eml文字コード",
                "confirm_temp_folder_delete": "暫定フォルダ削除確認",
                "ppt_slide_bookmarks": "PowerPointのスライドしおりを付ける",
                "resize_pdf": "すべてのPDFを指定サイズに変更",
                "save_mode": "保存方式",
                "error_check": "エラーチェック",
                "preflight_detail_repair": "詳細チェック",
                "preflight_confirm": "逐次確認",
                "asper_format": "電脳ASPer用のしおり名に整える",
                "add_pdf_page_numbers": "結合PDFの各ページにページ番号を追加",
                "page_start_number": "開始番号",
                "page_font_size": "文字サイズ",
                "page_margin_right": "右余白",
                "page_margin_bottom": "下余白",
                "page_font": "フォント",
                "page_color": "色",
                "page_opacity": "不透明度",
                "preset": "設定プリセット",
                "save_preset": "保存",
                "reset_preset": "↺",
                "preset_saved_title": "プリセット保存",
                "preset_saved_message": "現在の設定を {preset} に保存しました。",
                "preset_overwrite_title": "プリセットを上書きしますか？",
                "preset_overwrite_message": "{preset} を現在の設定で上書きしますか？",
                "preset_empty_title": "未保存のカスタム設定",
                "preset_empty_message": "{preset} はまだ保存されていません。",
                "preset_none_title": "プリセットを選択してください",
                "preset_none_message": "設定を保存する前にプリセットを選択してください。",
                "preset_reset_title": "保存済みプリセットをリセットしますか？",
                "preset_reset_message": "保存済みプリセット設定を削除し、内蔵の標準値に戻しますか？",
                "preset_reset_done_title": "プリセットをリセットしました",
                "preset_reset_done_message": "保存済みプリセット設定を削除しました。",
                "preset_reset_missing_message": "保存済みプリセット設定はありませんでした。",
                "preset_error_title": "プリセットエラー",
                "preset_error_message": "プリセット設定を保存できませんでした。\n{error}",
                "relative_scale": "相対補正",
                "absolute_scale": "絶対補正",
                "bookmark_view_mode": "表示モード",
                "horizontal_scale": "表示幅補正",
                "vertical_scale": "表示高さ補正",
                "base_view_width": "幅",
                "base_view_height": "高さ",
                "expand_all": "すべてのしおりを展開",
                "bookmark_level": "しおり展開階層",
                "folder_dialog": "フォルダを選択してください",
                "file_dialog": "出力PDFを指定してください",
                "default_output": "one_pdf_with_bookmarks.pdf",
                "pdf_filetype": "PDFファイル",
                "temp_pdf_notice_title": "一時PDF",
                "temp_pdf_notice_message": "結合ファイルの作成中に次の一時的なPDFファイルが作成されます。\n{pdf_path}",
                "temp_pdf_and_folder_notice_message": "結合ファイルの作成中に次の一時的なファイルとフォルダが作成されます。\n{pdf_path}\n{folder_path}",
                "temp_folder_notice_message": "\n暫定フォルダ: {path}",
                "temp_folder_notice_title": "Office変換の警告",
                "temp_folder_path_message": "変換中はWord･Excel･PowerPointを閉じてください。それらのアプリのシャットダウンや変換エラーをおこします。{folder_path}",
                "temp_folder_path_line": "変換中は次の暫定フォルダが作られます。\n{path}",
            },
        }
        return translations[self.language][key]

    def _notice_parts(self):
        notice = self._text("notice")
        marker = "\nNote:" if self.language == "en" else "\n注意："
        if marker not in notice:
            return notice, ""

        summary, license_notice = notice.split(marker, 1)
        return summary.strip(), marker.strip() + license_notice

    def _sync_notice_wraplength(self, event=None):
        if event is None:
            available_width = self.notice_label.winfo_width()
            if available_width <= 1:
                self._sync_dynamic_wraplengths()
                return
        else:
            available_width = event.width - self._px(328)

        wraplength = max(self._px(300), available_width)
        self.notice_label.configure(wraplength=wraplength)

    def _sync_dynamic_wraplengths(self, content_width=None):
        if content_width is None:
            content_width = self.root_frame.winfo_width()
            if content_width <= 1:
                content_width = min(self._px(CONTENT_MAX_WIDTH), self._px(WINDOW_WIDTH))

        root_horizontal_padding = self._px(28)
        notice_panel_padding_and_icon = self._px(94)
        notice_panel_preset_width = self._px(250)
        license_panel_padding = self._px(180)
        path_controls_width = self._px(250)

        inner_width = max(self._px(300), content_width - root_horizontal_padding)
        self.subtitle_label.configure(wraplength=max(self._px(300), inner_width - self._px(16)))
        self.notice_label.configure(wraplength=max(self._px(300), inner_width - notice_panel_padding_and_icon - notice_panel_preset_width))
        self.license_notice_label.configure(wraplength=max(self._px(300), inner_width - license_panel_padding))
        self.folder_label.configure(wraplength=max(self._px(300), inner_width - path_controls_width))
        self.file_label.configure(wraplength=max(self._px(300), inner_width - path_controls_width))

    def _apply_language(self):
        self.window.title(self._text("window_title"))
        self.title_label.configure(text=self._text("title"), bg=PANEL_BG, fg=TEXT_COLOR)
        self.subtitle_label.configure(text=self._text("subtitle"))
        notice_text, license_notice_text = self._notice_parts()
        notice_font_size = 9
        license_font_size = 8
        self.notice_label.configure(font=("Yu Gothic UI", notice_font_size, "bold"))
        self.license_notice_label.configure(font=("Yu Gothic UI", license_font_size))
        self.notice_label.configure(text=notice_text)
        self.license_notice_label.configure(text=license_notice_text)
        self.window.after_idle(self._sync_notice_wraplength)
        self.folder_button.configure(text=self._text("select_folder"))
        self.file_button.configure(text=self._text("output"))
        if self._widget_exists("preset_combo"):
            current_preset = self._current_preset_code()
            self.preset_label.configure(text=self._text("preset"))
            self.preset_combo.configure(values=self._preset_display_values())
            self._set_preset_code(current_preset)
            self.save_preset_button.configure(text=self._text("save_preset"))
            self.reset_preset_button.configure(text=self._text("reset_preset"))

        if not self._widget_exists("general_section_label"):
            if hasattr(self, "folder_text"):
                self.folder_text.set(self.selected_folder or self._text("not_selected"))
            if hasattr(self, "file_text"):
                self.file_text.set(self.selected_file or self._text("not_selected"))
            if self._widget_exists("japanese_button"):
                self.japanese_button.set_checked(self.language == "ja")
            if self._widget_exists("english_button"):
                self.english_button.set_checked(self.language == "en")
            self._refresh_progress_language()
            self._draw_run_button()
            return

        self.general_section_label.configure(text=self._text("general_options"))
        self.page_number_section_label.configure(text=self._text("page_number_options"))
        self.scale_section_label.configure(text=self._text("scale_options"))
        self.bookmark_section_label.configure(text=self._text("bookmark_options"))
        self.asp_section_label.configure(text=self._text("asp_options"))
        self.add_bookmark_page_number_checkbox.configure(text=self._text("add_bookmark_page_number"))
        self.add_page_checkbox.configure(text=self._text("add_page"))
        self.keep_pdf_extension_checkbox.configure(text=self._text("keep_pdf_extension"))
        self.convert_office_checkbox.configure(text=self._text("convert_office"))
        self.convert_mail_checkbox.configure(text=self._text("convert_mail"))
        current_eml_encoding = self._current_eml_encoding_code()
        self.eml_encoding_label.configure(text=self._text("eml_encoding"))
        self.eml_encoding_combo.configure(values=self._eml_encoding_display_values())
        self._set_eml_encoding_code(current_eml_encoding)
        self.confirm_temp_folder_delete_checkbox.configure(text=self._text("confirm_temp_folder_delete"))
        self.ppt_slide_bookmarks_checkbox.configure(text=self._text("ppt_slide_bookmarks"))
        self.resize_pdf_checkbox.configure(text=self._text("resize_pdf"))
        current_save_mode = self._current_save_mode_code()
        self.save_mode_label.configure(text=self._text("save_mode"))
        self.save_mode_combo.configure(values=self._save_mode_display_values())
        self._set_save_mode_code(current_save_mode)
        self.error_check_label.configure(text=self._text("error_check"))
        self.preflight_detail_repair_checkbox.configure(text=self._text("preflight_detail_repair"))
        self.preflight_confirm_checkbox.configure(text=self._text("preflight_confirm"))
        self.asper_format_checkbox.configure(text=self._text("asper_format"))
        self.add_pdf_page_numbers_checkbox.configure(text="")
        self.page_start_number_label.configure(text=self._text("page_start_number"))
        self.page_font_size_label.configure(text=self._text("page_font_size"))
        self.page_margin_right_label.configure(text=self._text("page_margin_right"))
        self.page_margin_bottom_label.configure(text=self._text("page_margin_bottom"))
        current_page_font = self._current_page_number_font_code()
        self.page_font_label.configure(text=self._text("page_font"))
        self.page_font_combo.configure(values=self._page_number_font_display_values())
        self._set_page_number_font_code(current_page_font)
        current_page_color = self._current_page_number_color_code()
        self.page_color_label.configure(text=self._text("page_color"))
        self.page_color_combo.configure(values=self._page_number_color_display_values())
        self._set_page_number_color_code(current_page_color)
        self.page_opacity_label.configure(text=self._text("page_opacity"))
        current_view_mode = self._current_bookmark_view_mode_code()
        self.bookmark_view_mode_label.configure(text=self._text("bookmark_view_mode"))
        self.bookmark_view_mode_combo.configure(values=self._bookmark_view_mode_display_values())
        self._set_bookmark_view_mode_code(current_view_mode)
        self.relative_scale_radio.configure(text=self._text("relative_scale"))
        self.absolute_scale_radio.configure(text=self._text("absolute_scale"))
        self.horizontal_scale_label.configure(text=self._text("horizontal_scale"))
        self.vertical_scale_label.configure(text=self._text("vertical_scale"))
        self.base_view_width_label.configure(text=self._text("base_view_width"))
        self.base_view_height_label.configure(text=self._text("base_view_height"))
        self.expand_all_checkbox.configure(text=self._text("expand_all"))
        self.bookmark_open_level_label.configure(text=self._text("bookmark_level"))
        self.folder_text.set(self.selected_folder or self._text("not_selected"))
        self.file_text.set(self.selected_file or self._text("not_selected"))
        self.japanese_button.set_checked(self.language == "ja")
        self.english_button.set_checked(self.language == "en")
        self._draw_run_button()

    def _refresh_progress_language(self):
        if self._widget_exists("progress_title_label"):
            self.progress_title_label.configure(text=self._text("progress_title"))
        if self._widget_exists("progress_elapsed_label") and hasattr(self, "progress_elapsed_text"):
            self.progress_elapsed_text.set(self._progress_heartbeat_text())

        if not hasattr(self, "progress_steps") or not hasattr(self, "progress_step_labels"):
            return

        current_index = getattr(self, "progress_step_index", 0)
        self.progress_steps = self._progress_steps()
        self.progress_step_index = min(current_index, len(self.progress_step_labels) - 1)
        for index, label in enumerate(self.progress_step_labels):
            if label.winfo_exists():
                label.configure(text=f"{index + 1}. {self.progress_steps[index]['label']}")
        self._set_progress_step(self.progress_step_index)

    def show(self):
        self._fit_window_to_screen()
        self._center_window()
        self.window.after(0, self._bring_to_front)
        debug_log("Window shown")
        self.window.mainloop()

    def _fit_window_to_screen(self):
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        available_width = max(self._px(MIN_WINDOW_WIDTH), screen_width - self._px(SCREEN_MARGIN_WIDTH))
        available_height = max(self._px(MIN_WINDOW_HEIGHT), screen_height - self._px(SCREEN_MARGIN_HEIGHT))
        width = min(self._px(WINDOW_WIDTH), available_width)
        content_width = min(self._px(CONTENT_MAX_WIDTH), width)
        self.root_frame.place_configure(width=content_width)
        self.window.geometry(f"{width}x{self._px(WINDOW_HEIGHT)}")
        self.window.update_idletasks()
        self._sync_dynamic_wraplengths(content_width)
        self.window.update_idletasks()
        requested_height = self.root_frame.winfo_reqheight() + self._px(WINDOW_HEIGHT_PADDING)
        max_height = min(self._px(WINDOW_HEIGHT), available_height)
        height = min(max(self._px(MIN_WINDOW_HEIGHT), requested_height), max_height)
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(min(self._px(MIN_WINDOW_WIDTH), width), min(self._px(MIN_WINDOW_HEIGHT), height))
        self.window.update_idletasks()

    def _center_window(self):
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = max(0, (self.window.winfo_screenwidth() - width) // 2)
        y = max(0, (self.window.winfo_screenheight() - height) // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _bring_to_front(self):
        self.window.lift()
        self.window.focus_force()
        self.window.attributes("-topmost", True)
        self.window.after(200, lambda: self.window.attributes("-topmost", False))

    def dispose(self):
        try:
            self.window.destroy()
        except tk.TclError:
            pass

    def cancel(self):
        self.selected_folder = None
        self.selected_file = None
        self.accepted = False
        self.window.destroy()

    def finish(self):
        self.accepted = True
        self.retry_requested = False
        self.show_progress()
        self.window.quit()

    def retry(self):
        self.retry_requested = True
        self.show_progress()
        self.window.quit()

    def show_progress(self):
        for child in self.options_group.winfo_children():
            child.destroy()

        self.folder_button.configure(state="disabled")
        self.file_button.configure(state="disabled")
        self.run_button.configure(cursor="")
        self.run_button.unbind("<Button-1>")
        self.run_button.unbind("<Enter>")
        self.run_button.unbind("<Leave>")

        self.options_group.configure(cursor="watch")
        self.progress_panel = tb.Frame(self.options_group, style="Band.TFrame", padding=self._px(12))
        self.progress_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.options_group.rowconfigure(0, weight=1)
        self.options_group.columnconfigure(0, weight=1)
        self.options_group.columnconfigure(1, weight=1)
        self.progress_panel.rowconfigure(5, weight=1)
        self.progress_panel.columnconfigure(0, weight=1)
        self._progress_started_at = time.monotonic()
        self._progress_last_message_at = self._progress_started_at

        self.progress_title_label = tb.Label(self.progress_panel, style="Section.TLabel")
        self.progress_title_label.grid(row=0, column=0, sticky="w", pady=self._pad(0, 8))
        self.progress_title_label.configure(text=self._text("progress_title"))

        self.progress_bar = tb.Progressbar(self.progress_panel, mode="indeterminate", bootstyle="danger-striped")
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=self._pad(0, 10))
        self.progress_bar.start(12)

        self.progress_current_text = tk.StringVar(value=self._text("progress_started").strip())
        self.progress_current_label = tk.Label(
            self.progress_panel,
            textvariable=self.progress_current_text,
            bg=SUBTLE_BG,
            fg=SECTION_TEXT_COLOR,
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
            padx=self._px(8),
            pady=self._px(5),
        )
        self.progress_current_label.grid(row=2, column=0, sticky="ew", pady=self._pad(0, 10))

        self.progress_elapsed_text = tk.StringVar(value=self._progress_heartbeat_text())
        self.progress_elapsed_label = tk.Label(
            self.progress_panel,
            textvariable=self.progress_elapsed_text,
            bg=BAND_BG,
            fg=MUTED_TEXT_COLOR,
            anchor="w",
            font=("Yu Gothic UI", 9),
        )
        self.progress_elapsed_label.grid(row=3, column=0, sticky="ew", pady=self._pad(0, 8))

        self.progress_step_frame = tk.Frame(self.progress_panel, bg=BAND_BG)
        self.progress_step_frame.grid(row=4, column=0, sticky="ew", pady=self._pad(0, 10))
        self.progress_steps = self._progress_steps()
        self.progress_step_labels = []
        for index, step in enumerate(self.progress_steps):
            self.progress_step_frame.columnconfigure(index, weight=1)
            label = tk.Label(
                self.progress_step_frame,
                text=f"{index + 1}. {step['label']}",
                bg="#dbe5ef",
                fg=MUTED_TEXT_COLOR,
                anchor="center",
                font=("Yu Gothic UI", 9),
                padx=self._px(5),
                pady=self._px(5),
            )
            label.grid(row=0, column=index, sticky="ew", padx=self._pad(0, 4 if index < len(self.progress_steps) - 1 else 0))
            self.progress_step_labels.append(label)
        self.progress_step_index = -1
        self._set_progress_step(0)

        self.progress_text = scrolledtext.ScrolledText(
            self.progress_panel,
            height=10,
            wrap="word",
            bg=PANEL_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief="flat",
            borderwidth=0,
            font=("Yu Gothic UI", 10),
        )
        self.progress_text.grid(row=5, column=0, sticky="nsew", pady=self._pad(0, 6))
        self.progress_text.configure(state="disabled")
        self.append_progress(self._text("progress_started"))
        self._start_progress_queue_poll()
        self._start_progress_heartbeat()
        self.window.update_idletasks()
        self._fit_window_to_screen()

    def _progress_steps(self):
        return [
            {"label": self._text("progress_step_check"), "patterns": ("問題のあるPDF", "すべてのPDFファイル")},
            {"label": self._text("progress_step_tree"), "patterns": ("フォルダー構造", "しおり順")},
            {"label": self._text("progress_step_merge"), "patterns": ("PDFファイルを結合",)},
            {"label": self._text("progress_step_pages"), "patterns": ("PDFページ", "ページ番号を追加")},
            {"label": self._text("progress_step_bookmarks"), "patterns": ("親しおり", "子しおり", "しおり名", "クリック位置")},
            {"label": self._text("progress_step_save"), "patterns": ("一時PDF", "最終PDF", "PDF作成が完了")},
        ]

    def _set_progress_step(self, index):
        if not hasattr(self, "progress_step_labels"):
            return
        index = max(0, min(index, len(self.progress_step_labels) - 1))
        self.progress_step_index = max(self.progress_step_index, index)
        for i, label in enumerate(self.progress_step_labels):
            if i < self.progress_step_index:
                label.configure(text=f"✓ {self.progress_steps[i]['label']}", bg="#dcefe3", fg="#1e5f36")
            elif i == self.progress_step_index:
                label.configure(text=f"▶ {self.progress_steps[i]['label']}", bg="#fff3cd", fg="#6b4b00")
            else:
                label.configure(text=f"{i + 1}. {self.progress_steps[i]['label']}", bg="#dbe5ef", fg=MUTED_TEXT_COLOR)

    def _update_progress_from_message(self, message):
        if not message or not hasattr(self, "progress_steps"):
            return
        clean_message = message.strip()
        if clean_message and hasattr(self, "progress_current_text"):
            self.progress_current_text.set(clean_message.splitlines()[-1])
        for index, step in enumerate(self.progress_steps):
            if any(pattern in clean_message for pattern in step["patterns"]):
                self._set_progress_step(index)
                break

    def append_progress(self, message):
        if not message or not hasattr(self, "progress_text"):
            return
        try:
            self._progress_last_message_at = time.monotonic()
            self._update_progress_from_message(message)
            self.progress_text.configure(state="normal")
            self.progress_text.insert("end", message)
            self.progress_text.see("end")
            self.progress_text.configure(state="disabled")
            self.window.update_idletasks()
            self.window.update()
        except tk.TclError:
            pass

    def _format_elapsed_time(self, seconds):
        seconds = max(0, int(seconds))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _progress_heartbeat_text(self):
        started_at = self._progress_started_at or time.monotonic()
        elapsed = self._format_elapsed_time(time.monotonic() - started_at)
        return self._text("progress_heartbeat").format(elapsed=elapsed)

    def _start_progress_heartbeat(self):
        if self._progress_heartbeat_after_id is None:
            self._update_progress_heartbeat()

    def _update_progress_heartbeat(self):
        self._progress_heartbeat_after_id = None
        if not hasattr(self, "progress_elapsed_text"):
            return
        try:
            self.progress_elapsed_text.set(self._progress_heartbeat_text())
            self._progress_heartbeat_after_id = self.window.after(1000, self._update_progress_heartbeat)
        except tk.TclError:
            pass

    def _stop_progress_heartbeat(self):
        if self._progress_heartbeat_after_id is None:
            return
        try:
            self.window.after_cancel(self._progress_heartbeat_after_id)
        except tk.TclError:
            pass
        self._progress_heartbeat_after_id = None

    def queue_progress(self, message):
        if message:
            self._progress_queue.put(message)

    def _start_progress_queue_poll(self):
        if self._progress_poll_after_id is None:
            self._poll_progress_queue()

    def _poll_progress_queue(self):
        self._progress_poll_after_id = None
        try:
            while True:
                self.append_progress(self._progress_queue.get_nowait())
        except queue.Empty:
            pass
        except tk.TclError:
            return

        if hasattr(self, "progress_text"):
            try:
                self._progress_poll_after_id = self.window.after(80, self._poll_progress_queue)
            except tk.TclError:
                pass

    def finish_progress(self, success=True):
        if not hasattr(self, "progress_text"):
            return
        try:
            self._stop_progress_heartbeat()
            self.progress_bar.stop()
            self.options_group.configure(cursor="")
            if success:
                self._set_progress_step(len(self.progress_step_labels) - 1)
            self.append_progress("\n" + (self._text("progress_done") if success else self._text("progress_failed")) + "\n")
            if not success:
                self.append_progress(self._text("retry_hint") + "\n")
                self.run_button.configure(cursor="hand2")
                self.run_button.bind("<Button-1>", lambda _event: self.retry())
                self.run_button.bind("<Enter>", lambda _event: self._draw_run_button(hover=True))
                self.run_button.bind("<Leave>", lambda _event: self._draw_run_button(hover=False))
        except tk.TclError:
            pass

    def confirm_exit_after_completion(self):
        try:
            should_exit = messagebox.askokcancel(
                self._text("completion_title"),
                self._text("completion_exit_message"),
                parent=self.window,
            )
            if should_exit:
                self.window.destroy()
            return should_exit
        except tk.TclError:
            return False

    def show_error_message(self, message):
        try:
            messagebox.showerror(self._text("error_title"), message, parent=self.window)
        except tk.TclError:
            pass

    def show_temp_pdf_notice(self, output_file_path, show_temp_folder=False):
        try:
            existing_notice = getattr(self, "_temp_pdf_notice", None)
            if existing_notice is not None and existing_notice.winfo_exists():
                existing_notice.destroy()

            temp_pdf_path = output_file_path[:-4] + "temp.PDF"
            notice_message_key = "temp_pdf_notice_message"
            notice_values = {"pdf_path": temp_pdf_path}
            if show_temp_folder:
                temp_folder_path = os.path.join(os.path.dirname(output_file_path), "temp_folder")
                notice_message_key = "temp_pdf_and_folder_notice_message"
                notice_values["folder_path"] = temp_folder_path

            notice = tk.Toplevel(self.window)
            self._temp_pdf_notice = notice
            notice.title(self._text("temp_pdf_notice_title"))
            notice.transient(self.window)
            notice.resizable(False, False)
            notice.configure(bg=PANEL_BG)
            notice.attributes("-topmost", True)

            frame = tb.Frame(notice, padding=self._pad(20, 16), bootstyle="light")
            frame.grid(row=0, column=0, sticky="nsew")
            label = tb.Label(
                frame,
                text=self._text(notice_message_key).format(**notice_values),
                style="Field.TLabel",
                justify="left",
                wraplength=self._px(520),
            )
            label.grid(row=0, column=0, sticky="w")

            notice.update_idletasks()
            width = notice.winfo_width()
            height = notice.winfo_height()
            parent_x = self.window.winfo_rootx()
            parent_y = self.window.winfo_rooty()
            parent_width = self.window.winfo_width()
            parent_height = self.window.winfo_height()
            x = parent_x + max(0, (parent_width - width) // 2)
            y = parent_y + max(0, (parent_height - height) // 2)
            notice.geometry(f"+{x}+{y}")

            notice.after(5000, lambda: notice.destroy() if notice.winfo_exists() else None)
            notice.after(200, lambda: notice.attributes("-topmost", False) if notice.winfo_exists() else None)
        except tk.TclError:
            pass

    def show_temp_folder_notice(self, output_file_path=None):
        try:
            folder_text = ""
            if output_file_path:
                temp_folder_path = os.path.join(os.path.dirname(output_file_path), "temp_folder")
                folder_text = "\n\n" + self._text("temp_folder_path_line").format(path=temp_folder_path)

            existing_notice = getattr(self, "_temp_folder_notice", None)
            if existing_notice is not None and existing_notice.winfo_exists():
                existing_notice.destroy()

            notice = tk.Toplevel(self.window)
            self._temp_folder_notice = notice
            notice.title(self._text("temp_folder_notice_title"))
            notice.transient(self.window)
            notice.resizable(False, False)
            notice.configure(bg=PANEL_BG)
            notice.attributes("-topmost", True)

            frame = tb.Frame(notice, padding=self._pad(20, 16), bootstyle="light")
            frame.grid(row=0, column=0, sticky="nsew")
            label = tb.Label(
                frame,
                text=self._text("temp_folder_path_message").format(folder_path=folder_text),
                style="Field.TLabel",
                justify="left",
                wraplength=self._px(520),
            )
            label.grid(row=0, column=0, sticky="w")

            notice.update_idletasks()
            width = notice.winfo_width()
            height = notice.winfo_height()
            parent_x = self.window.winfo_rootx()
            parent_y = self.window.winfo_rooty()
            parent_width = self.window.winfo_width()
            parent_height = self.window.winfo_height()
            x = parent_x + max(0, (parent_width - width) // 2)
            y = parent_y + max(0, (parent_height - height) // 2)
            notice.geometry(f"+{x}+{y}")

            notice.after(5000, lambda: notice.destroy() if notice.winfo_exists() else None)
            notice.after(200, lambda: notice.attributes("-topmost", False) if notice.winfo_exists() else None)
        except tk.TclError:
            pass

    def toggle_scale_mode(self):
        if self._current_bookmark_view_mode_code() != "adjust":
            return
        relative_widgets = (
            self.horizontal_scale_label,
            self.scale_x_spinbox,
            self.vertical_scale_label,
            self.scale_y_spinbox,
        )
        absolute_widgets = (
            self.base_view_width_label,
            self.base_view_width_spinbox,
            self.base_view_height_label,
            self.base_view_height_spinbox,
        )
        for widget in relative_widgets:
            widget.grid_remove()
        for widget in absolute_widgets:
            widget.grid()

    def toggle_bookmark_view_mode(self):
        adjust_mode = self._current_bookmark_view_mode_code() == "adjust"
        state = "normal" if adjust_mode else "disabled"
        for widget in (
            self.base_view_width_spinbox,
            self.base_view_height_spinbox,
        ):
            widget.configure(state=state)
        if adjust_mode:
            self.toggle_scale_mode()
        else:
            for widget in (
                self.horizontal_scale_label,
                self.scale_x_spinbox,
                self.vertical_scale_label,
                self.scale_y_spinbox,
                self.base_view_width_label,
                self.base_view_width_spinbox,
                self.base_view_height_label,
                self.base_view_height_spinbox,
            ):
                widget.grid_remove()

    def toggle_collapse_spinbox(self):
        state = "disabled" if self.expand_all_var.get() else "normal"
        self.collapse_spinbox.configure(state=state)

    def toggle_page_number_options(self):
        state = "normal" if self.add_pdf_page_numbers_var.get() else "disabled"
        for widget in (
            self.page_start_number_spinbox,
            self.page_font_size_spinbox,
            self.page_margin_right_spinbox,
            self.page_margin_bottom_spinbox,
            self.page_font_combo,
            self.page_color_combo,
            self.page_opacity_spinbox,
        ):
            widget.configure(state=state if not isinstance(widget, tb.Combobox) else ("readonly" if state == "normal" else "disabled"))

    def toggle_office_options(self):
        state = "normal" if self.convert_office_var.get() else "disabled"
        self.convert_mail_checkbox.configure(state=state)
        self.ppt_slide_bookmarks_checkbox.configure(state=state)
        self.confirm_temp_folder_delete_checkbox.configure(state=state)
        if not self.convert_office_var.get():
            self.convert_mail_var.set(False)
            self.confirm_temp_folder_delete_var.set(False)
        if self.convert_office_var.get():
            self.convert_mail_var.set(True)
            self.show_temp_folder_notice(self.selected_file)
        self.toggle_mail_options()

    def toggle_mail_options(self):
        enabled = self.convert_office_var.get() and self.convert_mail_var.get()
        self.eml_encoding_combo.configure(state="readonly" if enabled else "disabled")

    def _refresh_option_states(self):
        office_state = "normal" if self.convert_office_var.get() else "disabled"
        self.convert_mail_checkbox.configure(state=office_state)
        self.ppt_slide_bookmarks_checkbox.configure(state=office_state)
        self.confirm_temp_folder_delete_checkbox.configure(state=office_state)
        self.toggle_mail_options()
        self.toggle_page_number_options()
        self.toggle_bookmark_view_mode()
        self.toggle_collapse_spinbox()

    def current_ui_settings(self):
        return {
            "convert_office": self.convert_office_var.get(),
            "convert_mail": self.convert_mail_var.get(),
            "eml_encoding": self._current_eml_encoding_code(),
            "ppt_slide_bookmarks": self.ppt_slide_bookmarks_var.get(),
            "confirm_temp_folder_delete": self.confirm_temp_folder_delete_var.get(),
            "resize_pdf": self.resize_pdf_var.get(),
            "resize_size": self.resize_size_var.get(),
            "preflight_detail_repair": self.preflight_detail_repair_var.get(),
            "preflight_confirm": self.preflight_confirm_var.get(),
            "save_mode": self._current_save_mode_code(),
            "add_bookmark_page_number": self.add_bookmark_page_number_var.get(),
            "add_page": self.add_page_var.get(),
            "expand_all": self.expand_all_var.get(),
            "collapse_level": self._spinbox_value(self.collapse_spinbox),
            "keep_pdf_extension": self.keep_pdf_extension_var.get(),
            "add_pdf_page_numbers": self.add_pdf_page_numbers_var.get(),
            "page_start_number": self._spinbox_value(self.page_start_number_spinbox),
            "page_font_size": self._spinbox_value(self.page_font_size_spinbox),
            "page_margin_right": self._spinbox_value(self.page_margin_right_spinbox),
            "page_margin_bottom": self._spinbox_value(self.page_margin_bottom_spinbox),
            "page_font": self._current_page_number_font_code(),
            "page_color": self._current_page_number_color_code(),
            "page_opacity": self._spinbox_value(self.page_opacity_spinbox),
            "bookmark_view_mode": self._current_bookmark_view_mode_code(),
            "scale_mode": "absolute",
            "scale_x": 1.0,
            "scale_y": 1.0,
            "base_view_width": self._spinbox_value(self.base_view_width_spinbox),
            "base_view_height": self._spinbox_value(self.base_view_height_spinbox),
            "asper_format": self.asper_format_var.get(),
        }

    def apply_ui_settings(self, settings):
        values = {**DEFAULT_UI_SETTINGS, **(settings or {})}
        self.convert_office_var.set(bool(values["convert_office"]))
        self.convert_mail_var.set(bool(values["convert_mail"]))
        self._set_eml_encoding_code(values["eml_encoding"])
        self.ppt_slide_bookmarks_var.set(bool(values["ppt_slide_bookmarks"]))
        self.confirm_temp_folder_delete_var.set(bool(values["confirm_temp_folder_delete"]))
        self.resize_pdf_var.set(bool(values["resize_pdf"]))
        self.resize_size_var.set(values["resize_size"] if values["resize_size"] in {"A3", "A4", "A5", "B4", "B5"} else "A4")
        self.preflight_detail_repair_var.set(bool(values["preflight_detail_repair"]))
        self.preflight_confirm_var.set(bool(values["preflight_confirm"]))
        self._set_save_mode_code(values["save_mode"])
        self.add_bookmark_page_number_var.set(bool(values["add_bookmark_page_number"]))
        self.add_page_var.set(bool(values["add_page"]))
        self.expand_all_var.set(bool(values["expand_all"]))
        self._set_spinbox_value(self.collapse_spinbox, values["collapse_level"])
        self.keep_pdf_extension_var.set(bool(values["keep_pdf_extension"]))
        self.add_pdf_page_numbers_var.set(bool(values["add_pdf_page_numbers"]))
        self._set_spinbox_value(self.page_start_number_spinbox, values["page_start_number"])
        self._set_spinbox_value(self.page_font_size_spinbox, values["page_font_size"])
        self._set_spinbox_value(self.page_margin_right_spinbox, values["page_margin_right"])
        self._set_spinbox_value(self.page_margin_bottom_spinbox, values["page_margin_bottom"])
        self._set_page_number_font_code(values["page_font"])
        self._set_page_number_color_code(values["page_color"])
        self._set_spinbox_value(self.page_opacity_spinbox, values["page_opacity"])
        self._set_bookmark_view_mode_code(values["bookmark_view_mode"])
        self.scale_mode_var.set("absolute")
        self._set_spinbox_value(self.scale_x_spinbox, 1.0)
        self._set_spinbox_value(self.scale_y_spinbox, 1.0)
        self._set_spinbox_value(self.base_view_width_spinbox, values["base_view_width"])
        self._set_spinbox_value(self.base_view_height_spinbox, values["base_view_height"])
        self.asper_format_var.set(bool(values["asper_format"]))
        self._refresh_option_states()

    def load_selected_preset(self):
        code = self._current_preset_code()
        if code == "none":
            return
        settings = self._preset_settings(code)
        if settings is None:
            messagebox.showinfo(
                self._text("preset_empty_title"),
                self._text("preset_empty_message").format(preset=self.preset_var.get()),
                parent=self.window,
            )
            return
        self.apply_ui_settings(settings)

    def save_selected_preset(self):
        code = self._current_preset_code()
        if code == "none":
            messagebox.showinfo(
                self._text("preset_none_title"),
                self._text("preset_none_message"),
                parent=self.window,
            )
            return
        if code in BUILT_IN_PRESET_CODES:
            should_overwrite = messagebox.askyesno(
                self._text("preset_overwrite_title"),
                self._text("preset_overwrite_message").format(preset=self.preset_var.get()),
                parent=self.window,
            )
            if not should_overwrite:
                return
        self.custom_presets[code] = self.current_ui_settings()
        try:
            self._save_custom_presets()
        except OSError as exc:
            messagebox.showerror(
                self._text("preset_error_title"),
                self._text("preset_error_message").format(error=exc),
                parent=self.window,
            )
            return
        messagebox.showinfo(
            self._text("preset_saved_title"),
            self._text("preset_saved_message").format(preset=self.preset_var.get()),
            parent=self.window,
        )

    def reset_saved_presets(self):
        should_reset = messagebox.askyesno(
            self._text("preset_reset_title"),
            self._text("preset_reset_message"),
            parent=self.window,
        )
        if not should_reset:
            return

        path = settings_file_path()
        deleted = False
        try:
            if os.path.exists(path):
                os.remove(path)
                deleted = True
        except OSError as exc:
            messagebox.showerror(
                self._text("preset_error_title"),
                self._text("preset_error_message").format(error=exc),
                parent=self.window,
            )
            return

        self.custom_presets = {}
        self._set_preset_code("none")
        messagebox.showinfo(
            self._text("preset_reset_done_title"),
            self._text("preset_reset_done_message" if deleted else "preset_reset_missing_message"),
            parent=self.window,
        )

    def select_folder(self):
        folder = filedialog.askdirectory(
            parent=self.window,
            title=self._text("folder_dialog"),
            initialdir=self.default_folder,
        )
        if folder:
            self.selected_folder = folder
            self.folder_text.set(folder)

    def select_save_file(self):
        file_path = filedialog.asksaveasfilename(
            parent=self.window,
            title=self._text("file_dialog"),
            initialdir=self.default_folder,
            initialfile=self._text("default_output"),
            defaultextension=".pdf",
            filetypes=[(self._text("pdf_filetype"), "*.pdf")],
        )
        if file_path:
            self.selected_file = file_path
            self.file_text.set(file_path)
            self.show_temp_pdf_notice(file_path, show_temp_folder=self.convert_office_var.get())

    @property
    def add_bookmark_page_number(self):
        return self.add_bookmark_page_number_var.get()

    @property
    def add_page(self):
        return self.add_page_var.get()

    @property
    def convert_office(self):
        return self.convert_office_var.get()

    @property
    def convert_mail(self):
        return self.convert_mail_var.get()

    @property
    def eml_encoding(self):
        return self._current_eml_encoding_code()

    @property
    def confirm_temp_folder_delete(self):
        return self.confirm_temp_folder_delete_var.get()

    @property
    def ppt_slide_bookmarks(self):
        return self.ppt_slide_bookmarks_var.get()

    @property
    def resize_pdf(self):
        return self.resize_pdf_var.get()

    @property
    def resize_size(self):
        return self.resize_size_var.get()

    @property
    def preflight_detail_repair(self):
        return self.preflight_detail_repair_var.get()

    @property
    def preflight_confirm(self):
        return self.preflight_confirm_var.get()

    @property
    def save_options(self):
        save_mode = self._current_save_mode_code()
        return dict(SAVE_MODE_OPTIONS[save_mode]["save_options"])

    @property
    def asper_format(self):
        return self.asper_format_var.get()

    @property
    def keep_pdf_extension(self):
        return self.keep_pdf_extension_var.get()

    @property
    def add_pdf_page_numbers(self):
        return self.add_pdf_page_numbers_var.get()

    @property
    def page_number_options(self):
        return {
            "start_number": self._spinbox_value(self.page_start_number_spinbox),
            "font_size": self._spinbox_value(self.page_font_size_spinbox),
            "margin_right": self._spinbox_value(self.page_margin_right_spinbox),
            "margin_bottom": self._spinbox_value(self.page_margin_bottom_spinbox),
            "fontname": self._current_page_number_font_code(),
            "fill": PAGE_NUMBER_COLOR_VALUES[self._current_page_number_color_code()],
            "fill_opacity": self._spinbox_value(self.page_opacity_spinbox),
        }

    @property
    def scale_x(self):
        return 1.0

    @property
    def scale_y(self):
        return 1.0

    @property
    def scale_enabled(self):
        return True

    @property
    def bookmark_view_mode(self):
        return self._current_bookmark_view_mode_code()

    @property
    def base_view_width_mm(self):
        return self._spinbox_value(self.base_view_width_spinbox)

    @property
    def base_view_height_mm(self):
        return self._spinbox_value(self.base_view_height_spinbox)

    @property
    def expand_all(self):
        return self.expand_all_var.get()

    @property
    def collapse_level(self):
        return self._spinbox_value(self.collapse_spinbox)


def select_folder_and_file():
    debug_log("select_folder_and_file started")
    selector = FileSelectorApp()
    selector.show()
    debug_log("Tkinter event loop ended")

    result = (
        selector.selected_folder,
        selector.selected_file,
        selector.add_bookmark_page_number,
        selector.add_page,
        selector.convert_office,
        selector.confirm_temp_folder_delete,
        selector.ppt_slide_bookmarks,
        selector.convert_mail,
        selector.eml_encoding,
        selector.resize_pdf,
        selector.resize_size,
        selector.preflight_detail_repair,
        selector.preflight_confirm,
        selector.save_options,
        selector.asper_format,
        selector.keep_pdf_extension,
        selector.add_pdf_page_numbers,
        selector.page_number_options,
        selector.scale_x,
        selector.scale_y,
        selector.scale_enabled,
        selector.bookmark_view_mode,
        selector.base_view_width_mm,
        selector.base_view_height_mm,
        selector.expand_all,
        selector.collapse_level,
        selector,
    )
    return result


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


if __name__ == "__main__":
    (
        folder,
        file_path,
        add_bookmark_page_number,
        add_page,
        convert_office,
        confirm_temp_folder_delete,
        ppt_slide_bookmarks,
        convert_mail,
        eml_encoding,
        resize_pdf,
        resize_size,
        preflight_detail_repair,
        preflight_confirm,
        save_options,
        asper_format,
        keep_pdf_extension,
        add_pdf_page_numbers,
        page_number_options,
        scale_x,
        scale_y,
        scale_enabled,
        base_view_width_mm,
        base_view_height_mm,
        expand_all,
        collapse_level,
        progress_ui,
    ) = select_folder_and_file()
    print(f"Selected folder: {folder}")
    print(f"Output file: {file_path}")
    print(f"Add bookmark page numbers to bookmark labels: {add_bookmark_page_number}")
    print(f"Add page numbers to bookmark labels: {add_page}")
    print(f"Convert Office files: {convert_office}")
    print(f"Confirm temp folder delete: {confirm_temp_folder_delete}")
    print(f"Add PowerPoint slide bookmarks: {ppt_slide_bookmarks}")
    print(f"Support msg/eml files: {convert_mail}")
    print(f"eml encoding: {eml_encoding}")
    print(f"Resize PDF pages: {resize_pdf}")
    print(f"Resize PDF page size: {resize_size}")
    print(f"Preflight detail repair: {preflight_detail_repair}")
    print(f"Preflight step confirm: {preflight_confirm}")
    print(f"Save options: {save_options}")
    print(f"Apply Cyber ASPer bookmark name rules: {asper_format}")
    print(f"Keep .pdf in bookmark names: {keep_pdf_extension}")
    print(f"Add page numbers to PDF pages: {add_pdf_page_numbers}")
    print(f"PDF page number options: {page_number_options}")
    print(f"Scale X: {scale_x:.2f}")
    print(f"Scale Y: {scale_y:.2f}")
    print(f"Scale enabled: {scale_enabled}")
    print(f"Base view width: {base_view_width_mm}")
    print(f"Base view height: {base_view_height_mm}")
    print(f"Expand all bookmarks: {expand_all}")
    print(f"Collapse level: {collapse_level}")
