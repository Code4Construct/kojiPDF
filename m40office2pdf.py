import os
import tempfile
import fitz  # PyMuPDF

WORD_EXTENSIONS = {'.doc', '.docx', '.docm'}
EXCEL_EXTENSIONS = {'.xls', '.xlsx', '.xlsm'}
POWERPOINT_EXTENSIONS = {'.ppt', '.pptx', '.pptm'}
SUPPORTED_OFFICE_EXTENSIONS = WORD_EXTENSIONS | EXCEL_EXTENSIONS | POWERPOINT_EXTENSIONS


def convert_word_to_pdf(input_path, output_path):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        doc = word.Documents.Open(os.path.abspath(input_path))
        doc.SaveAs(os.path.abspath(output_path), FileFormat=17)  # 17 = PDF
        doc.Close()
    except Exception as e:
        print(f"Word変換エラー: {e}")
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
        excel = win32com.client.Dispatch("Excel.Application")
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
                print(f"エクスポート失敗: {sheet_name}, エラー: {e}")  # エクスポート失敗した場合のエラーメッセージ

        wb.Close(False)
        merge_pdfs_with_bookmarks(temp_files, output_path, add_bookmarks=add_sheet_bookmarks)
    except Exception as e:
        print(f"Excel変換エラー: {e}")
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
        print(f"PowerPoint変換エラー: {e}")
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
        print("指定されたファイルが存在しません。")
        return

    filename, ext = os.path.splitext(input_path)
    output_path = filename + ".pdf"

    try:
        ext = ext.lower()
        if ext in WORD_EXTENSIONS:
            convert_word_to_pdf(input_path, output_path)
        elif ext in EXCEL_EXTENSIONS:
            convert_excel_to_pdf_with_bookmarks(input_path, output_path)
        elif ext in POWERPOINT_EXTENSIONS:
            convert_pptx_to_pdf(input_path, output_path, ppt_slide_bookmarks)
        else:
            print("対応していないファイル形式です。（対応形式: .doc, .docx, .xls, .xlsx, .ppt, .pptx）")
            return

        print(f"変換が完了しました: {output_path}")
    except Exception as e:
        print(f"変換中にエラーが発生しました: {e}")

# スクリプトとして使用する例
if __name__ == "__main__":
    convert_to_pdf(r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー\令和７年度第１回庶務担当課長会資料\04想定外の事案発生時対応について\要領の概略.pptx")
