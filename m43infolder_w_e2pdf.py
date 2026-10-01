import os
import time

import m40office2pdf as m40
import m41each_file_pathlist as m41
import m53path_display_map as display_names


def is_office_temp_file(file_path):
    name = os.path.basename(file_path)
    extension = os.path.splitext(file_path)[1].lower()
    return name.startswith("~$") and extension in m40.SUPPORTED_OFFICE_EXTENSIONS


def convert_all_files_to_pdf(folder_path, ppt_slide_bookmarks=True, issue_report=None):
    """Convert supported Office files under the folder to PDF."""
    file_list = m41.list_all_files(folder_path)
    display_map = display_names.load_display_map(folder_path)

    for file_path in file_list:
        if os.path.splitext(file_path)[1].lower() not in m40.SUPPORTED_OFFICE_EXTENSIONS:
            continue
        if is_office_temp_file(file_path):
            print(f"Office temporary file skipped: {file_path}")
            continue
        print(f"Converting Office file: {file_path}")
        output_path = os.path.splitext(file_path)[0] + ".pdf"
        conversion_error = None
        try:
            m40.convert_to_pdf(file_path, ppt_slide_bookmarks)
        except Exception as exc:
            conversion_error = exc
            message = f"Office conversion failed: {file_path}\n{type(exc).__name__}: {exc}"
            print(message)
            if issue_report is not None:
                issue_report.append({"category": "Office conversion error", "message": message})
        if conversion_error is None and (not os.path.exists(output_path) or os.path.getsize(output_path) == 0):
            message = f"OfficeファイルのPDF変換に失敗しました: {file_path}"
            print(message)
            if issue_report is not None:
                issue_report.append(
                    {
                        "category": "Office conversion error",
                        "message": message,
                    }
                )
        time.sleep(1)
        if conversion_error is None and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            try:
                source_relative = os.path.relpath(file_path, folder_path)
                output_relative = os.path.relpath(output_path, folder_path)
                display_names.map_pdf_sidecar_name(output_relative, source_relative, display_map)
                display_names.save_display_map(folder_path, display_map)
            except ValueError:
                pass


if __name__ == "__main__":
    convert_all_files_to_pdf(
        r"C:\SampleData\OfficeFiles"
    )
