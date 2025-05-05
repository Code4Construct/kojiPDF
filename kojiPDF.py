import os
import sys
import shutil
from fitz import open as fitz_open  # PyMuPDF のみ必要
import m01make_treedata as m01
import m02merge_from_treedata as m02
import m03make_bookmark as m03
import m04file_name_replace as m04
import m05select_folder as m05
import m06finish_message as m06
import m10set_newtoc as m10
import m11add_number_bookmarks as m11
import m12last_bookmarks_rename as m12
import m21get_eachPDF_toc as m21
import m22add_child_toc as m22
import m44temp_convert as m44
import m45invalid_pdflist as m45
# ユーザーにフォルダを選択させる
folder_path ,output_file_path, add_page ,exist_w_e_file,xratio,yratio,scale_enabled= m05.select_folder_and_file()
if folder_path is None or output_file_path is None:
    print("キャンセルされたため処理を中断します。")
    sys.exit(1)  # 終了コード1（異常終了）
print(f"選択されたフォルダ: {folder_path}")

if exist_w_e_file:
    folder_path = m44.copy_all_folders_to_temp(folder_path, output_file_path)

invalids = m45.find_invalid_pdfs_with_errors(folder_path)
if invalids:
    result = "❌ 問題のあるPDFファイル一覧:\n"
    for path, msg in invalids:
        result += f" - {path} → {msg}\n"
        result += "問題のあるファイルを削除してからやり直してください。"
        m06.main(result)
else:
    print("✅ すべてのPDFファイルは正常に読み込めます。")

# m01からデータを作成し、フォルダ構造を分解し、フォルダ階層ごとに列を追加する
print("フォルダーの構造を分析しています。")
df, max_levels = m01.main(folder_path)

# データの各カラムのファイル名の変更とページ数をカウントしてDataFrameに格納する
print("ソートを行うためにしおり名の変更を行っています。")
df=m04.modify_pdf_names_in_all_columns(df)

# Excelファイルに保存
#df.to_excel('Treedata.xlsx', index=False)

# PDFをマージ
print("PDFファイルを結合しています。")
output_pdf = m02.merge_pdfs_from_df(df)

# マージしたPDFにブックマークを追加する
print("しおりを追加しています。")
output_pdf = m03.add_bookmarks_to_pdf(df, max_levels, output_pdf)

# 結合前PDFでしおりを持つものpage,tiltle,TOCを辞書で取得しています。
print("結合前PDFでしおりを持つものpage,tiltle,TOCを辞書で取得しています。")
toc_dict=m21.get_each_pdf_toc(df)

#結合後のしおりに結合前のしおりを追加したいます。
print("結合後のしおりに結合前のしおりを追加したいます。")
output_pdf = m22.add_children_to_existing_toc(output_pdf, toc_dict)
print("しおり名の最終調整をしています。")
output_pdf = m12.last_bookmarks_rename(output_pdf)
# ボタンがチェックされていれば、ブックマークの文字列の最後にページ数を追加する。
if add_page:
    print("各しおり名に含まれるページ数を追記しています。")
    output_pdf = m11.add_page_number_to_bookmarks(output_pdf)
print("一時ファイルを保存しています。")
output_pdf.save(output_file_path[:-4]+"temp.PDF")
output_pdf.close()
print("一時ファイルを開いています。")
output_pdf = fitz_open(output_file_path[:-4]+"temp.PDF")
print("しおりにスタイルを追加し、クリックしたときの位置とサイズの最適化しています。")
output_pdf=m10.set_newtoc(output_pdf,xratio,yratio)
print("最終ファイルを保存しています。")
output_pdf.save(output_file_path)
output_pdf.close()
print("一時ファイルを削除しています。")
os.remove(output_file_path[:-4]+"temp.PDF")  
if exist_w_e_file:
    m06.main(f'{folder_path}を削除しますよ。\n本当にいいですか。')
    shutil.rmtree(folder_path)
