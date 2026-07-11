import os
import tempfile

from fitz import Document, EmptyFileError, FileDataError, TOOLS


def _run_with_mupdf_messages_hidden(callback):
    TOOLS.reset_mupdf_warnings()
    TOOLS.mupdf_display_errors(False)
    TOOLS.mupdf_display_warnings(False)
    try:
        result = callback()
        return result, TOOLS.mupdf_warnings()
    finally:
        TOOLS.mupdf_display_errors(True)
        TOOLS.mupdf_display_warnings(True)


def _validate_pdf(full_path, detailed=True):
    with Document(full_path) as pdf:
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDF")
        if pdf.page_count <= 0:
            raise ValueError("PDF has no pages")

        if not detailed:
            pdf.load_page(0)
            return

        scratch = Document()
        try:
            pdf.get_toc(simple=False)
            for page_index in range(pdf.page_count):
                page = pdf.load_page(page_index)
                page.get_text("text")
                page.get_links()
                annotations = page.annots()
                if annotations is not None:
                    for annotation in annotations:
                        annotation.info
                scratch.insert_pdf(pdf, from_page=page_index, to_page=page_index)
        finally:
            scratch.close()


def find_invalid_pdfs_with_errors(folder_path):
    """
    Return PDFs that cannot be safely opened, read page-by-page, and inserted.
    """
    invalid_files = []

    for full_path in iter_pdf_paths(folder_path):
        if not os.path.isfile(full_path):
            invalid_files.append((full_path, "Not a file"))
        elif os.path.getsize(full_path) == 0:
            invalid_files.append((full_path, "File size is 0"))
        else:
            try:
                _run_with_mupdf_messages_hidden(lambda: _validate_pdf(full_path))
            except EmptyFileError as e:
                invalid_files.append((full_path, f"EmptyFileError: {str(e)}"))
            except FileDataError as e:
                invalid_files.append((full_path, f"FileDataError: {str(e)}"))
            except Exception as e:
                invalid_files.append((full_path, f"Other error: {str(e)}"))

    return invalid_files


def iter_pdf_paths(folder_path):
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [
            directory
            for directory in dirs
            if directory.lower() != "error_files"
        ]
        for file in files:
            file_lower = file.lower()
            if (
                file_lower.endswith(".pdf")
                and not file_lower.endswith("temp.pdf")
                and not file_lower.startswith("kojipdf_final_")
                and not file_lower.startswith("kojipdf_final_clean_")
            ):
                yield os.path.join(root, file)


def check_pdf(full_path, detailed=False):
    if not os.path.isfile(full_path):
        return {
            "path": full_path,
            "status": "error",
            "message": "Not a file",
            "warnings": "",
        }
    if os.path.getsize(full_path) == 0:
        return {
            "path": full_path,
            "status": "error",
            "message": "File size is 0",
            "warnings": "",
        }

    try:
        _, warnings = _run_with_mupdf_messages_hidden(
            lambda: _validate_pdf(full_path, detailed=detailed)
        )
    except EmptyFileError as e:
        return {"path": full_path, "status": "error", "message": f"EmptyFileError: {e}", "warnings": ""}
    except FileDataError as e:
        return {"path": full_path, "status": "error", "message": f"FileDataError: {e}", "warnings": ""}
    except Exception as e:
        return {"path": full_path, "status": "error", "message": f"Other error: {e}", "warnings": ""}

    return {
        "path": full_path,
        "status": "warning" if warnings else "ok",
        "message": "MuPDF warnings" if warnings else "OK",
        "warnings": warnings,
    }


def check_folder_pdfs(folder_path, detailed=False):
    results = []
    for full_path in iter_pdf_paths(folder_path):
        results.append(check_pdf(full_path, detailed=detailed))
    return results


def problem_results(results):
    return [
        item
        for item in results
        if item["status"] in {"warning", "error"}
    ]


def _unique_path(path):
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    index = 2
    while True:
        candidate = f"{base}_{index}{ext}"
        if not os.path.exists(candidate):
            return candidate
        index += 1


def _backup_path_for_source(source_path, source_folder_path, error_files_dir):
    try:
        relative_path = os.path.relpath(source_path, source_folder_path)
    except ValueError:
        relative_path = os.path.basename(source_path)

    backup_path = os.path.join(error_files_dir, relative_path)
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    return _unique_path(backup_path)


def repair_source_pdf(source_path, source_folder_path, error_files_dir):
    output_dir = os.path.dirname(os.path.abspath(source_path)) or "."
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix="kojiPDF_repaired_source_",
            suffix=".pdf",
            dir=output_dir,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name

        def save_repaired():
            with Document(source_path) as pdf:
                if pdf.is_encrypted:
                    raise ValueError("Encrypted PDF")
                if pdf.page_count <= 0:
                    raise ValueError("PDF has no pages")
                pdf.save(temp_path, garbage=4, clean=True, deflate=True)

        _run_with_mupdf_messages_hidden(save_repaired)

        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise ValueError("Repair output is empty")

        post_repair_check = check_pdf(temp_path, detailed=True)
        if post_repair_check["status"] != "ok":
            raise ValueError(
                "Repair output still has problems: "
                f"{post_repair_check['message']}"
            )

        backup_path = _backup_path_for_source(source_path, source_folder_path, error_files_dir)
        os.replace(source_path, backup_path)
        os.replace(temp_path, source_path)
        temp_path = None
        return {
            "path": source_path,
            "status": "repaired",
            "backup_path": backup_path,
            "message": "Repaired source PDF",
        }
    except Exception as e:
        return {
            "path": source_path,
            "status": "failed",
            "backup_path": "",
            "message": f"Repair failed: {e}",
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def repair_problem_source_pdfs(results, source_folder_path, output_file_path):
    output_dir = os.path.dirname(os.path.abspath(output_file_path)) or "."
    error_files_dir = os.path.join(output_dir, "error_files")
    repair_results = []

    for item in problem_results(results):
        repair_results.append(
            repair_source_pdf(
                item["path"],
                source_folder_path,
                error_files_dir,
            )
        )

    return repair_results, error_files_dir


def summarize_repair_results(repair_results, error_files_dir):
    repaired = [item for item in repair_results if item["status"] == "repaired"]
    failed = [item for item in repair_results if item["status"] == "failed"]

    lines = [
        "Source PDF repair result",
        f"Original error file folder: {error_files_dir}",
        f"Repaired: {len(repaired)}",
        f"Repair failed: {len(failed)}",
    ]

    if repair_results:
        lines.append("")
        lines.append("Files:")
        for item in repair_results[:80]:
            lines.append(f"- {item['path']}")
            lines.append(f"  {item['message']}")
            if item["backup_path"]:
                lines.append(f"  Original moved to: {item['backup_path']}")
        if len(repair_results) > 80:
            lines.append(f"... and {len(repair_results) - 80} more files")

    return "\n".join(lines)


def summarize_check_results(results, title):
    total = len(results)
    warnings = [item for item in results if item["status"] == "warning"]
    errors = [item for item in results if item["status"] == "error"]

    lines = [
        title,
        f"Checked PDFs: {total}",
        f"Warnings: {len(warnings)}",
        f"Errors: {len(errors)}",
    ]

    problem_items = warnings + errors
    if problem_items:
        lines.append("")
        lines.append("Problem files:")
        for item in problem_items[:80]:
            lines.append(f"- {item['path']}")
            lines.append(f"  {item['message']}")
            if item["status"] == "warning":
                lines.append("  action: 自動修復対象")
                lines.append("  backup: 修復に成功した場合、元PDFを error_files に退避します")
            else:
                lines.append("  action: 手動対応対象")
                lines.append("  backup: error_files には退避しません")
            if item.get("warnings"):
                warning_lines = item["warnings"].strip().splitlines()
                for warning_line in warning_lines[:5]:
                    lines.append(f"  warning: {warning_line}")
                if len(warning_lines) > 5:
                    lines.append(f"  ... {len(warning_lines) - 5} more warning lines")
        if len(problem_items) > 80:
            lines.append(f"... and {len(problem_items) - 80} more files")

    return "\n".join(lines)


if __name__ == "__main__":
    folder_path = r"F:\backup_data\sample"

    if not os.path.isdir(folder_path):
        print("Input folder does not exist.")
    else:
        invalids = find_invalid_pdfs_with_errors(folder_path)
        if invalids:
            print("\nInvalid PDF files:")
            for path, msg in invalids:
                print(f" - {path} -> {msg}")
        else:
            print("All PDF files are readable.")
