import os
import shutil
from pathlib import Path
from datetime import datetime
import m06finish_message as m06
import m43infolder_w_e2pdf as m43
import m48mail_to_pdf as mail_exporter
import m49image_to_pdf as image_converter
import m50text_to_pdf as text_converter
import m51zip_extract as zip_extractor

MAX_ARCHIVE_MAIL_EXPANSION_PASSES = 3
IGNORED_UNCONVERTED_EXTENSIONS = {".ini", ".db", ".tmp"}


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


def path_key(path):
    return str(Path(path).resolve()).lower()


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


def collect_unconverted_files(temp_folder_path, source_folder_path=None):
    temp_folder_path = Path(temp_folder_path)
    source_folder_path = Path(source_folder_path) if source_folder_path else None
    unconverted_files = []

    for file_path in sorted(path for path in temp_folder_path.rglob("*") if path.is_file()):
        if any(part.lower() == "error_files" for part in file_path.parts):
            continue
        suffix = file_path.suffix.lower()
        if suffix == ".pdf" or suffix in IGNORED_UNCONVERTED_EXTENSIONS:
            continue
        if has_converted_pdf(file_path):
            continue

        item = {"work_path": file_path}
        if source_folder_path is not None:
            original_path = original_path_for_temp_file(file_path, temp_folder_path, source_folder_path)
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


def expand_mails_once(folder_path, failed_paths, eml_encoding="auto", issue_report=None):
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
    if msg_files:
        try:
            outlook = mail_exporter.create_outlook_application()
        except Exception as exc:
            for msg_file in msg_files:
                failed_paths.add(path_key(msg_file))
                message = f"メール展開失敗: {msg_file} -> {exc}"
                print(message)
                add_issue(issue_report, "Mail conversion error", message)
            mail_files = [path for path in mail_files if path.suffix.lower() != ".msg"]
            if not mail_files:
                return 0, len(msg_files)

    success_count = 0
    try:
        for mail_file in mail_files:
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
            if result.success:
                success_count += 1
                print(f"メール展開完了: {result.output}")
                result.source.unlink(missing_ok=True)
                continue

            failed_paths.add(path_key(mail_file))
            message = f"メール展開失敗: {result.source} -> {result.error}"
            print(message)
            add_issue(issue_report, "Mail conversion error", message)
    finally:
        if outlook is not None:
            mail_exporter.release_com_object(outlook)
            mail_exporter.uninitialize_com()

    return success_count, len(mail_files)


def expand_archives_and_mails(folder_path, eml_encoding="auto", issue_report=None, max_passes=MAX_ARCHIVE_MAIL_EXPANSION_PASSES):
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

    # folder_path 配下の構造を再帰的に temp_folder_path にコピー
    for root, dirs, files in os.walk(folder_path):
        # temp_folder 自身への再帰コピーを防止する
        dirs[:] = [
            directory
            for directory in dirs
            if os.path.abspath(os.path.join(root, directory)) != os.path.abspath(temp_folder_path)
        ]

        # 現在の root から folder_path までの相対パスを取得
        relative_path = os.path.relpath(root, folder_path)
        # 対象のコピー先パスを作成
        target_dir = os.path.join(temp_folder_path, relative_path)
        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_dir, file)
            shutil.copy2(src_file, dst_file)

    if convert_mail:
        expand_archives_and_mails(
            temp_folder_path,
            eml_encoding=eml_encoding,
            issue_report=issue_report,
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
    folder_path = r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー"  # コピー元フォルダ
    file_path = r"C:\Users\uboni\Desktop\test.txt"  # テンポラリーフォルダ（固定）

    temp_path = copy_all_folders_to_temp(folder_path, file_path)
    print(f"テンポラリーフォルダのパス: {temp_path}")





