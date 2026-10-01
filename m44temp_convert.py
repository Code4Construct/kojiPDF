import os
import shutil
import time
from pathlib import Path
from datetime import datetime
import m06finish_message as m06
import m43infolder_w_e2pdf as m43
import m48mail_to_pdf as mail_exporter
import m49image_to_pdf as image_converter
import m50text_to_pdf as text_converter
import m51zip_extract as zip_extractor
import m53path_display_map as display_names

MAX_ARCHIVE_MAIL_EXPANSION_PASSES = 3
IGNORED_UNCONVERTED_EXTENSIONS = {".ini", ".db", ".tmp"}
OFFICE_TEMP_EXTENSIONS = {".doc", ".docx", ".docm", ".xls", ".xlsx", ".xlsm", ".ppt", ".pptx", ".pptm"}


def is_office_temp_file(path):
    path = Path(path)
    return path.name.startswith("~$") and path.suffix.lower() in OFFICE_TEMP_EXTENSIONS


def short_directory_name(index):
    return f"d{index:05d}"


def short_file_name(index, suffix):
    return f"f{index:05d}{suffix.lower()}"


def add_issue(issue_report, category, message):
    if issue_report is None:
        return
    issue_report.append(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "message": message,
        }
    )


def path_length_diagnosis(*paths):
    lines = []
    long_path_found = False
    for label, path in paths:
        path_text = str(path)
        path_length = len(path_text)
        lines.append(f"{label} path length: {path_length}")
        lines.append(f"{label}: {path_text}")
        if os.name == "nt" and path_length >= 240:
            long_path_found = True

    if long_path_found:
        lines.extend(
            [
                "Long path warning: one or more paths are close to or over the traditional Windows 260 character limit.",
                "This file may be visible in Explorer or open in Office, but Python copy operations can still fail.",
            ]
        )
    return "\n".join(lines)


def path_key(path):
    return str(Path(path).resolve()).lower()


def unlink_with_retry(path, attempts=5, delay_seconds=0.5):
    path = Path(path)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            path.unlink(missing_ok=True)
            return True, None, attempt
        except (PermissionError, OSError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(delay_seconds)
    return False, last_error, attempts


def display_path_for_work_file(work_path, temp_folder_path, source_folder_path=None):
    work_path = Path(work_path)
    temp_folder_path = Path(temp_folder_path)
    try:
        relative_path = work_path.relative_to(temp_folder_path)
    except ValueError:
        return str(work_path)

    display_map = display_names.load_display_map(temp_folder_path)
    display_relative = display_names.mapped_relative_path(relative_path, display_map) if display_map else relative_path
    if source_folder_path is not None:
        return str(Path(source_folder_path) / display_relative)
    return str(display_relative)


def expected_pdf_path(source_path):
    return Path(source_path).with_suffix(".pdf")


def has_converted_pdf(source_path):
    pdf_path = expected_pdf_path(source_path)
    return pdf_path.exists() and pdf_path.stat().st_size > 0


def original_path_for_temp_file(temp_file, temp_folder_path, source_folder_path):
    try:
        relative_path = Path(temp_file).relative_to(temp_folder_path)
    except ValueError:
        return None

    original_path = Path(source_folder_path) / relative_path
    return original_path if original_path.exists() else None



def is_converted_mail_body_html(file_path):
    try:
        return (
            file_path.name == mail_exporter.BODY_HTML_NAME
            and (file_path.parent / mail_exporter.BODY_PDF_NAME).exists()
        )
    except Exception:
        return False
def collect_unconverted_files(temp_folder_path, source_folder_path=None):
    temp_folder_path = Path(temp_folder_path)
    source_folder_path = Path(source_folder_path) if source_folder_path else None
    display_map = display_names.load_display_map(temp_folder_path)
    unconverted_files = []

    for file_path in sorted(path for path in temp_folder_path.rglob("*") if path.is_file()):
        if any(part.lower() == "error_files" for part in file_path.parts):
            continue
        if file_path.name == display_names.MAP_FILE_NAME:
            continue
        if is_office_temp_file(file_path):
            continue
        suffix = file_path.suffix.lower()
        if suffix == ".pdf" or suffix in IGNORED_UNCONVERTED_EXTENSIONS:
            continue
        if is_converted_mail_body_html(file_path):
            continue
        if has_converted_pdf(file_path):
            continue

        item = {"work_path": file_path}
        if source_folder_path is not None:
            original_path = original_path_for_temp_file(file_path, temp_folder_path, source_folder_path)
            if original_path is None and display_map:
                relative_path = file_path.relative_to(temp_folder_path)
                original_path = source_folder_path / display_names.mapped_relative_path(relative_path, display_map)
            if original_path is not None:
                item["original_path"] = original_path
        unconverted_files.append(item)

    return unconverted_files


def report_unconverted_files(temp_folder_path, source_folder_path=None, issue_report=None):
    unconverted_files = collect_unconverted_files(temp_folder_path, source_folder_path)
    if not unconverted_files:
        return

    lines = [
        "PDFに変換されなかったファイルがあります。",
        "同じ場所に同名PDFが作成されていないPDF以外のファイルを表示しています。",
        "",
    ]
    for index, item in enumerate(unconverted_files, start=1):
        lines.append(f"{index}. {item['work_path']}")
        if "original_path" in item:
            lines.append(f"   original: {item['original_path']}")

    message = "\n".join(lines)
    print(message)
    add_issue(issue_report, "Unconverted file list", message)


def expand_zips_once(folder_path, failed_paths, issue_report=None):
    zip_files = sorted(
        path
        for path in Path(folder_path).rglob("*")
        if path.is_file()
        and path.suffix.lower() in zip_extractor.SUPPORTED_ZIP_EXTENSIONS
        and path_key(path) not in failed_paths
    )

    success_count = 0
    for zip_file in zip_files:
        print(f"ZIP展開処理: {zip_file}")
        result = zip_extractor.extract_zip_file(zip_file)
        if result.success:
            success_count += 1
            print(f"ZIP展開完了: {result.output}")
            continue

        failed_paths.add(path_key(zip_file))
        message = f"ZIPファイルの展開に失敗しました: {result.source} -> {result.error}"
        print(message)
        add_issue(issue_report, "Zip extraction error", message)

    return success_count, len(zip_files)


def expand_mails_once(folder_path, failed_paths, eml_encoding="auto", issue_report=None, source_folder_path=None):
    folder_path = Path(folder_path)
    mail_files = sorted(
        path
        for path in folder_path.rglob("*")
        if path.is_file()
        and path.suffix.lower() in mail_exporter.MAIL_FILE_SUFFIXES
        and path_key(path) not in failed_paths
    )

    if not mail_files:
        return 0, 0

    msg_files = [path for path in mail_files if path.suffix.lower() == ".msg"]
    outlook = None
    if msg_files and mail_exporter.any_msg_file_requires_outlook(msg_files):
        try:
            outlook = mail_exporter.create_outlook_application()
        except Exception as exc:
            for msg_file in msg_files:
                failed_paths.add(path_key(msg_file))
                original_mail_path = display_path_for_work_file(msg_file, folder_path, source_folder_path)
                message = f"メール展開失敗: {msg_file}; 元メール: {original_mail_path} -> {exc}"
                print(message)
                add_issue(issue_report, "Mail conversion error", message)
            mail_files = [path for path in mail_files if path.suffix.lower() != ".msg"]
            if not mail_files:
                return 0, len(msg_files)

    success_count = 0
    try:
        for mail_file in mail_files:
            original_mail_path = display_path_for_work_file(mail_file, folder_path, source_folder_path)
            try:
                relative_parent = mail_file.parent.relative_to(folder_path)
            except ValueError:
                relative_parent = Path()

            mail_destination = folder_path / relative_parent
            mail_destination.mkdir(parents=True, exist_ok=True)
            result = mail_exporter.export_mail_file(
                mail_file,
                mail_destination,
                outlook=outlook,
                eml_encoding=eml_encoding,
            )
            time.sleep(mail_exporter.MAIL_EXPORT_COOLDOWN_SECONDS)
            for warning in getattr(result, "warnings", ()):
                category = warning.get("category", "Mail conversion warning")
                warning_message = warning.get("message", "")
                print(warning_message)
                add_issue(
                    issue_report,
                    category,
                    f"{warning_message}\nwork file: {result.source}; original mail: {original_mail_path}",
                )
            if result.success:
                success_count += 1
                print(f"Mail expansion complete: {result.output}")
                print(f"Original mail: {original_mail_path}")
                cleanup_ok, cleanup_error, cleanup_attempts = unlink_with_retry(result.source)
                if not cleanup_ok:
                    failed_paths.add(path_key(result.source))
                    message = (
                        "Mail expansion completed, but the temporary work mail could not be deleted "
                        "because it is still in use. Processing will continue. "
                        f"work file: {result.source}; original mail: {original_mail_path}; "
                        f"cleanup attempts: {cleanup_attempts} -> {cleanup_error}"
                    )
                    print(message)
                    add_issue(issue_report, "Mail source delete skipped", message)
                continue

            failed_paths.add(path_key(mail_file))
            message = f"Mail expansion failed: {result.source}; original mail: {original_mail_path} -> {result.error}"
            print(message)
            add_issue(issue_report, "Mail conversion error", message)
    finally:
        if outlook is not None:
            mail_exporter.release_com_object(outlook)
            mail_exporter.uninitialize_com()

    return success_count, len(mail_files)


def expand_archives_and_mails(folder_path, eml_encoding="auto", issue_report=None, max_passes=MAX_ARCHIVE_MAIL_EXPANSION_PASSES, source_folder_path=None):
    failed_paths = set()
    folder_path = Path(folder_path)

    for pass_index in range(1, max_passes + 1):
        print(f"ZIP/メール展開処理 {pass_index}/{max_passes} を開始します。")
        zip_success_count, zip_target_count = expand_zips_once(folder_path, failed_paths, issue_report=issue_report)
        mail_success_count, mail_target_count = expand_mails_once(
            folder_path,
            failed_paths,
            eml_encoding=eml_encoding,
            issue_report=issue_report,
            source_folder_path=source_folder_path,
        )

        print(
            "ZIP/メール展開処理 "
            f"{pass_index}/{max_passes}: ZIP {zip_success_count}/{zip_target_count} 件, "
            f"メール {mail_success_count}/{mail_target_count} 件"
        )
        if zip_target_count == 0 and mail_target_count == 0:
            print("新しいZIP/メールが見つからないため、展開処理を終了します。")
            break
        if zip_success_count == 0 and mail_success_count == 0:
            print("新しく展開できたZIP/メールがないため、展開処理を終了します。")
            break
    else:
        remaining_files = sorted(
            path
            for path in folder_path.rglob("*")
            if path.is_file()
            and (
                path.suffix.lower() in zip_extractor.SUPPORTED_ZIP_EXTENSIONS
                or path.suffix.lower() in mail_exporter.MAIL_FILE_SUFFIXES
            )
            and path_key(path) not in failed_paths
        )
        if remaining_files:
            message = (
                f"ZIP/メール展開処理が最大回数 {max_passes} 回に達しました。"
                f"未処理ファイル {len(remaining_files)} 件が残っています。"
            )
            print(message)
            add_issue(issue_report, "Archive/mail expansion limit", message)


def copy_all_folders_to_temp(
    folder_path,
    file_path,
    ppt_slide_bookmarks=True,
    convert_mail=False,
    eml_encoding="auto",
    issue_report=None,
):
    #file_path の親フォルダをtemp_folder_pathに指定
    pfile_path = Path(file_path)
    print(f"フォルダのパス: {pfile_path.parent}")
    temp_folder_path = str(pfile_path.parent / "temp_folder")
    # temp_folder_path が既に存在する場合は削除
    if os.path.exists(temp_folder_path):
        m06.main(f'暫定フォルダの{temp_folder_path}が既に存在します。\n上書きして続けてよいですか。')
        shutil.rmtree(temp_folder_path)
    os.makedirs(temp_folder_path)

    display_map = {}
    folder_map = {os.path.abspath(folder_path): ""}
    directory_index = 1
    file_index = 1

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [
            directory
            for directory in sorted(dirs)
            if os.path.abspath(os.path.join(root, directory)) != os.path.abspath(temp_folder_path)
        ]
        files = sorted(files)

        root_key = os.path.abspath(root)
        target_relative = folder_map.get(root_key)
        if target_relative is None:
            dirs[:] = []
            continue

        target_dir = os.path.join(temp_folder_path, target_relative)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as exc:
            message = (
                f"Folder copy skipped: {root} -> {target_dir}\n"
                f"{type(exc).__name__}: {exc}\n"
                + path_length_diagnosis(("source folder", root), ("destination folder", target_dir))
            )
            print(message)
            add_issue(issue_report, "Folder copy skipped", message)
            dirs[:] = []
            continue

        kept_dirs = []
        for directory in dirs:
            src_dir = os.path.join(root, directory)
            short_name = short_directory_name(directory_index)
            directory_index += 1
            child_relative = display_names.normalize_relative_path(Path(target_relative) / short_name)
            folder_map[os.path.abspath(src_dir)] = child_relative
            display_map[child_relative] = directory
            kept_dirs.append(directory)
        dirs[:] = kept_dirs

        for file in files:
            src_file = os.path.join(root, file)
            if is_office_temp_file(src_file):
                print(f"Office temporary file skipped: {src_file}")
                continue

            suffix = Path(file).suffix
            short_name = short_file_name(file_index, suffix)
            file_index += 1
            dst_file = os.path.join(target_dir, short_name)
            relative_file = display_names.normalize_relative_path(Path(target_relative) / short_name)
            display_map[relative_file] = file
            try:
                shutil.copy2(src_file, dst_file)
            except (FileNotFoundError, OSError) as exc:
                message = (
                    f"File copy skipped: {src_file} -> {dst_file}\n"
                    f"{type(exc).__name__}: {exc}\n"
                    + path_length_diagnosis(("source", src_file), ("destination", dst_file))
                )
                print(message)
                add_issue(issue_report, "File copy skipped", message)

    display_names.save_display_map(temp_folder_path, display_map)

    if convert_mail:
        expand_archives_and_mails(
            temp_folder_path,
            eml_encoding=eml_encoding,
            issue_report=issue_report,
            source_folder_path=folder_path,
        )

    # PDF変換処理
    m43.convert_all_files_to_pdf(temp_folder_path, ppt_slide_bookmarks, issue_report=issue_report)
    image_converter.convert_all_images_to_pdf(temp_folder_path, issue_report=issue_report)
    text_converter.convert_all_texts_to_pdf(temp_folder_path, issue_report=issue_report)
    report_unconverted_files(temp_folder_path, folder_path, issue_report=issue_report)
    print("PDF変換処理が完了しました。")

    return temp_folder_path

# 使用例
if __name__ == "__main__":
    folder_path = r"C:\SampleData\OfficeFiles"  # コピー元フォルダ
    file_path = r"C:\Users\SampleUser\Desktop\test.txt"  # テンポラリーフォルダ（固定）

    temp_path = copy_all_folders_to_temp(folder_path, file_path)
    print(f"テンポラリーフォルダのパス: {temp_path}")





