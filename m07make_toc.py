import fitz  # PyMuPDF

def make_newentry(entry, Po_Z,Bfont):
    """
    各しおりエントリにリンク情報を追加する。

    Args:
        entry (list): しおりのエントリ [レベル, タイトル, ページ番号]。
        Po_Z (tuple): (x座標, y座標, ズーム) のタプル。

    Returns:
        str: しおりエントリにリンク情報を追加したJSON風の文字列。
    """
    return str(entry)[:-1]+ ",{\"kind\": fitz.LINK_GOTO, \"page\": "+str(entry[2])+", \"to\": fitz.Point("+str(Po_Z[0])+","+str(Po_Z[1])+"), \"zoom\": "+str(Po_Z[2])+", \"color\": "+str(Bfont[0])+", \"bold\": "+str(Bfont[1])+", \"italic\": "+str(Bfont[2])+"}]"

def make_newtoc(toc, Po_Zs,Bfonts):
    """
    しおりリスト全体にリンク情報を追加する。

    Args:
        toc (list): しおりのリスト [[レベル, タイトル, ページ番号], ...]。
        Po_Zs (dict): ページ番号をキー、(x座標, y座標, ズーム) のタプルを値とする辞書。

    Returns:
        str: 変換後のしおりデータをJSON風の文字列として返す。
    """
    print("　変換後のしおりデータをJSON風の文字列として作成しています。")
    entries = []
    for entry in toc:
        level, title, page = entry
        Bfont=Bfonts.get((title,page), ((0, 0, 0), False, False))  # そのページの座標とズームを取得 tocは１ページからPo_Zsは０ページから
        Po_Z = Po_Zs.get(page)  # そのページの座標とズームを取得 tocは１ページからPo_Zsは０ページから
        entries += [make_newentry(entry, Po_Z,Bfont)] #この[]がリスト化してくれるのか。
    return "["+",".join(entries)+"]"
        #参考return "["+",".join([add_link_to_entry(entry) for entry in toc])+"]"#文字列


if __name__ == "__main__":
    # 元の目次データ
    toc = [
        [1, '完成文書(未分類)', 1],
        [2, '打合せ簿【提出】', 1],
        [3, 'ｶ鑑_R6.12　履行報告書.pdf', 1],
        [3, 'ﾃ00_R6.12履行報告書.pdf', 2]
    ]

    # しおりのフォント情報（タイトルとページ番号のペアをキー）
    Bfonts = {
        ('完成文書(未分類)', 1): ((0, 0, 0), False, False),
        ('打合せ簿【提出】', 1): ((255, 0, 0), True, True),
        ('打合せ簿【提出】', 2): ((0, 128, 0), True, True)
    }

    # ページごとのリンク座標とズーム情報
    Po_Zs = {
        1: (100.0, 100.0, 0),
        2: (0.0, 100.0, 2),
        3: (100.0, 0.0, 1.5)
    }

    # 変換後の目次データ
    new_toc = make_newtoc(toc, Po_Zs, Bfonts)

    # 出力確認
    print(new_toc)


