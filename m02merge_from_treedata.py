import os

from fitz import Document


def merge_pdfs_from_df(df, issue_report=None):
    """
    Merge PDF files listed in the tree rows into one in-memory PDF document.
    """
    output_pdf = Document()
    paths = [row.get("Full Path") for row in df]
    print(f"　{len(paths)} のPDFファイルを結合しています。")

    for path in paths:
        if (
            isinstance(path, str)
            and os.path.isfile(path)
            and path.lower().endswith(".pdf")
            and os.path.getsize(path) > 0
        ):
            try:
                with Document(path) as pdf:
                    output_pdf.insert_pdf(pdf)
            except Exception as e:
                message = f"PDF読み込み失敗: {path} -> {e}"
                print(f"⚠ エラー: {message}")
                if issue_report is not None:
                    issue_report.append({"category": "PDF merge error", "message": message})
        else:
            message = f"PDFスキップ: {path}（存在しない・PDFでない・空ファイル）"
            print(f"⚠ スキップ: {message}")
            if issue_report is not None:
                issue_report.append({"category": "PDF merge warning", "message": message})

    return output_pdf


if __name__ == "__main__":
    import m01make_treedata as tree_data

    df, _ = tree_data.build_tree_data(".")
    output_pdf = merge_pdfs_from_df(df)
    output_pdf.save("merged_output.pdf")
    output_pdf.close()
