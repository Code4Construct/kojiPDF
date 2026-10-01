import os
import tempfile
import time
import fitz  # PyMuPDF

WORD_EXTENSIONS = {'.doc', '.docx', '.docm'}
EXCEL_EXTENSIONS = {'.xls', '.xlsx', '.xlsm'}
POWERPOINT_EXTENSIONS = {'.ppt', '.pptx', '.pptm'}
SUPPORTED_OFFICE_EXTENSIONS = WORD_EXTENSIONS | EXCEL_EXTENSIONS | POWERPOINT_EXTENSIONS

OFFICE_COM_RETRY_DELAYS = (3, 8, 15)
TRANSIENT_COM_HRESULTS = {-2147418111, -2147417846, -2147023170}


def find_hresult(exc):
    hresult = getattr(exc, "hresult", None)
    if isinstance(hresult, int):
        return hresult
    for value in getattr(exc, "args", ()):
        if isinstance(value, int) and value < 0:
            return value
        if isinstance(value, (tuple, list)):
            for nested in value:
                if isinstance(nested, int) and nested < 0:
                    return nested
    return None


class OfficeOperationError(RuntimeError):
    def __init__(self, app_name, input_path, stage, cause):
        self.app_name = app_name
        self.input_path = input_path
        self.stage = stage
        self.cause = cause
        self.hresult = find_hresult(cause)
        super().__init__(str(cause))


class OfficeConversionError(RuntimeError):
    def __init__(self, error, attempts):
        self.error = error
        self.attempts = attempts
        super().__init__(format_conversion_error(error, attempts))


def format_conversion_error(error, attempts):
    details = str(vars(error))
    return f"{details}; attempts: {attempts}"


def run_with_com_retry(operation):
    attempts = 0
    for delay in (*OFFICE_COM_RETRY_DELAYS, None):
        attempts += 1
        try:
            return operation()
        except OfficeOperationError as error:
            if delay is None or error.hresult not in TRANSIENT_COM_HRESULTS:
                raise OfficeConversionError(error, attempts) from error
            time.sleep(delay)


def office_not_available_message(app_name, input_path, error):
    return (
        f"{app_name} is required to convert this Office file to PDF: {input_path}\n"
        f"Please make sure {app_name} is installed and can be opened normally on this PC.\n"
        f"Details: {error}"
    )


def convert_word_to_pdf(input_path, output_path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        doc = word.Documents.Open(os.path.abspath(input_path))
        doc.SaveAs(os.path.abspath(output_path), FileFormat=17)  # 17 = PDF
        doc.Close()
    except Exception as e:
        raise OfficeOperationError("Microsoft Word", input_path, "convert document", e) from e
    finally:
        if word:
            word.Quit()
            del word
        pythoncom.CoUninitialize()

def convert_excel_to_pdf_with_bookmarks(input_path, output_path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    excel = None
    try:
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.DisplayAlerts = False
        excel.Visible = False
        wb = excel.Workbooks.Open(os.path.abspath(input_path))
        temp_files = []
        visible_sheets = [sheet for sheet in wb.Sheets if sheet.Visible == -1]
        add_sheet_bookmarks = len(visible_sheets) >= 2

        for i, sheet in enumerate(visible_sheets):
            sheet_name = sheet.Name
            temp_pdf_path = os.path.join(tempfile.gettempdir(), f"{sheet_name}_{i}.pdf")

            #print(f"Exporting: {temp_pdf_path}")  # どのシートをエクスポートするか確認

            try:
                sheet.ExportAsFixedFormat(0, temp_pdf_path)  # エクスポート
                temp_files.append((sheet_name, temp_pdf_path))  # エクスポート成功したらリストに追加
            except Exception as e:
                raise OfficeOperationError("Microsoft Excel", input_path, f"export worksheet: {sheet_name}", e) from e

        wb.Close(False)
        merge_pdfs_with_bookmarks(temp_files, output_path, add_bookmarks=add_sheet_bookmarks)
    except OfficeOperationError:
        raise
    except Exception as e:
        raise OfficeOperationError("Microsoft Excel", input_path, "convert workbook", e) from e
    finally:
        if excel:
            excel.Quit()
            del excel
        pythoncom.CoUninitialize()

def remove_pdf_bookmarks(pdf_path):
    temp_path = pdf_path + ".no_bookmarks.pdf"
    doc = fitz.open(pdf_path)
    try:
        doc.set_toc([])
        doc.save(temp_path)
    finally:
        doc.close()
    os.replace(temp_path, pdf_path)


def convert_pptx_to_pdf(input_path, output_path, ppt_slide_bookmarks=True):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    ppt_app = None
    try:
        ppt_app = win32com.client.DispatchEx("PowerPoint.Application")
        ppt_app.Visible = True  # False にすると不具合の報告あり
        presentation = ppt_app.Presentations.Open(os.path.abspath(input_path), WithWindow=False)
        presentation.SaveAs(os.path.abspath(output_path), 32)  # 32 = PDF format
        presentation.Close()
        if not ppt_slide_bookmarks:
            remove_pdf_bookmarks(output_path)
    except Exception as e:
        raise OfficeOperationError("Microsoft PowerPoint", input_path, "convert presentation", e) from e
    finally:
        if ppt_app:
            ppt_app.Quit()
            del ppt_app
        pythoncom.CoUninitialize()

def merge_pdfs_with_bookmarks(temp_files, output_path, add_bookmarks=True):
    merged_pdf = fitz.open()
    page_index = 0
    toc = []

    for name, pdf_path in temp_files:
        pdf = fitz.open(pdf_path)
        merged_pdf.insert_pdf(pdf)
        if add_bookmarks:
            toc.append([1, name, page_index + 1])
        page_index += pdf.page_count
        pdf.close()

    if add_bookmarks:
        merged_pdf.set_toc(toc)
    merged_pdf.save(output_path)
    merged_pdf.close()

    for _, f in temp_files:
        try:
            os.remove(f)
        except:
            pass

def convert_to_pdf(input_path, ppt_slide_bookmarks=True):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Office file does not exist: {input_path}")

    filename, ext = os.path.splitext(input_path)
    output_path = filename + ".pdf"

    try:
        ext = ext.lower()
        if ext in WORD_EXTENSIONS:
            run_with_com_retry(lambda: convert_word_to_pdf(input_path, output_path))
        elif ext in EXCEL_EXTENSIONS:
            run_with_com_retry(lambda: convert_excel_to_pdf_with_bookmarks(input_path, output_path))
        elif ext in POWERPOINT_EXTENSIONS:
            run_with_com_retry(lambda: convert_pptx_to_pdf(input_path, output_path, ppt_slide_bookmarks))
        else:
            print("対応していないファイル形式です。（対応形式: .doc, .docx, .xls, .xlsx, .ppt, .pptx）")
            return

        print(f"変換が完了しました: {output_path}")
    except Exception:
        raise

# スクリプトとして使用する例
if __name__ == "__main__":
    convert_to_pdf(r"C:\SampleData\OfficeFiles\presentation.pptx")
