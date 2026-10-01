import os
import shutil
import sys
import tempfile
import time
import threading
import traceback
from datetime import datetime


def startup_log(message):
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    log_dir = os.path.join(local_app_data, "kojiPDF")
    try:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "kojiPDF_startup.log")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    startup_log(
        "Unhandled exception:\n"
        + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = log_unhandled_exception
startup_log("kojiPDF process started")

from fitz import TOOLS, open as fitz_open

import m01make_treedata as tree_data
import m02merge_from_treedata as pdf_merge
import m03make_bookmark as bookmark_builder
import m04file_name_replace as tree_data_cleanup
import m05_qt_ui as gui
import qt_dialogs
import m06finish_message as confirmation_dialog
import m10set_newtoc as bookmark_links
import m11add_number_bookmarks as bookmark_page_counts
import m14asper_format as asper_bookmarks
import m21get_eachPDF_toc as source_bookmarks
import m22add_child_toc as child_bookmarks
import m44temp_convert as office_temp_convert
import m45invalid_pdflist as pdf_validation
import m46pdf_resize as pdf_resize
import m47add_pagenum as pdf_page_numbers
import m52launch_config as launch_config_loader


class SourcePdfRepairedRetry(Exception):
    def __init__(self, message, repaired_folder_path):
        super().__init__(message)
        self.repaired_folder_path = repaired_folder_path


FINAL_PDF_REPLACE_RETRY_DELAYS = (0.5, 1, 2)
FINAL_PDF_REPLACE_LOCK_WINERRORS = {5, 32, 33}


class FinalPdfReplaceError(PermissionError):
    def __init__(self, output_file_path, preserved_candidate_path, original_error):
        self.output_file_path = output_file_path
        self.preserved_candidate_path = preserved_candidate_path
        self.original_error = original_error
        message = (
            "\u6700\u7d42PDF\u3092\u51fa\u529b\u5148\u3078\u7f6e\u304d\u63db\u3048\u3089\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002\n"
            "\u51fa\u529b\u5148PDF\u304cPDF\u30d3\u30e5\u30fc\u30a2\u306a\u3069\u3067\u958b\u304b\u308c\u3066\u3044\u308b\u53ef\u80fd\u6027\u304c\u3042\u308a\u307e\u3059\u3002\n"
            "\u65b0\u3057\u304f\u4f5c\u6210\u3057\u305fPDF\u306f\u6b21\u306e\u4e00\u6642\u30d5\u30a1\u30a4\u30eb\u3068\u3057\u3066\u6b8b\u3057\u307e\u3057\u305f\u3002\n"
            f"\u51fa\u529b\u5148: {output_file_path}\n"
            f"\u4fdd\u5b58\u6e08\u307f\u5019\u88dcPDF: {preserved_candidate_path}\n"
            "\u51fa\u529b\u5148PDF\u3092\u9589\u3058\u3066\u304b\u3089\u3001\u5fc5\u8981\u306b\u5fdc\u3058\u3066\u5019\u88dcPDF\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002\n"
            f"\u8a73\u7d30: {type(original_error).__name__}: {original_error}"
        )
        super().__init__(message)


def is_output_replace_lock_error(exc):
    if isinstance(exc, PermissionError):
        return True
    winerror = getattr(exc, "winerror", None)
    return winerror in FINAL_PDF_REPLACE_LOCK_WINERRORS


def replace_final_pdf_with_retry(candidate_path, output_file_path):
    last_error = None
    for delay in (0, *FINAL_PDF_REPLACE_RETRY_DELAYS):
        if delay:
            print(f"\u51fa\u529b\u5148PDF\u306e\u7f6e\u304d\u63db\u3048\u3092\u518d\u8a66\u884c\u3057\u307e\u3059... {delay:g}\u79d2\u5f85\u6a5f")
            time.sleep(delay)
        try:
            os.replace(candidate_path, output_file_path)
            return
        except OSError as exc:
            if not is_output_replace_lock_error(exc):
                raise
            last_error = exc
            print(f"\u51fa\u529b\u5148PDF\u306e\u7f6e\u304d\u63db\u3048\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u3002\u518d\u8a66\u884c\u5bfe\u8c61\u3067\u3059: {exc}")
    raise FinalPdfReplaceError(output_file_path, candidate_path, last_error) from last_error


def ensure_output_file_writable(output_file_path):
    if not os.path.exists(output_file_path):
        return

    try:
        with open(output_file_path, "r+b"):
            pass
    except PermissionError as exc:
        raise PermissionError(
            "出力先PDFファイルが使用中のため上書きできません。\n"
            "PDFビューアなどで開いている場合は閉じてから、もう一度実行してください。\n"
            f"対象ファイル: {output_file_path}"
        ) from exc
    except OSError as exc:
        raise OSError(
            "出力先PDFファイルを上書きできるか確認できませんでした。\n"
            "PDFビューアなどで開いていないか確認してください。\n"
            f"対象ファイル: {output_file_path}\n"
            f"詳細: {exc}"
        ) from exc


def ensure_safe_temp_folder_delete_path(folder_path):
    absolute_path = os.path.abspath(folder_path)
    if os.path.basename(absolute_path).lower() != "temp_folder":
        raise RuntimeError(f"Refusing to delete non-temp folder: {absolute_path}")
    return absolute_path


def delete_temp_folder_best_effort(folder_path, issue_report=None):
    try:
        shutil.rmtree(ensure_safe_temp_folder_delete_path(folder_path))
        return True
    except (PermissionError, OSError) as exc:
        message = f"一時フォルダの削除をスキップしました（使用中）: {folder_path}\n{type(exc).__name__}: {exc}"
        print(message)
        add_issue(issue_report, "Temporary folder delete skipped", message)
        return False


def add_issue(issue_report, category, message):
    if issue_report is not None:
        issue_report.append(
            {
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "category": category,
                "message": str(message),
            }
        )


def summarize_issue_message(message, max_lines=40):
    text = str(message)
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text

    shown = lines[:max_lines]
    shown.append(f"... {len(lines) - max_lines} more warning lines omitted")
    return "\n".join(shown)


def long_path_hint_from_exception(exc):
    paths = []
    filename = getattr(exc, "filename", None)
    filename2 = getattr(exc, "filename2", None)
    if filename:
        paths.append(("path", filename))
    if filename2:
        paths.append(("path2", filename2))

    text = str(exc)
    for quoted in text.split("'")[1::2]:
        if "\\" in quoted or "/" in quoted:
            paths.append(("message path", quoted))

    lines = []
    seen = set()
    for label, path in paths:
        path_text = str(path)
        if path_text in seen:
            continue
        seen.add(path_text)
        path_length = len(path_text)
        lines.append(f"{label} length: {path_length}")
        lines.append(f"{label}: {path_text}")

    if not lines:
        return ""

    if os.name == "nt" and any(len(str(path)) >= 240 for _, path in paths):
        lines.extend(
            [
                "Long path warning: one or more paths are close to or over the traditional Windows 260 character limit.",
                "The file may exist and open in Office, while Python or Office automation still reports FileNotFoundError.",
            ]
        )
    return "\n".join(lines)


def write_issue_report(output_file_path, issue_report):
    if not issue_report:
        return None

    output_dir = os.path.dirname(os.path.abspath(output_file_path)) or "."
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_dir, f"kojiPDF_error_report_{timestamp}.txt")

    lines = [
        "kojiPDF error / warning report",
        f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Output PDF: {output_file_path}",
        "",
    ]
    for index, item in enumerate(issue_report, start=1):
        lines.extend(
            [
                f"[{index}] {item.get('category', 'Issue')}",
                f"Time: {item.get('time', '')}",
                summarize_issue_message(item.get("message", "")),
                "",
            ]
        )

    with open(report_path, "w", encoding="utf-8-sig") as report_file:
        report_file.write("\n".join(lines))
    print(f"エラー一覧を保存しました: {report_path}")
    return report_path


def open_output_pdf_file(output_file_path, issue_report=None):
    try:
        if not output_file_path or not os.path.exists(output_file_path):
            raise FileNotFoundError(f"Output PDF was not found: {output_file_path}")
        os.startfile(os.path.abspath(output_file_path))
        print(f"出力PDFを開きました: {output_file_path}")
    except Exception as exc:
        message = f"出力PDFを自動で開けませんでした: {output_file_path}\n{type(exc).__name__}: {exc}"
        print(message)
        add_issue(issue_report, "Open output PDF warning", message)


def save_pdf_collecting_mupdf_warnings(pdf_document, output_file_path, save_options):
    save_options = dict(save_options)
    save_options.pop("auto_clean_on_warning", None)
    TOOLS.reset_mupdf_warnings()
    TOOLS.mupdf_display_errors(False)
    TOOLS.mupdf_display_warnings(False)
    try:
        pdf_document.save(output_file_path, **save_options)
        return TOOLS.mupdf_warnings()
    finally:
        TOOLS.mupdf_display_errors(True)
        TOOLS.mupdf_display_warnings(True)


def is_smaller_file_save_mode(save_options):
    return int(save_options.get("garbage", 0)) >= 4 and bool(save_options.get("deflate"))


def choose_save_warning_action(warnings):
    return qt_dialogs.choose_save_warning_action(warnings)


def show_pdf_check_report(title, report, actions=None):
    return qt_dialogs.show_pdf_check_report(title, report, actions)


def run_fast_preflight_check(
    source_folder_path,
    output_file_path,
    confirm_problems=False,
    repair_warnings=False,
    issue_report=None,
):
    title = "高速な結合前チェック結果"
    print("Fast preflight PDF check started.")
    results = pdf_validation.check_folder_pdfs(source_folder_path, detailed=False)
    problems = pdf_validation.problem_results(results)
    if not problems:
        print("Fast preflight PDF check passed.")
        return

    report = pdf_validation.summarize_check_results(results, title)
    add_issue(issue_report, "PDF preflight check", report)
    print(report)
    errors = [item for item in problems if item["status"] == "error"]
    repairable = [item for item in problems if item["status"] == "warning"]
    if errors:
        show_pdf_check_report(
            title,
            report + "\n\n手動対応が必要なPDFがあります。処理を終了します。",
        )
        raise RuntimeError("高速な結合前チェックでエラーが見つかったため処理を終了しました。")

    if repairable and repair_warnings:
        repair_results, error_files_dir = pdf_validation.repair_problem_source_pdfs(
            repairable,
            source_folder_path,
            output_file_path,
        )
        repair_report = pdf_validation.summarize_repair_results(
            repair_results,
            error_files_dir,
        )
        print(repair_report)
        failed = [item for item in repair_results if item["status"] == "failed"]
        repaired = [item for item in repair_results if item["status"] == "repaired"]
        post_report = ""
        if repaired:
            post_results = pdf_validation.check_folder_pdfs(source_folder_path, detailed=False)
            post_report = pdf_validation.summarize_check_results(post_results, "高速修復後の結合前チェック結果")
            print(post_report)
        combined_report = report + "\n\n" + repair_report
        if post_report:
            combined_report += "\n\n" + post_report
        if confirm_problems:
            show_pdf_check_report("高速チェック・修復結果", combined_report)
        if failed:
            add_issue(issue_report, "Source PDF repair failed", repair_report)
            print("Some source PDF warnings could not be repaired. Continuing with the original PDFs.")
        if repaired:
            print("Fast preflight PDF warnings were repaired. Continuing.")
        return
    if repairable:
        print("Source PDF warnings were found, but source repair is enabled only in compress mode.")
        print("Continuing without confirmation because detailed PDF check is off.")


def run_detail_preflight_repair(
    source_folder_path,
    output_file_path,
    confirm_steps=False,
    repair_warnings=False,
    issue_report=None,
):
    title = "事前詳細チェック結果"
    print("Detailed preflight PDF check started.")
    results = pdf_validation.check_folder_pdfs(source_folder_path, detailed=True)
    report = pdf_validation.summarize_check_results(results, title)
    print(report)
    problems = pdf_validation.problem_results(results)
    if not problems:
        if confirm_steps:
            show_pdf_check_report(title, report)
        print("Detailed preflight PDF check passed.")
        return

    add_issue(issue_report, "PDF detailed preflight check", report)
    manual_required = [item for item in problems if item["status"] == "error"]
    repairable = [item for item in problems if item["status"] == "warning"]

    if manual_required:
        manual_report = pdf_validation.summarize_check_results(manual_required, "手動対応が必要なPDF")
        print(manual_report)
        show_pdf_check_report("事前詳細チェック結果", report + "\n\n" + manual_report)
        raise RuntimeError("詳細チェックで手動対応が必要なPDFが見つかりました。")

    if repairable and repair_warnings:
        repair_results, error_files_dir = pdf_validation.repair_problem_source_pdfs(
            repairable,
            source_folder_path,
            output_file_path,
        )
        repair_report = pdf_validation.summarize_repair_results(
            repair_results,
            error_files_dir,
        )
        print(repair_report)
        failed = [item for item in repair_results if item["status"] == "failed"]
        repaired = [item for item in repair_results if item["status"] == "repaired"]
        post_report = ""
        if repaired:
            post_results = pdf_validation.check_folder_pdfs(source_folder_path, detailed=True)
            post_report = pdf_validation.summarize_check_results(post_results, "修復後の事前詳細チェック結果")
            print(post_report)
        combined_report = report + "\n\n" + repair_report
        if post_report:
            combined_report += "\n\n" + post_report
        if confirm_steps:
            show_pdf_check_report("事前詳細チェック・修復結果", combined_report)
        if failed:
            add_issue(issue_report, "Source PDF repair failed", repair_report)
            print("Some source PDF warnings could not be repaired. Continuing with the original PDFs.")
        if repaired:
            raise SourcePdfRepairedRetry(
                "Source PDFs were repaired. Rebuilding merged PDF.",
                source_folder_path,
            )
    if repairable:
        print("Source PDF warnings were found, but source repair is enabled only in compress mode.")
        if confirm_steps:
            show_pdf_check_report(title, report)


def save_final_pdf(
    pdf_document,
    output_file_path,
    save_options,
    source_folder_path=None,
    confirm_save_warnings=False,
    issue_report=None,
):
    output_dir = os.path.dirname(os.path.abspath(output_file_path)) or "."
    candidate_path = None
    auto_clean_on_warning = bool(save_options.get("auto_clean_on_warning", True))

    try:
        with tempfile.NamedTemporaryFile(
            prefix="kojiPDF_final_",
            suffix=".pdf",
            dir=output_dir,
            delete=False,
        ) as candidate_file:
            candidate_path = candidate_file.name

        warnings = save_pdf_collecting_mupdf_warnings(
            pdf_document,
            candidate_path,
            dict(save_options),
        )

        should_retry_clean = False
        if warnings and not confirm_save_warnings:
            add_issue(issue_report, "MuPDF save warning", warnings)
            print("MuPDF warnings were detected during final save.")
            print(warnings)
            if auto_clean_on_warning:
                print("Step confirm is off, so a clean save will be tried automatically.")
                should_retry_clean = True
            else:
                print("Automatic clean save is off for this save mode. Using the normally saved merged PDF.")

        while warnings and confirm_save_warnings:
            add_issue(issue_report, "MuPDF save warning", warnings)
            action = choose_save_warning_action(warnings)
            if action == "abort":
                raise RuntimeError("PDF保存時の警告により処理を終了しました。")
            if action == "repair":
                should_retry_clean = True
                break
            elif action == "ignore":
                print("MuPDF warning was ignored. Using the normally saved merged PDF.")
                break

        if should_retry_clean:
            os.remove(candidate_path)
            with tempfile.NamedTemporaryFile(
                prefix="kojiPDF_final_clean_",
                suffix=".pdf",
                dir=output_dir,
                delete=False,
            ) as candidate_file:
                candidate_path = candidate_file.name

            clean_save_options = dict(save_options)
            clean_save_options["garbage"] = max(int(clean_save_options.get("garbage", 0)), 4)
            clean_save_options["clean"] = True
            print("最終PDFを修復保存しています。大きいPDFでは数分かかることがあります。")
            clean_warnings = save_pdf_collecting_mupdf_warnings(
                pdf_document,
                candidate_path,
                clean_save_options,
            )
            if clean_warnings:
                add_issue(issue_report, "MuPDF clean-save warning", clean_warnings)
                print("MuPDF warnings remained after clean save.")

        replace_final_pdf_with_retry(candidate_path, output_file_path)
        candidate_path = None
    except FinalPdfReplaceError:
        candidate_path = None
        raise
    finally:
        if candidate_path and os.path.exists(candidate_path):
            os.remove(candidate_path)


def create_pdf(
    folder_path,
    output_file_path,
    add_bookmark_page_number,
    add_page,
    exist_w_e_file,
    confirm_temp_folder_delete,
    ppt_slide_bookmarks,
    convert_mail,
    eml_encoding,
    resize_pdf,
    resize_size,
    preflight_detail_repair,
    preflight_confirm,
    save_options,
    add_pdf_page_numbers,
    page_number_options,
    xratio,
    yratio,
    bookmark_view_mode,
    base_view_width_mm,
    base_view_height_mm,
    expand_all,
    collapse_level,
    asper_format,
    keep_pdf_extension,
    issue_report=None,
):
    print(f"選択されたフォルダ: {folder_path}")
    ensure_output_file_writable(output_file_path)

    if exist_w_e_file:
        print("OfficeファイルをPDFに変換するため、一時フォルダへコピーしています。")
        folder_path = office_temp_convert.copy_all_folders_to_temp(
            folder_path,
            output_file_path,
            ppt_slide_bookmarks,
            convert_mail,
            eml_encoding=eml_encoding,
            issue_report=issue_report,
        )

    repair_source_warnings = is_smaller_file_save_mode(save_options)
    if preflight_detail_repair:
        run_detail_preflight_repair(
            folder_path,
            output_file_path,
            confirm_steps=preflight_confirm,
            repair_warnings=repair_source_warnings,
            issue_report=issue_report,
        )
    else:
        run_fast_preflight_check(
            folder_path,
            output_file_path,
            confirm_problems=preflight_confirm,
            repair_warnings=repair_source_warnings,
            issue_report=issue_report,
        )

    print("フォルダー構造を解析しています。")
    df, max_levels = tree_data.build_tree_data(folder_path)

    if asper_format:
        print("電脳ASPer向けにしおり名を調整しています。")
        df = asper_bookmarks.modify_pdf_names_in_all_columns(df)

    print("しおり順とページ位置を計算しています。")
    df = tree_data_cleanup.prepare_treedata_for_merge(df)

    print("PDFファイルを結合しています。")
    output_pdf = pdf_merge.merge_pdfs_from_df(df, issue_report=issue_report)
    output_pdf = pdf_resize.normalize_file_links_as_uri_doc(output_pdf)
    if output_pdf.page_count == 0:
        raise RuntimeError(
            "結合できるPDFがありません。メール、ZIP、Officeファイルなどの変換に失敗していないか、"
            "エラーレポートを確認してください。"
        )

    if resize_pdf:
        print(f"PDFページを{resize_size}サイズに変更しています。")
        output_pdf = pdf_resize.resize_doc_auto_orientation(output_pdf, size=resize_size)

    if add_pdf_page_numbers:
        print("結合PDFの各ページにページ番号を追加しています。")
        output_pdf = pdf_page_numbers.add_page_numbers_to_doc(
            output_pdf,
            **page_number_options,
        )

    print("親しおりを追加しています。")
    toc_dict = source_bookmarks.get_each_pdf_toc(df)

    if not keep_pdf_extension:
        df = tree_data_cleanup.remove_pdf_extensions_from_level_titles(df)
        toc_dict = tree_data_cleanup.remove_pdf_extensions_from_toc_keys(toc_dict)

    output_pdf = bookmark_builder.add_bookmarks_to_pdf(df, max_levels, output_pdf)

    print("結合前PDFが持つしおりを取得しています。")

    print("結合前PDFのしおりを子しおりとして追加しています。")
    output_pdf = child_bookmarks.add_children_to_existing_toc(output_pdf, toc_dict)

    if asper_format:
        print("電脳ASPer向けにしおり名を最終調整しています。")
        output_pdf = asper_bookmarks.last_bookmarks_rename(output_pdf)

    print("しおり名末尾の古いページ番号を整理しています。")
    if add_bookmark_page_number or add_page:
        print("しおり名にページ番号または含まれるページ数を付け直しています。")
    output_pdf = bookmark_page_counts.add_numbers_to_bookmarks(
        output_pdf,
        add_bookmark_page_number=add_bookmark_page_number,
        add_included_page_count=add_page,
    )

    temp_output_path = output_file_path[:-4] + "temp.PDF"
    print("一時PDFを保存しています。")
    output_pdf.save(temp_output_path)
    output_pdf.close()

    print("一時PDFを開き直しています。")
    output_pdf = fitz_open(temp_output_path)

    print("しおりのクリック位置、ズーム倍率、展開階層を設定しています。")
    toc_collapse_level = 99 if expand_all else collapse_level
    output_pdf = bookmark_links.set_newtoc(
        output_pdf,
        xratio,
        yratio,
        toc_collapse_level,
        base_view_width_mm,
        base_view_height_mm,
        bookmark_view_mode=bookmark_view_mode,
        apply_asper_bookmark_colors=asper_format,
    )
    output_pdf = bookmark_links.apply_bookmark_view_mode(output_pdf, bookmark_view_mode)

    print("最終PDFを保存しています。")
    print("最終PDFを一時ファイルに保存中です。大きいPDFでは数分かかることがあります。")
    ensure_output_file_writable(output_file_path)
    output_pdf.xref_set_key(output_pdf.pdf_catalog(), "PageMode", "/UseOutlines")
    output_pdf = bookmark_links.apply_open_view_mode(output_pdf, bookmark_view_mode)
    try:
        save_final_pdf(
            output_pdf,
            output_file_path,
            save_options,
            source_folder_path=folder_path,
            confirm_save_warnings=preflight_confirm,
            issue_report=issue_report,
        )
        output_pdf.close()
    except SourcePdfRepairedRetry:
        output_pdf.close()
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        raise

    print("一時PDFを削除しています。")
    os.remove(temp_output_path)

    if exist_w_e_file:
        should_delete_folder = True
        if confirm_temp_folder_delete:
            should_delete_folder = confirmation_dialog.main(f"{folder_path}を削除します。\nよろしいですか。")
        if should_delete_folder:
            delete_temp_folder_best_effort(folder_path, issue_report)
        else:
            print(f"フォルダ削除をキャンセルしました: {folder_path}")

    print(f"PDF作成が完了しました: {output_file_path}")


def run_create_pdf_in_worker(progress_ui, create_pdf_args, worker_options=None):
    result = {"success": False, "error": None, "issue_count": 0, "report_path": None}
    worker_options = worker_options or {}

    def worker():
        original_stdout = sys.stdout
        sys.stdout = gui.ProgressWriter(progress_ui, original_stdout)
        issue_report = create_pdf_args[-1] if create_pdf_args else None
        output_file_path = create_pdf_args[1] if len(create_pdf_args) > 1 else None
        write_error_report_enabled = bool(worker_options.get("write_error_report", True))
        open_output_pdf_enabled = bool(worker_options.get("open_output_pdf", False))
        try:
            current_create_pdf_args = list(create_pdf_args)
            retry_count = 0
            while True:
                try:
                    create_pdf(*current_create_pdf_args)
                    break
                except SourcePdfRepairedRetry as exc:
                    retry_count += 1
                    if retry_count > 3:
                        raise RuntimeError(
                            "Source PDF repair requested rebuild repeatedly. Stopped to avoid an endless retry."
                        ) from exc
                    current_create_pdf_args[0] = exc.repaired_folder_path
                    current_create_pdf_args[4] = False
                    print(str(exc))
                    print(f"Restarting PDF merge from repaired folder: {exc.repaired_folder_path}")
            if (
                retry_count
                and create_pdf_args[4]
                and current_create_pdf_args[0] != create_pdf_args[0]
                and os.path.isdir(current_create_pdf_args[0])
            ):
                should_delete_folder = True
                if create_pdf_args[5]:
                    should_delete_folder = confirmation_dialog.main(
                        f"{current_create_pdf_args[0]}を削除します。\nよろしいですか。"
                    )
                if should_delete_folder:
                    delete_temp_folder_best_effort(current_create_pdf_args[0], issue_report)
            if open_output_pdf_enabled:
                open_output_pdf_file(output_file_path, issue_report)
            result["success"] = True
        except Exception as exc:
            result["error"] = exc
            error_message = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            long_path_hint = long_path_hint_from_exception(exc)
            if long_path_hint:
                error_message += "\n\n" + long_path_hint
            add_issue(issue_report, "Processing error", error_message)
            print("処理中にエラーが発生しました。")
            traceback.print_exc()
        finally:
            if output_file_path and write_error_report_enabled:
                try:
                    result["report_path"] = write_issue_report(output_file_path, issue_report)
                except Exception as report_exc:
                    print(f"エラー一覧の保存に失敗しました: {report_exc}")
            result["issue_count"] = len(issue_report) if issue_report else 0
            sys.stdout = original_stdout

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    if progress_ui is not None:
        progress_ui.wait_for_worker(worker_thread)
    else:
        worker_thread.join()
    return result


def wait_for_viewer_close(progress_ui):
    """Keep the shared Qt process alive while the integrated viewer is open."""
    if progress_ui is None or not progress_ui.viewer_launcher.is_open:
        return
    from PySide6.QtCore import QEventLoop

    viewer_loop = QEventLoop()
    progress_ui.viewer_launcher.viewer_closed.connect(viewer_loop.quit)
    if progress_ui.viewer_launcher.is_open:
        viewer_loop.exec()


def main():
    launch_config = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        startup_log(f"Launch config argument received: {config_path}")
        try:
            launch_config = launch_config_loader.load_launch_config(config_path)
        except launch_config_loader.LaunchConfigError as exc:
            startup_log(f"Launch config error: {exc}")
            print(str(exc))
            sys.exit(1)

    (
        folder_path,
        output_file_path,
        add_bookmark_page_number,
        add_page,
        exist_w_e_file,
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
        xratio,
        yratio,
        scale_enabled,
        bookmark_view_mode,
        base_view_width_mm,
        base_view_height_mm,
        expand_all,
        collapse_level,
        progress_ui,
    ) = gui.select_folder_and_file(launch_config)

    if folder_path is None or output_file_path is None:
        print("キャンセルされたため、処理を中断します。")
        wait_for_viewer_close(progress_ui)
        sys.exit(1)

    if not scale_enabled:
        xratio = 1.0
        yratio = 1.0
        base_view_width_mm = 330
        base_view_height_mm = 210

    create_pdf_args = (
        folder_path,
        output_file_path,
        add_bookmark_page_number,
        add_page,
        exist_w_e_file,
        confirm_temp_folder_delete,
        ppt_slide_bookmarks,
        convert_mail,
        eml_encoding,
        resize_pdf,
        resize_size,
        preflight_detail_repair,
        preflight_confirm,
        save_options,
        add_pdf_page_numbers,
        page_number_options,
        xratio,
        yratio,
        bookmark_view_mode,
        base_view_width_mm,
        base_view_height_mm,
        expand_all,
        collapse_level,
        asper_format,
        keep_pdf_extension,
        [],
    )
    worker_options = {
        "write_error_report": True,
        "open_output_pdf": False,
    }
    if launch_config is not None:
        worker_options.update(
            {
                "write_error_report": launch_config.write_error_report,
                "open_output_pdf": launch_config.open_output_pdf,
            }
        )

    if progress_ui is not None:
        qt_dialogs.set_bridge(progress_ui.dialog_bridge)

    while True:
        if progress_ui is not None:
            progress_ui.retry_requested = False

        result = run_create_pdf_in_worker(progress_ui, create_pdf_args, worker_options)

        if progress_ui is None:
            break

        progress_ui.finish_progress(result["success"])
        if result["error"] is not None:
            progress_ui.show_error_message(str(result["error"]))

        if result["success"]:
            exited = progress_ui.confirm_exit_after_completion(
                result.get("issue_count", 0),
                result.get("report_path"),
            )
            if not exited:
                progress_ui.wait_for_action()
            break

        progress_ui.wait_for_action()
        if not progress_ui.retry_requested:
            break

    qt_dialogs.set_bridge(None)

    wait_for_viewer_close(progress_ui)


if __name__ == "__main__":
    main()
