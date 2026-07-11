import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext

import ttkbootstrap as tb
from PIL import Image, ImageDraw, ImageFont, ImageTk


def resource_path(relative_path):
    """Return a path that works both from source and from a frozen executable."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


def debug_log(message):
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(local_app_data, "kojiPDF")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "kojiPDF_startup.log")
    with open(log_path, "a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{timestamp}] {message}\n")


class FlagButton(tk.Label):
    def __init__(self, master, flag, command, tooltip_text="", **kwargs):
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
            self.images[state] = make_flag_image(self.flag, state)
        self.configure(bg=self.bg_color, image=self.images[state])
        self.image = self.images[state]


def _circle_mask(size, scale):
    mask = Image.new("L", (size * scale, size * scale), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size * scale - 1, size * scale - 1), fill=255)
    return mask


def _scaled_points(points, scale):
    return [(x * scale, y * scale) for x, y in points]


def make_flag_image(flag, state):
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

    image = canvas.resize((size, size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)


def make_run_image(text, hover=False):
    size = 74
    scale = 4
    image = Image.new("RGBA", (size * scale, size * scale), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    fill = "#8f1d2c" if not hover else "#a92536"
    button_fill = "#eaf6fc" if hover else "#e7ecf2"
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
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)


def make_intro_icon_image():
    image = Image.open(resource_path("smallicon_v2.png")).convert("RGBA")
    image = image.resize((62, 62), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image)


class FileSelectorApp:
    def __init__(self):
        self.default_folder = os.path.expanduser("~/Documents")
        self.selected_folder = None
        self.selected_file = None
        self.accepted = False
        self.retry_requested = False
        self.language = "ja"
        self.color_choices = {
            "Red": (1, 0, 0),
            "Black": (0, 0, 0),
            "Blue": (0, 0, 1),
            "Gray": (0.5, 0.5, 0.5),
        }

        self.window = tb.Window(themename="flatly")
        self.window.title("kojiPDF - Built with Python by Code4Construct")
        self.window.geometry("790x665")
        self.window.minsize(760, 640)
        self.window.configure(bg="#e7ecf2")
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        self._build_window()
        self._apply_language()
        self.toggle_scale_mode()
        self.toggle_collapse_spinbox()
        self.toggle_page_number_options()
        self.toggle_office_options()
        debug_log("Tkinter UI loaded successfully")

    def _build_window(self):
        style = self.window.style
        style.configure("Koji.TFrame", background="#e7ecf2")
        style.configure("Panel.TFrame", background="#f7f9fb")
        style.configure("Band.TFrame", background="#f6f8fa")
        title_font = ("Segoe UI Variable Display", 22, "bold")
        style.configure("Title.TLabel", background="#e7ecf2", foreground="#0f1f2f", font=title_font)
        style.configure("Subtitle.TLabel", background="#e7ecf2", foreground="#33485c", font=("Yu Gothic UI", 11))
        style.configure("IntroSubtitle.TLabel", background="#f7f9fb", foreground="#33485c", font=("Yu Gothic UI", 11))
        style.configure("Notice.TLabel", background="#ffffff", foreground="#174a6b", font=("Yu Gothic UI", 9, "bold"))
        style.configure("License.TLabel", background="#ffffff", foreground="#25465f", font=("Yu Gothic UI", 7))
        style.configure("LicensePanel.TFrame", background="#eef7fb")
        style.configure("LicenseInner.TFrame", background="#ffffff")
        style.configure("Path.TLabel", background="#ffffff", foreground="#17212b", borderwidth=1, relief="solid", padding=7)
        style.configure("Field.TLabel", background="#f6f8fa", foreground="#17212b", font=("Yu Gothic UI", 10))
        style.configure("Section.TLabel", background="#f6f8fa", foreground="#174a6b", font=("Yu Gothic UI", 11, "bold"))
        style.configure("FormLabel.TLabel", background="#f7f9fb", foreground="#25465f", font=("Yu Gothic UI", 10, "bold"))
        style.configure("Run.TButton", font=("Yu Gothic UI", 12, "bold"), padding=(26, 10))

        root = tb.Frame(self.window, style="Koji.TFrame", padding=(14, 8, 14, 8))
        root.pack(fill="both", expand=True)

        header = tk.Frame(root, bg="#ffffff", height=42)
        header.pack_propagate(False)
        header.pack(fill="x", pady=(0, 6))
        header.columnconfigure(0, minsize=96)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, minsize=96)
        header_left_balance = tk.Frame(header, bg="#ffffff", width=96)
        header_left_balance.grid(row=0, column=0, sticky="nsew")
        self.title_label = tk.Label(
            header,
            bg="#ffffff",
            fg="#0f1f2f",
            font=title_font,
            anchor="center",
        )
        self.title_label.grid(row=0, column=1, sticky="nsew")
        flag_holder = tk.Frame(header, bg="#ffffff", width=96)
        flag_holder.grid(row=0, column=2, sticky="nsew")
        self.japanese_button = FlagButton(flag_holder, "jp", lambda: self._set_language("ja"), bg="#ffffff")
        self.english_button = FlagButton(flag_holder, "gb", lambda: self._set_language("en"), bg="#ffffff")
        self.english_button.pack(side="right", padx=(6, 0))
        self.japanese_button.pack(side="right", padx=(6, 0))

        intro_panel = tb.Frame(root, style="Panel.TFrame", height=76, padding=(8, 6))
        intro_panel.pack_propagate(False)
        intro_panel.pack(fill="x", pady=(0, 6))

        self.subtitle_label = tb.Label(intro_panel, style="IntroSubtitle.TLabel", wraplength=720)

        notice_panel = tk.Frame(intro_panel, bg="#ffffff", height=64)
        notice_panel.pack_propagate(False)
        notice_panel.columnconfigure(0, minsize=70)
        notice_panel.columnconfigure(1, weight=1)
        notice_panel.pack(fill="x", expand=True)
        self.intro_icon_image = make_intro_icon_image()
        self.intro_icon_label = tk.Label(notice_panel, image=self.intro_icon_image, bg="#ffffff", bd=0)
        self.intro_icon_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.notice_label = tb.Label(notice_panel, style="Notice.TLabel", wraplength=630, justify="left")
        self.notice_label.grid(row=0, column=1, sticky="nsew")

        top_panel = tk.Frame(root, bg="#ffffff", padx=10, pady=10)
        top_panel.pack(fill="x", pady=(0, 6))
        top_panel.columnconfigure(1, weight=1)
        self.folder_button = tb.Button(top_panel, bootstyle="secondary-outline", command=self.select_folder)
        self.folder_button.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=3)
        self.folder_text = tk.StringVar()
        self.folder_label = tb.Label(top_panel, textvariable=self.folder_text, style="Path.TLabel", wraplength=560)
        self.folder_label.grid(row=0, column=1, sticky="ew", pady=3)
        self.file_button = tb.Button(top_panel, bootstyle="secondary-outline", command=self.select_save_file)
        self.file_button.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=3)
        self.file_text = tk.StringVar()
        self.file_label = tb.Label(top_panel, textvariable=self.file_text, style="Path.TLabel", wraplength=560)
        self.file_label.grid(row=1, column=1, sticky="ew", pady=3)
        self.run_button = tk.Label(
            top_panel,
            bd=0,
            bg="#ffffff",
            cursor="hand2",
        )
        self.run_button.grid(row=0, column=2, rowspan=2, sticky="ns", padx=(12, 0))
        self.run_button.bind("<Button-1>", lambda _event: self.finish())
        self.run_button.bind("<Enter>", lambda _event: self._draw_run_button(hover=True))
        self.run_button.bind("<Leave>", lambda _event: self._draw_run_button(hover=False))

        self.options_group = tb.Frame(root, style="Koji.TFrame")
        self.options_group.pack(fill="x")
        self.options_group.columnconfigure(0, weight=5)
        self.options_group.columnconfigure(1, weight=6)

        self._build_general_options()
        self._build_bookmark_options()
        self._build_page_number_options()
        self._build_scale_options()
        self._build_asp_options()

        license_notice_panel = tb.Frame(root, style="LicensePanel.TFrame", height=56, padding=(8, 8, 8, 8))
        license_notice_panel.pack_propagate(False)
        license_notice_panel.pack(fill="x")
        license_inner_panel = tb.Frame(license_notice_panel, style="LicenseInner.TFrame")
        license_inner_panel.pack(fill="both", expand=True)
        self.license_notice_label = tb.Label(
            license_inner_panel,
            style="License.TLabel",
            wraplength=720,
            justify="left",
        )
        self.license_notice_label.pack(fill="x", expand=True)
        self._draw_run_button()

    def _band(self, row, title_attr, parent=None, column=0, columnspan=1, padx=(0, 0), pady=(0, 6)):
        parent = parent or self.options_group
        frame = tb.Frame(parent, style="Band.TFrame", padding=10)
        frame.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=padx, pady=pady)
        frame.columnconfigure(0, weight=1)
        title_label = tb.Label(frame, style="Section.TLabel")
        title_label.grid(row=0, column=0, sticky="w", columnspan=8, pady=(0, 6))
        setattr(self, title_attr, title_label)
        return frame

    def _build_general_options(self):
        frame = self._band(0, "general_section_label", column=0, padx=(0, 4))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        self.add_page_var = tk.BooleanVar(value=False)
        self.convert_office_var = tk.BooleanVar(value=False)
        self.ppt_slide_bookmarks_var = tk.BooleanVar(value=False)
        self.resize_pdf_var = tk.BooleanVar(value=False)
        self.asper_format_var = tk.BooleanVar(value=False)
        self.keep_pdf_extension_var = tk.BooleanVar(value=False)
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
        resize_row = tb.Frame(frame, style="Band.TFrame")
        self.resize_pdf_checkbox = tb.Checkbutton(resize_row, variable=self.resize_pdf_var, bootstyle="primary-round-toggle")
        self.convert_office_checkbox.grid(row=1, column=0, columnspan=2, sticky="w", pady=3)
        self.ppt_slide_bookmarks_checkbox.grid(row=2, column=0, columnspan=2, sticky="w", padx=(66, 0), pady=3)
        resize_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=3)
        self.resize_pdf_checkbox.pack(side="left")
        self.resize_size_var = tk.StringVar(value="A4")
        self.resize_size_combo = tb.Combobox(resize_row, textvariable=self.resize_size_var, values=["A3", "A4", "A5", "B4", "B5"], width=8, state="readonly")
        self.resize_size_combo.pack(side="left", padx=(12, 0))

    def _build_page_number_options(self):
        frame = self._band(1, "page_number_section_label", column=0, columnspan=2)
        self.page_number_section_label.grid_configure(columnspan=1)
        for col in range(8):
            frame.columnconfigure(col, weight=1 if col in (1, 3, 5, 7) else 0)

        self.add_pdf_page_numbers_var = tk.BooleanVar(value=False)
        self.add_pdf_page_numbers_checkbox = tb.Checkbutton(
            frame,
            variable=self.add_pdf_page_numbers_var,
            bootstyle="primary-round-toggle",
            command=self.toggle_page_number_options,
        )
        self.add_pdf_page_numbers_checkbox.grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 8))

        self.page_start_number_label = tb.Label(frame, style="Field.TLabel")
        self.page_start_number_spinbox = self._make_spinbox(frame, 1, 9999, 1, 1, integer=True)
        self.page_font_size_label = tb.Label(frame, style="Field.TLabel")
        self.page_font_size_spinbox = self._make_spinbox(frame, 1, 300, 1, 100, integer=True)
        self.page_margin_right_label = tb.Label(frame, style="Field.TLabel")
        self.page_margin_right_spinbox = self._make_spinbox(frame, 0, 1000, 1, 30, integer=True)
        self.page_margin_bottom_label = tb.Label(frame, style="Field.TLabel")
        self.page_margin_bottom_spinbox = self._make_spinbox(frame, 0, 1000, 1, 25, integer=True)

        labels_widgets = [
            (self.page_start_number_label, self.page_start_number_spinbox),
            (self.page_font_size_label, self.page_font_size_spinbox),
            (self.page_margin_right_label, self.page_margin_right_spinbox),
            (self.page_margin_bottom_label, self.page_margin_bottom_spinbox),
        ]
        for index, (label, widget) in enumerate(labels_widgets):
            label.grid(row=1, column=index * 2, sticky="e", padx=(0, 6), pady=3)
            widget.grid(row=1, column=index * 2 + 1, sticky="w", pady=3)

        self.page_font_label = tb.Label(frame, style="Field.TLabel")
        self.page_font_var = tk.StringVar(value="helv")
        self.page_font_combo = tb.Combobox(frame, textvariable=self.page_font_var, values=["helv", "cour", "tiro"], width=8, state="readonly")
        self.page_color_label = tb.Label(frame, style="Field.TLabel")
        self.page_color_var = tk.StringVar(value="Red")
        self.page_color_combo = tb.Combobox(frame, textvariable=self.page_color_var, values=list(self.color_choices), width=8, state="readonly")
        self.page_opacity_label = tb.Label(frame, style="Field.TLabel")
        self.page_opacity_spinbox = self._make_spinbox(frame, 0.05, 1.00, 0.05, 0.20, integer=False)

        self.page_font_label.grid(row=2, column=0, sticky="e", padx=(0, 6), pady=3)
        self.page_font_combo.grid(row=2, column=1, sticky="w", pady=3)
        self.page_color_label.grid(row=2, column=2, sticky="e", padx=(0, 6), pady=3)
        self.page_color_combo.grid(row=2, column=3, sticky="w", pady=3)
        self.page_opacity_label.grid(row=2, column=4, sticky="e", padx=(0, 6), pady=3)
        self.page_opacity_spinbox.grid(row=2, column=5, sticky="w", pady=3)

    def _build_scale_options(self, parent=None):
        frame = self._band(2, "scale_section_label", parent=parent, column=0, padx=(0, 4))
        self.scale_section_label.grid_configure(columnspan=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)
        self.scale_mode_var = tk.StringVar(value="relative")
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
        self.relative_scale_radio.grid(row=0, column=1, sticky="w", padx=(18, 0), pady=(0, 8))
        self.absolute_scale_radio.grid(row=0, column=2, sticky="w", padx=(12, 0), pady=(0, 8))
        self.horizontal_scale_label.grid(row=1, column=0, sticky="e", padx=(0, 8), pady=2)
        self.scale_x_spinbox.grid(row=1, column=1, sticky="w", pady=2)
        self.vertical_scale_label.grid(row=1, column=2, sticky="e", padx=(12, 8), pady=2)
        self.scale_y_spinbox.grid(row=1, column=3, sticky="w", pady=2)
        self.base_view_width_label.grid(row=1, column=0, sticky="e", padx=(0, 8), pady=2)
        self.base_view_width_spinbox.grid(row=1, column=1, sticky="w", pady=2)
        self.base_view_height_label.grid(row=1, column=2, sticky="e", padx=(12, 8), pady=2)
        self.base_view_height_spinbox.grid(row=1, column=3, sticky="w", pady=2)

    def _build_bookmark_options(self, parent=None):
        frame = self._band(0, "bookmark_section_label", parent=parent, column=1, padx=(4, 0))
        frame.columnconfigure(0, weight=1)
        self.add_page_checkbox = tb.Checkbutton(frame, variable=self.add_page_var, bootstyle="primary-round-toggle")
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
        self.add_page_checkbox.grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        self.expand_all_checkbox.grid(row=2, column=0, sticky="w", pady=3)
        self.bookmark_open_level_label = tb.Label(frame, style="Field.TLabel")
        self.bookmark_open_level_label.grid(row=2, column=1, sticky="e", padx=(16, 8), pady=3)
        self.collapse_spinbox = self._make_spinbox(frame, 1, 10, 1, 1, integer=True)
        self.collapse_spinbox.grid(row=2, column=2, sticky="w", pady=3)
        self.keep_pdf_extension_checkbox.grid(row=3, column=0, columnspan=3, sticky="w", pady=3)

    def _build_asp_options(self):
        frame = self._band(2, "asp_section_label", column=1, padx=(4, 0))
        self.asper_format_checkbox = tb.Checkbutton(
            frame,
            variable=self.asper_format_var,
            bootstyle="primary-round-toggle",
        )
        self.asper_format_checkbox.grid(row=1, column=0, sticky="w", pady=3)

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
        if not hasattr(self, "run_button"):
            return
        key = "run_hover_image" if hover else "run_image"
        image = make_run_image(self._text("create_short"), hover)
        setattr(self, key, image)
        self.run_button.configure(bg="#ffffff", image=image)
        self.run_button.image = image

    def _spinbox_value(self, spinbox):
        self._normalize_spinbox(spinbox)
        value = float(spinbox._koji_var.get())
        return int(value) if spinbox._koji_integer else value

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
        self.japanese_button.set_checked(language == "ja")
        self.english_button.set_checked(language == "en")
        self._apply_language()

    def _text(self, key):
        translations = {
            "en": {
                "window_title": "kojiPDF - Built with Python by Code4Construct",
                "title": "kojiPDF v2.0.0",
                "subtitle": "Select a folder and output PDF file, then create a structured inspection PDF.",
                "notice": (
                    "- Merge PDFs and create bookmarks from file and folder names\n"
                    "- Convert Office files, add transparent page numbers, and resize pages\n"
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
                "page_number_options": "Page numbers",
                "scale_options": "Bookmark view adjust",
                "bookmark_options": "Bookmark display",
                "asp_options": "Construction info-sharing (ASP)",
                "progress_title": "Progress",
                "progress_started": "Starting PDF creation...\n",
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
                "add_page": "Add included page count to bookmark names",
                "keep_pdf_extension": "Keep .pdf in bookmark names",
                "convert_office": "Convert Office files to PDF before merging",
                "ppt_slide_bookmarks": "Add PowerPoint slide bookmarks",
                "resize_pdf": "Resize all PDFs to selected page size",
                "asper_format": "Apply Dennoh ASPer bookmark name rules",
                "add_pdf_page_numbers": "Add page numbers to merged PDF pages",
                "page_start_number": "Start number",
                "page_font_size": "Font size",
                "page_margin_right": "Right margin",
                "page_margin_bottom": "Bottom margin",
                "page_font": "Font",
                "page_color": "Color",
                "page_opacity": "Opacity",
                "relative_scale": "Relative",
                "absolute_scale": "Absolute",
                "horizontal_scale": "Width corr.",
                "vertical_scale": "Height corr.",
                "base_view_width": "Base width",
                "base_view_height": "Base height",
                "expand_all": "Expand all",
                "bookmark_level": "Open level",
                "folder_dialog": "Select folder",
                "file_dialog": "Select output PDF",
                "default_output": "merged_inspection_documents.pdf",
                "pdf_filetype": "PDF files",
            },
            "ja": {
                "window_title": "kojiPDF - Built with Python by Code4Construct",
                "title": "kojiPDF v2.0.0",
                "subtitle": "フォルダとPDF保存先を選択し、工事検査用PDFファイルを作成します。",
                "notice": (
                    "・選択フォルダ内のPDFを結合し、ファイル名をしおり、フォルダ名を親しおりとして追加した構造化PDFを作成\n"
                    "・Microsoft OfficeファイルのPDF自動変換、透過文字によるページ番号付与、ページサイズ変更などに対応\n"
                    "用途：工事検査資料の整理、情報共有システムの電子データ確認、"
                    "ペーパーレス会議資料の作成・閲覧\n"
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
                "page_number_options": "ページ番号",
                "scale_options": "しおり表示位置補正",
                "bookmark_options": "しおり表示",
                "asp_options": "工事情報共有システム（ASP）",
                "progress_title": "作成状況",
                "progress_started": "PDF作成を開始します...\n",
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
                "add_page": "しおり名に含まれるページ数を追加",
                "keep_pdf_extension": "しおり名に.pdfを残す",
                "convert_office": "Word・Excel・PowerPointをPDFに変換してから結合",
                "ppt_slide_bookmarks": "PowerPointのスライドしおりを付ける",
                "resize_pdf": "すべてのPDFを指定サイズに変更",
                "asper_format": "電脳ASPer用のしおり名に整える",
                "add_pdf_page_numbers": "結合PDFの各ページにページ番号を追加",
                "page_start_number": "開始番号",
                "page_font_size": "文字サイズ",
                "page_margin_right": "右余白",
                "page_margin_bottom": "下余白",
                "page_font": "フォント",
                "page_color": "色",
                "page_opacity": "透明度",
                "relative_scale": "相対補正",
                "absolute_scale": "絶対補正",
                "horizontal_scale": "表示幅補正",
                "vertical_scale": "表示高さ補正",
                "base_view_width": "基準表示幅",
                "base_view_height": "基準表示高さ",
                "expand_all": "すべてのしおりを展開",
                "bookmark_level": "しおり展開階層",
                "folder_dialog": "フォルダを選択してください",
                "file_dialog": "出力PDFを指定してください",
                "default_output": "結合済み検査資料.pdf",
                "pdf_filetype": "PDFファイル",
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

    def _apply_language(self):
        self.window.title(self._text("window_title"))
        self.title_label.configure(text=self._text("title"), bg="#ffffff", fg="#0f1f2f")
        self.subtitle_label.configure(text=self._text("subtitle"))
        notice_text, license_notice_text = self._notice_parts()
        notice_font_size = 9
        license_font_size = 8
        self.notice_label.configure(font=("Yu Gothic UI", notice_font_size, "bold"))
        self.license_notice_label.configure(font=("Yu Gothic UI", license_font_size))
        self.notice_label.configure(text=notice_text)
        self.license_notice_label.configure(text=license_notice_text)
        self.folder_button.configure(text=self._text("select_folder"))
        self.file_button.configure(text=self._text("output"))
        self.general_section_label.configure(text=self._text("general_options"))
        self.page_number_section_label.configure(text=self._text("page_number_options"))
        self.scale_section_label.configure(text=self._text("scale_options"))
        self.bookmark_section_label.configure(text=self._text("bookmark_options"))
        self.asp_section_label.configure(text=self._text("asp_options"))
        self.add_page_checkbox.configure(text=self._text("add_page"))
        self.keep_pdf_extension_checkbox.configure(text=self._text("keep_pdf_extension"))
        self.convert_office_checkbox.configure(text=self._text("convert_office"))
        self.ppt_slide_bookmarks_checkbox.configure(text=self._text("ppt_slide_bookmarks"))
        self.resize_pdf_checkbox.configure(text=self._text("resize_pdf"))
        self.asper_format_checkbox.configure(text=self._text("asper_format"))
        self.add_pdf_page_numbers_checkbox.configure(text="")
        self.page_start_number_label.configure(text=self._text("page_start_number"))
        self.page_font_size_label.configure(text=self._text("page_font_size"))
        self.page_margin_right_label.configure(text=self._text("page_margin_right"))
        self.page_margin_bottom_label.configure(text=self._text("page_margin_bottom"))
        self.page_font_label.configure(text=self._text("page_font"))
        self.page_color_label.configure(text=self._text("page_color"))
        self.page_opacity_label.configure(text=self._text("page_opacity"))
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

    def show(self):
        self._center_window()
        self.window.after(0, self._bring_to_front)
        debug_log("Window shown")
        self.window.mainloop()

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
        self.progress_panel = tb.Frame(self.options_group, style="Band.TFrame", padding=12)
        self.progress_panel.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.options_group.rowconfigure(0, weight=1)
        self.options_group.columnconfigure(0, weight=1)
        self.options_group.columnconfigure(1, weight=1)
        self.progress_panel.rowconfigure(4, weight=1)
        self.progress_panel.columnconfigure(0, weight=1)

        self.progress_title_label = tb.Label(self.progress_panel, style="Section.TLabel")
        self.progress_title_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.progress_title_label.configure(text=self._text("progress_title"))

        self.progress_bar = tb.Progressbar(self.progress_panel, mode="indeterminate", bootstyle="danger-striped")
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.progress_bar.start(12)

        self.progress_current_text = tk.StringVar(value=self._text("progress_started").strip())
        self.progress_current_label = tk.Label(
            self.progress_panel,
            textvariable=self.progress_current_text,
            bg="#eef7fb",
            fg="#174a6b",
            anchor="w",
            font=("Yu Gothic UI", 10, "bold"),
            padx=8,
            pady=5,
        )
        self.progress_current_label.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.progress_step_frame = tk.Frame(self.progress_panel, bg="#f6f8fa")
        self.progress_step_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.progress_steps = self._progress_steps()
        self.progress_step_labels = []
        for index, step in enumerate(self.progress_steps):
            self.progress_step_frame.columnconfigure(index, weight=1)
            label = tk.Label(
                self.progress_step_frame,
                text=f"{index + 1}. {step['label']}",
                bg="#dfe8ef",
                fg="#25465f",
                anchor="center",
                font=("Yu Gothic UI", 9),
                padx=5,
                pady=5,
            )
            label.grid(row=0, column=index, sticky="ew", padx=(0, 4 if index < len(self.progress_steps) - 1 else 0))
            self.progress_step_labels.append(label)
        self.progress_step_index = -1
        self._set_progress_step(0)

        self.progress_text = scrolledtext.ScrolledText(
            self.progress_panel,
            height=14,
            wrap="word",
            bg="#ffffff",
            fg="#17212b",
            insertbackground="#17212b",
            relief="flat",
            borderwidth=0,
            font=("Yu Gothic UI", 10),
        )
        self.progress_text.grid(row=4, column=0, sticky="nsew")
        self.progress_text.configure(state="disabled")
        self.append_progress(self._text("progress_started"))
        self.window.update_idletasks()

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
                label.configure(text=f"{i + 1}. {self.progress_steps[i]['label']}", bg="#dfe8ef", fg="#25465f")

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
            self._update_progress_from_message(message)
            self.progress_text.configure(state="normal")
            self.progress_text.insert("end", message)
            self.progress_text.see("end")
            self.progress_text.configure(state="disabled")
            self.window.update_idletasks()
            self.window.update()
        except tk.TclError:
            pass

    def finish_progress(self, success=True):
        if not hasattr(self, "progress_text"):
            return
        try:
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

    def toggle_scale_mode(self):
        relative_mode = self.scale_mode_var.get() == "relative"
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
            widget.grid() if relative_mode else widget.grid_remove()
        for widget in absolute_widgets:
            widget.grid_remove() if relative_mode else widget.grid()

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
        self.ppt_slide_bookmarks_checkbox.configure(state=state)

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

    @property
    def add_page(self):
        return self.add_page_var.get()

    @property
    def convert_office(self):
        return self.convert_office_var.get()

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
            "fontname": self.page_font_var.get(),
            "fill": self.color_choices[self.page_color_var.get()],
            "fill_opacity": self._spinbox_value(self.page_opacity_spinbox),
        }

    @property
    def scale_x(self):
        if self.scale_mode_var.get() == "absolute":
            return 1.0
        return self._spinbox_value(self.scale_x_spinbox)

    @property
    def scale_y(self):
        if self.scale_mode_var.get() == "absolute":
            return 1.0
        return self._spinbox_value(self.scale_y_spinbox)

    @property
    def scale_enabled(self):
        return True

    @property
    def base_view_width_mm(self):
        if self.scale_mode_var.get() == "relative":
            return 330
        return self._spinbox_value(self.base_view_width_spinbox)

    @property
    def base_view_height_mm(self):
        if self.scale_mode_var.get() == "relative":
            return 210
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
        selector.add_page,
        selector.convert_office,
        selector.ppt_slide_bookmarks,
        selector.resize_pdf,
        selector.resize_size,
        selector.asper_format,
        selector.keep_pdf_extension,
        selector.add_pdf_page_numbers,
        selector.page_number_options,
        selector.scale_x,
        selector.scale_y,
        selector.scale_enabled,
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
            self.progress_ui.append_progress(message)

    def flush(self):
        if self.original is not None:
            self.original.flush()


if __name__ == "__main__":
    (
        folder,
        file_path,
        add_page,
        convert_office,
        ppt_slide_bookmarks,
        resize_pdf,
        resize_size,
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
    print(f"Add page numbers to bookmark labels: {add_page}")
    print(f"Convert Office files: {convert_office}")
    print(f"Add PowerPoint slide bookmarks: {ppt_slide_bookmarks}")
    print(f"Resize PDF pages: {resize_pdf}")
    print(f"Resize PDF page size: {resize_size}")
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
