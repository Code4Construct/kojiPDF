import fitz
from fitz import open as fitz_open  # PyMuPDF のみ必要
from pandas import read_excel  # pandas のみ必要
#import m07make_toc as m07
#import m08get_Po_Zs as m08

def add_bookmarks_to_pdf(df, N, pdf_document):
    last_bookmarks = [None] * N  # 各レベルの直前のしおりのタイトルを保持するリスト
    for _, row in df.iterrows():
        page_count = row.get('Page Count', 0)
        page_all = row.get('Page All', None)
        levels = [row.get(f'Level {i + 1}', "") for i in range(N)]
        #print(f'levels: {levels}')

        if page_count != 0 and page_all is not None:
            page_index = int(page_all)
            preleveladd = False
            if 0 <= page_index < len(pdf_document):
                for level, text in enumerate(levels, start=1):
                    if (preleveladd or text != last_bookmarks[level - 1]) and str(text) not in ('None', ''):
                        pdf_document.set_toc(pdf_document.get_toc() + [(level, str(text), page_index + 1, 0)])
                        last_bookmarks[level - 1] = text
                        #print(f"Added level{level} bookmark: '{text}' on page {page_index + 1}")
                        preleveladd = True
                    else:
                        #print(f"Skipping level{level} bookmark: {text}")
                        preleveladd = False
            else:
                #print(f"Skipping bookmark for page {page_index + 1}: Out of range")
                continue
    
    return pdf_document





if __name__ == '__main__':
    excel_path = "Treedata.xlsx"
    pdf_path1 = "merged_output.pdf"
    pdf_path2 = "bookmarked_output.pdf"
    df = read_excel(excel_path, sheet_name=0)
    pdf_document = fitz_open(pdf_path1)
    N = 3
    add_bookmarks_to_pdf(df, N, pdf_document, pdf_path2)
