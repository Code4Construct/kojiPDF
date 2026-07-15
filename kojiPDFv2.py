import os
import shutil
import sys
import tempfile
import threading
import traceback
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext


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
import m05select_folder as gui
import m06finish_message as confirmation_dialog
import m10set_newtoc as bookmark_links
import m11add_number_bookmarks as bookmark_page_counts
import m14asper_format as asper_bookmarks
import m15bookmark_title_cleanup as bookmark_cleanup
import m21get_eachPDF_toc as source_bookmarks
import m22add_child_toc as child_bookmarks
import m44temp_convert as office_temp_convert
import m45invalid_pdflist as pdf_validation
import m46pdf_resize as pdf_resize
import m47add_pagenum as pdf_page_numbers


class SourcePdfRepairedRetry(Exception):
    def __init__(self, message, repaired_folder_path):
        super().__init__(message)
        self.repaired_folder_path = repaired_folder_path


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


def save_pdf_collecting_mupdf_warnings(pdf_document, output_file_path, save_options):
    TOOLS.reset_mupdf_warnings()
    TOOLS.mupdf_display_errors(False)
    TOOLS.mupdf_display_warnings(False)
    try:
        pdf_document.save(output_file_path, **save_options)
        return TOOLS.mupdf_warnings()
    finally:
        TOOLS.mupdf_display_errors(True)
        TOOLS.mupdf_display_warnings(True)


def choose_save_warning_action(warnings):
    actions = [
        ("repair", "修復: garbage4", "#1976D2"),
        ("ignore", "無視: 続行", "#388E3C"),
        ("abort", "終了", "#D32F2F"),
    ]
    selected = {"action": "abort"}

    def select_action(action):
        selected["action"] = action
        root.quit()
        root.destroy()

    root = tk.Tk()
    root.title("PDF保存エラーの処理")
    root.geometry("940x390")
    root.protocol("WM_DELETE_WINDOW", lambda: select_action("abort"))

    message = (
        "PDF保存時にMuPDF警告が検出されました。\n"
        "修復は結合後PDFを garbage4 で保存し直します。\n"
        "大容量PDFでは修復に非常に時間がかかるため、通常保存PDFで続行する選択も検討してください。"
    )
    tk.Label(
        root,
        text=message,
        font=("Yu Gothic UI", 11),
        justify="left",
        anchor="w",
        wraplength=880,
    ).pack(fill="x", padx=18, pady=(16, 8))

    warning_text = scrolledtext.ScrolledText(root, height=6, font=("Consolas", 9), wrap=tk.WORD)
    warning_text.insert("1.0", warnings or "MuPDF warning details were empty.")
    warning_text.configure(state="disabled")
    warning_text.pack(fill="both", expand=True, padx=18, pady=(0, 10))

    button_frame = tk.Frame(root)
    button_frame.pack(fill="x", padx=18, pady=(0, 16))
    for action, text, color in actions:
        button = tk.Button(
            button_frame,
            text=text,
            font=("Yu Gothic UI", 10, "bold"),
            bg=color,
            fg="white",
            command=lambda value=action: select_action(value),
            relief="raised",
            bd=3,
            padx=8,
            pady=8,
        )
        button.pack(side=tk.LEFT, padx=4, expand=True, fill="x")

    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))
    root.mainloop()
    return selected["action"]


def show_pdf_check_report(title, report, actions=None):
    actions = actions or [("ok", "OK", "#263849")]
    selected = {"action": actions[0][0]}

    def select_action(action):
        selected["action"] = action
        root.quit()
        root.destroy()

    root = tk.Tk()
    root.title(title)
    root.geometry("940x560")
    report_text = scrolledtext.ScrolledText(root, font=("Consolas", 10), wrap=tk.WORD)
    report_text.insert("1.0", report)
    report_text.configure(state="disabled")
    report_text.pack(fill="both", expand=True, padx=12, pady=(12, 8))
    button_frame = tk.Frame(root)
    button_frame.pack(fill="x", padx=12, pady=(0, 12))
    for action, text, color in actions:
        tk.Button(
            button_frame,
            text=text,
            font=("Yu Gothic UI", 11, "bold"),
            bg=color,
            fg="white",
            command=lambda value=action: select_action(value),
            padx=16,
            pady=7,
        ).pack(side=tk.LEFT, padx=6, expand=True, fill="x")
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))
    root.mainloop()
    return selected["action"]


def run_fast_preflight_check(source_folder_path, output_file_path, confirm_problems=False):
    title = "高速な結合前チェック結果"
    print("Fast preflight PDF check started.")
    results = pdf_validation.check_folder_pdfs(source_folder_path, detailed=False)
    problems = pdf_validation.problem_results(results)
    if not problems:
        print("Fast preflight PDF check passed.")
        return

    report = pdf_validation.summarize_check_results(results, title)
    print(report)
    errors = [item for item in problems if item["status"] == "error"]
    repairable = [item for item in problems if item["status"] == "warning"]
    if errors:
        show_pdf_check_report(
            title,
            report + "\n\n手動対応が必要なPDFがあります。処理を終了します。",
        )
        raise RuntimeError("高速な結合前チェックでエラーが見つかったため処理を終了しました。")

    if repairable:
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
        if confirm_problems or failed:
            show_pdf_check_report("高速チェック・修復結果", combined_report)
        if failed:
            raise RuntimeError("高速チェックで自動修復できないPDFがありました。手動対応してください。")
        if repaired:
            print("Fast preflight PDF warnings were repaired. Continuing.")
        return

    action = show_pdf_check_report(
        title,
        report
        + "\n\n対象ファイルを削除・差し替え・修復してからやり直すことを推奨します。"
        + "\n削除・差し替え等の対応が済んでいる場合のみ続行してください。",
        actions=[
            ("abort", "終了", "#D32F2F"),
            ("continue", "続行（削除等の対応済み）", "#388E3C"),
        ],
    )
    if action != "continue":
        raise RuntimeError("高速な結合前チェックで問題が見つかったため処理を終了しました。")
    print("Continuing after fast preflight PDF check problems by user choice.")


def run_detail_preflight_repair(source_folder_path, output_file_path, confirm_steps=False):
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

    manual_required = [item for item in problems if item["status"] == "error"]
    repairable = [item for item in problems if item["status"] == "warning"]

    if manual_required:
        manual_report = pdf_validation.summarize_check_results(manual_required, "手動対応が必要なPDF")
        print(manual_report)
        show_pdf_check_report("事前詳細チェック結果", report + "\n\n" + manual_report)
        raise RuntimeError("詳細チェックで手動対応が必要なPDFが見つかりました。")

    if repairable:
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
        if confirm_steps or failed:
            show_pdf_check_report("事前詳細チェック・修復結果", combined_report)
        if failed:
            raise RuntimeError("自動修復できないPDFがありました。手動対応してください。")
        if repaired:
            raise SourcePdfRepairedRetry(
                "Source PDFs were repaired. Rebuilding merged PDF.",
                source_folder_path,
            )


def save_final_pdf(
    pdf_document,
    output_file_path,
    save_options,
    source_folder_path=None,
    confirm_save_warnings=False,
):
    output_dir = os.path.dirname(os.path.abspath(output_file_path)) or "."
    candidate_path = None

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
            print("MuPDF warnings were detected during final save.")
            print("Step confirm is off, so a clean save will be tried automatically.")
            print(warnings)
            should_retry_clean = True

        while warnings and confirm_save_warnings:
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
            clean_warnings = save_pdf_collecting_mupdf_warnings(
                pdf_document,
                candidate_path,
                clean_save_options,
            )
            if clean_warnings:
                print("MuPDF warnings remained after clean save.")

        os.replace(candidate_path, output_file_path)
        candidate_path = None
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
    resize_pdf,
    resize_size,
    preflight_detail_repair,
    preflight_confirm,
    save_options,
    add_pdf_page_numbers,
    page_number_options,
    xratio,
    yratio,
    base_view_width_mm,
    base_view_height_mm,
    expand_all,
    collapse_level,
    asper_format,
    keep_pdf_extension,
):
    print(f"選択されたフォルダ: {folder_path}")
    ensure_output_file_writable(output_file_path)

    if exist_w_e_file:
        print("OfficeファイルをPDFに変換するため、一時フォルダへコピーしています。")
        folder_path = office_temp_convert.copy_all_folders_to_temp(
            folder_path,
            output_file_path,
            ppt_slide_bookmarks,
        )

    if preflight_detail_repair:
        run_detail_preflight_repair(
            folder_path,
            output_file_path,
            confirm_steps=preflight_confirm,
        )
    else:
        run_fast_preflight_check(
            folder_path,
            output_file_path,
            confirm_problems=preflight_confirm,
        )

    print("フォルダー構造を解析しています。")
    df, max_levels = tree_data.build_tree_data(folder_path)

    if asper_format:
        print("電脳ASPer向けにしおり名を調整しています。")
        df = asper_bookmarks.modify_pdf_names_in_all_columns(df)

    print("しおり順とページ位置を計算しています。")
    df = tree_data_cleanup.prepare_treedata_for_merge(df)

    print("PDFファイルを結合しています。")
    output_pdf = pdf_merge.merge_pdfs_from_df(df)

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
    output_pdf = bookmark_builder.add_bookmarks_to_pdf(df, max_levels, output_pdf)

    print("結合前PDFが持つしおりを取得しています。")
    toc_dict = source_bookmarks.get_each_pdf_toc(df)

    print("結合前PDFのしおりを子しおりとして追加しています。")
    output_pdf = child_bookmarks.add_children_to_existing_toc(output_pdf, toc_dict)

    if asper_format:
        print("電脳ASPer向けにしおり名を最終調整しています。")
        output_pdf = asper_bookmarks.last_bookmarks_rename(output_pdf)

    if add_bookmark_page_number or add_page:
        print("しおり名にページ番号または含まれるページ数を追記しています。")
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
        apply_asper_bookmark_colors=asper_format,
    )

    if not keep_pdf_extension:
        print("しおり名の末尾にある.pdfを削除しています。")
        output_pdf = bookmark_cleanup.remove_pdf_extension_from_bookmarks(output_pdf, collapse=toc_collapse_level)

    print("最終PDFを保存しています。")
    ensure_output_file_writable(output_file_path)
    output_pdf.xref_set_key(output_pdf.pdf_catalog(), "PageMode", "/UseOutlines")
    try:
        save_final_pdf(
            output_pdf,
            output_file_path,
            save_options,
            source_folder_path=folder_path,
            confirm_save_warnings=preflight_confirm,
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
            shutil.rmtree(ensure_safe_temp_folder_delete_path(folder_path))
        else:
            print(f"フォルダ削除をキャンセルしました: {folder_path}")

    print(f"PDF作成が完了しました: {output_file_path}")


def run_create_pdf_in_worker(progress_ui, create_pdf_args):
    result = {"success": False, "error": None}

    def worker():
        original_stdout = sys.stdout
        sys.stdout = gui.ProgressWriter(progress_ui, original_stdout)
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
                    shutil.rmtree(ensure_safe_temp_folder_delete_path(current_create_pdf_args[0]))
            result["success"] = True
        except Exception as exc:
            result["error"] = exc
            print("処理中にエラーが発生しました。")
            traceback.print_exc()
        finally:
            sys.stdout = original_stdout

    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()

    if progress_ui is not None:
        def stop_when_done():
            if worker_thread.is_alive():
                progress_ui.window.after(100, stop_when_done)
            else:
                progress_ui.window.quit()

        progress_ui.window.after(100, stop_when_done)
        progress_ui.window.mainloop()

    worker_thread.join()
    return result


def main():
    (
        folder_path,
        output_file_path,
        add_bookmark_page_number,
        add_page,
        exist_w_e_file,
        confirm_temp_folder_delete,
        ppt_slide_bookmarks,
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
        base_view_width_mm,
        base_view_height_mm,
        expand_all,
        collapse_level,
        progress_ui,
    ) = gui.select_folder_and_file()

    if folder_path is None or output_file_path is None:
        print("キャンセルされたため、処理を中断します。")
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
        resize_pdf,
        resize_size,
        preflight_detail_repair,
        preflight_confirm,
        save_options,
        add_pdf_page_numbers,
        page_number_options,
        xratio,
        yratio,
        base_view_width_mm,
        base_view_height_mm,
        expand_all,
        collapse_level,
        asper_format,
        keep_pdf_extension,
    )

    while True:
        if progress_ui is not None:
            progress_ui.retry_requested = False

        result = run_create_pdf_in_worker(progress_ui, create_pdf_args)

        if progress_ui is None:
            break

        progress_ui.finish_progress(result["success"])
        if result["error"] is not None:
            progress_ui.show_error_message(str(result["error"]))

        if result["success"]:
            exited = progress_ui.confirm_exit_after_completion()
            if not exited:
                progress_ui.window.mainloop()
            break

        progress_ui.window.mainloop()
        if not progress_ui.retry_requested:
            break


if __name__ == "__main__":
    main()
