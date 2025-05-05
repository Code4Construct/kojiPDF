import os
import tempfile
import win32com.client
import pythoncom
import fitz  # PyMuPDF

def convert_word_to_pdf(input_path, output_path):
    pythoncom.CoInitialize()
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
        word.Quit()
        del word
        pythoncom.CoUninitialize()

def convert_excel_to_pdf_with_bookmarks(input_path, output_path):
    pythoncom.CoInitialize()
    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.DisplayAlerts = False
        excel.Visible = False
        wb = excel.Workbooks.Open(os.path.abspath(input_path))
        temp_files = []

        for i, sheet in enumerate(wb.Sheets):
            sheet_name = sheet.Name
            temp_pdf_path = os.path.join(tempfile.gettempdir(), f"{sheet_name}_{i}.pdf")

            #print(f"Exporting: {temp_pdf_path}")  # どのシートをエクスポートするか確認

            try:
                sheet.ExportAsFixedFormat(0, temp_pdf_path)  # エクスポート
                temp_files.append((sheet_name, temp_pdf_path))  # エクスポート成功したらリストに追加
            except Exception as e:
                print(f"エクスポート失敗: {sheet_name}, エラー: {e}")  # エクスポート失敗した場合のエラーメッセージ

        wb.Close(False)
        merge_pdfs_with_bookmarks(temp_files, output_path)
    except Exception as e:
        print(f"Excel変換エラー: {e}")
    finally:
        excel.Quit()
        del excel
        pythoncom.CoUninitialize()

def convert_pptx_to_pdf(input_path, output_path):
    pythoncom.CoInitialize()
    ppt_app = None
    try:
        ppt_app = win32com.client.DispatchEx("PowerPoint.Application")
        ppt_app.Visible = True  # False にすると不具合の報告あり
        presentation = ppt_app.Presentations.Open(os.path.abspath(input_path), WithWindow=False)
        presentation.SaveAs(os.path.abspath(output_path), 32)  # 32 = PDF format
        presentation.Close()
    except Exception as e:
        print(f"PowerPoint変換エラー: {e}")
    finally:
        if ppt_app:
            ppt_app.Quit()
            del ppt_app
        pythoncom.CoUninitialize()

def merge_pdfs_with_bookmarks(temp_files, output_path):
    merged_pdf = fitz.open()
    page_index = 0
    toc = []

    for name, pdf_path in temp_files:
        pdf = fitz.open(pdf_path)
        merged_pdf.insert_pdf(pdf)
        toc.append([1, name, page_index + 1])
        page_index += pdf.page_count
        pdf.close()

    merged_pdf.set_toc(toc)
    merged_pdf.save(output_path)
    merged_pdf.close()

    for _, f in temp_files:
        try:
            os.remove(f)
        except:
            pass

def convert_to_pdf(input_path):
    if not os.path.isfile(input_path):
        print("指定されたファイルが存在しません。")
        return

    filename, ext = os.path.splitext(input_path)
    output_path = filename + ".pdf"

    try:
        ext = ext.lower()
        if ext in ['.doc', '.docx']:
            convert_word_to_pdf(input_path, output_path)
        elif ext in ['.xls', '.xlsx']:
            convert_excel_to_pdf_with_bookmarks(input_path, output_path)
        elif ext in ['.ppt', '.pptx']:
            convert_pptx_to_pdf(input_path, output_path)
        else:
            print("対応していないファイル形式です。（対応形式: .doc, .docx, .xls, .xlsx, .ppt, .pptx）")
            return

        print(f"変換が完了しました: {output_path}")
    except Exception as e:
        print(f"変換中にエラーが発生しました: {e}")

# スクリプトとして使用する例
if __name__ == "__main__":
    convert_to_pdf(r"F:\01HIROTAKAのデータ\仕事\20250415庶務担当課長会資料 - コピー\令和７年度第１回庶務担当課長会資料\04想定外の事案発生時対応について\要領の概略.pptx")
