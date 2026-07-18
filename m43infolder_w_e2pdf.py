import os
import time

import m40office2pdf as m40
import m41each_file_pathlist as m41


def convert_all_files_to_pdf(folder_path, ppt_slide_bookmarks=True, issue_report=None):
    """Convert supported Office files under the folder to PDF."""
    file_list = m41.list_all_files(folder_path)

    for file_path in file_list:
        if os.path.splitext(file_path)[1].lower() not in m40.SUPPORTED_OFFICE_EXTENSIONS:
            continue
        print(f"Converting Office file: {file_path}")
        m40.convert_to_pdf(file_path, ppt_slide_bookmarks)
        output_path = os.path.splitext(file_path)[0] + ".pdf"
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
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


if __name__ == "__main__":
    convert_all_files_to_pdf(
        r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー"
    )
