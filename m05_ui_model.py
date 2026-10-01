"""UI-independent settings and labels copied from the legacy UI.

Keep values in sync with the saved settings contract until the Qt cutover.
"""

import os

POINTS_PER_MM = 72 / 25.4

SAVE_MODE_OPTIONS = {
    "speed": {"save_options": {"garbage": 1, "deflate": False, "auto_clean_on_warning": False}},
    "balanced": {"save_options": {"garbage": 1, "deflate": True, "auto_clean_on_warning": False}},
    "smaller_file": {"save_options": {"garbage": 4, "deflate": True, "auto_clean_on_warning": False}},
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

PAGE_NUMBER_POSITION_LABELS = {
    "ja": {
        "top_left": "左上",
        "top_center": "中央上",
        "top_right": "右上",
        "bottom_left": "左下",
        "bottom_center": "中央下",
        "bottom_right": "右下",
    },
    "en": {
        "top_left": "Top left",
        "top_center": "Top center",
        "top_right": "Top right",
        "bottom_left": "Bottom left",
        "bottom_center": "Bottom center",
        "bottom_right": "Bottom right",
    },
}

PAGE_NUMBER_FORMAT_LABELS = {
    "ja": {
        "number": "1",
        "page_number": "Page 1",
        "number_total": "1 / 10",
        "page_of_total": "Page 1 of 10",
        "p_number": "p.1",
        "no_number": "No.1",
        "dash_number": "- 1 -",
        "bracket_number": "【1】",
    },
    "en": {
        "number": "1",
        "page_number": "Page 1",
        "number_total": "1 / 10",
        "page_of_total": "Page 1 of 10",
        "p_number": "p.1",
        "no_number": "No.1",
        "dash_number": "- 1 -",
        "bracket_number": "【1】",
    },
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
    "page_number_position": "bottom_right",
    "page_number_format": "number",
    "page_start_page": 1,
    "page_start_number": 1,
    "page_font_size": 30,
    "page_margin_x": 5,
    "page_margin_y": 5,
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
        "preflight_detail_repair": False,
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

TRANSLATIONS = {
            "en": {
                "window_title": "kojiPDF - Built with Python by Code4Construct",
                "title": "kojiPDF v2.6.0",
                "subtitle": "Select a folder and output PDF file, then create a structured inspection PDF.",
                "notice": (
                    "- Useful for creating paperless meeting materials with PDFs, organizing email data, and preparing construction document inspections (ASP support)\n"
                    "- Convert all PDFs, Office files, emails, images, text files, and ZIP files under the selected folder into one PDF, with folder hierarchy, email attachments, and ZIP contents organized as multi-level bookmarks\n"
                    "- Supports output adjustments such as page numbers, page resizing, PDF repair, and compression\n"
                    "Note: This app uses Python modules licensed under AGPL-3.0.\n"
                    "Commercial use is allowed. If modified, redistributed, or provided over a network, "
                    "the source code must be published under AGPL-3.0.\n"
                    "If this obligation is not met, permission to use the app cannot be granted."
                ),
                "open_viewer": "Open Viewer",
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
                "add_bookmark_page_number_and_count": "Add page no. + count",
                "add_bookmark_page_number_and_count_hint": "Ex. [bookmark]_[page no.]_[page count]",
                "keep_pdf_extension": "Keep .pdf",
                "convert_office": "Convert non-PDF files before merging",
                "convert_mail": "Convert .msg/.eml email and zip files to PDF",
                "eml_encoding": "eml encoding",
                "confirm_temp_folder_delete": "Confirm temp folder delete",
                "ppt_slide_bookmarks": "Add PowerPoint slide bookmarks",
                "resize_pdf": "Resize all PDFs to selected page size",
                "save_mode": "Save Mode",
                "pdf_detail_check": "Check PDF details",
                "pdf_detail_check_hint": (
                    "Only for failed merges, broken PDFs, or final checks before submission."
                ),
                "asper_format": "Apply Dennoh ASPer bookmark name rules",
                "add_pdf_page_numbers": "Add page numbers to merged PDF pages",
                "page_number_position": "Position",
                "page_number_format": "Format",
                "page_start_page": "Start page",
                "page_start_number": "Start number",
                "page_font_size": "Font size",
                "page_margin_right": "Right margin (mm)",
                "page_margin_bottom": "Bottom margin (mm)",
                "page_margin_left": "Left margin (mm)",
                "page_margin_disabled": "N/A",
                "page_margin_top": "Top margin (mm)",
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
                "title": "kojiPDF v2.6.0",
                "subtitle": "フォルダとPDF保存先を選択し、工事検査用PDFファイルを作成します。",
                "notice": (
                    "・PDFを活用したペーパーレス会議資料の作成、メールデータ整理、工事書類検査（ASP対応）に役立ちます。\n"
                    "・選択フォルダ配下のすべてのPDF、Office、メール、画像、テキスト、ZIPファイルをPDF化して1つのファイルに結合し、\n"
                    "　フォルダ階層・メール添付・ZIP内ファイルを複階層しおりとして整理したPDFを作成します。\n"
                    "・ページ番号、ページサイズ変更、PDF修復・圧縮などの出力調整に対応しています。\n"
                    "注意：本アプリは、使用しているPythonモジュールによりAGPL-3.0 Licenseが適用されます。\n"
                    "商用利用は可能ですが、改変・再配布・ネットワーク経由で提供する場合はソースコード公開が必要です。\n"
                    "この義務を遵守しない場合、AGPL-3.0に基づく利用許諾を受けられません。"
                ),
                "open_viewer": "kojiPDFviewerを起動",
                "select_folder": "フォルダ選択",
                "output": "出力PDF",
                "create": "PDFを作成",
                "create_short": "作成",
                "not_selected": "未選択",
                "general_options": "結合設定",
                "page_number_options": "ページ番号印字",
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
                "add_bookmark_page_number_and_count": "しおり名にページ番号と含まれるページ数を追加",
                "add_bookmark_page_number_and_count_hint": "例：[しおり名]_[ページ番号]_[含まれるページ数]",
                "keep_pdf_extension": "しおり名に.pdfを残す",
                "convert_office": "PDF以外のファイルをPDFに変換してから結合",
                "convert_mail": "msg・emlメール及びzipファイルをPDF化する",
                "eml_encoding": "eml文字コード",
                "confirm_temp_folder_delete": "暫定フォルダ削除確認",
                "ppt_slide_bookmarks": "PowerPointのスライドしおりを付ける",
                "resize_pdf": "すべてのPDFを指定サイズに変更",
                "save_mode": "保存方式",
                "pdf_detail_check": "PDFを詳しくチェック",
                "pdf_detail_check_hint": "PDF結合に失敗して壊れたPDFが混ざっていそうな場合、提出前に念入りに確認したい場合にのみON",
                "asper_format": "電脳ASPer用のしおり名に整える",
                "add_pdf_page_numbers": "結合PDFの各ページにページ番号を追加",
                "page_number_position": "配置",
                "page_number_format": "表示形式",
                "page_start_page": "開始ページ",
                "page_start_number": "開始番号",
                "page_font_size": "文字サイズ",
                "page_margin_right": "右余白(mm)",
                "page_margin_bottom": "下余白(mm)",
                "page_margin_left": "左余白(mm)",
                "page_margin_disabled": "無効",
                "page_margin_top": "上余白(mm)",
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


def load_custom_presets(path=None):
    """Read the existing version-1 preset file without changing its schema."""
    import json

    try:
        with open(path or settings_file_path(), "r", encoding="utf-8-sig") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    presets = data.get("custom_presets", {})
    if not isinstance(presets, dict):
        return {}
    return {
        code: presets[code]
        for code in PRESET_CODES
        if isinstance(presets.get(code), dict)
    }


def save_custom_presets(presets, path=None):
    import json

    destination = path or settings_file_path()
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    data = {
        "version": 1,
        "custom_presets": {
            code: presets[code]
            for code in PRESET_CODES
            if code in presets
        },
    }
    with open(destination, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)


def margin_setting_mm(settings, new_key, legacy_key, default_value):
    if new_key in settings:
        return settings[new_key]
    if legacy_key in settings:
        return round(float(settings[legacy_key]) / POINTS_PER_MM, 2)
    return default_value


def page_number_options(settings):
    """Convert UI millimetres to the PDF engine's point-based contract."""
    x_points = float(settings["page_margin_x"]) * POINTS_PER_MM
    y_points = float(settings["page_margin_y"]) * POINTS_PER_MM
    return {
        "position": settings["page_number_position"],
        "number_format": settings["page_number_format"],
        "start_page": settings["page_start_page"],
        "start_number": settings["page_start_number"],
        "font_size": settings["page_font_size"],
        "margin_x": x_points,
        "margin_y": y_points,
        "margin_right": x_points,
        "margin_bottom": y_points,
        "fontname": settings["page_font"],
        "fill": PAGE_NUMBER_COLOR_VALUES[settings["page_color"]],
        "fill_opacity": settings["page_opacity"],
    }