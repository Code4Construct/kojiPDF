import re
from pandas import DataFrame  # pd.DataFrame のため
from pandas import set_option  # 表示オプション設定のため

def modify_pdf_names_in_all_columns(df: DataFrame) -> DataFrame:
    """ 
    DataFrame 内のすべての列に含まれる PDF 名を適切に修正します。

    ただし、列名が "Full Path" の場合は変更をスキップします。

    修正内容:
    - "【本文】" を削除
    - "【鑑】" → "ｶ鑑_"
    - "【添付" → "ﾃ"
    - "】" → "_"
    - .pdf で終わらない場合、先頭に半角数字 2 文字 + "-" があれば削除

    さらに、以下の処理を行います:
    - 'sortpath' 列で昇順ソート
    - 'Page Count' 列の累積値を 'Page All' として追加
    - 'Page All' をデータフレームの左端の列に移動

    Args:
        df (DataFrame): 修正対象のデータフレーム

    Returns:
        DataFrame: 修正後のデータフレーム
    """
    def modify_name(value):
        if isinstance(value, str):
            if value.endswith('.pdf'):
                value = value.replace("【本文】", "")
                value = value.replace("【鑑】", "ｶ鑑_")

                # 【添付〇〇】 → ﾃ〇〇_
                value = re.sub(r'【添付(\d+)】', r'ﾃ\1_', value)

                # 00XX- を削除
                value = re.sub(r'^00(\d{2})-', r'', value)
            else:
                # XX- を削除
                value = re.sub(r'^(\d{2})-', r'', value)
        return value

    for column in df.columns:
        if column != "Full Path":
            df[column] = df[column].apply(modify_name)

    df = df.sort_values(by='sortpath', ascending=True)

    # 'Page Count' を累積して 'Page All' を新たに追加
    df['Page All'] = df['Page Count'].shift(1).cumsum().fillna(0).astype(int)
    
    # 'Page All' を左端の列に移動
    cols = ['Page All'] + [col for col in df.columns if col != 'Page All']
    df = df[cols]

    return df

if __name__ == '__main__':
    set_option('display.unicode.east_asian_width', True)  # 表示設定（オプション）
    
    data = {
        "column1": ["【本文】example1.pdf", "example2.txt", "12-example3.txt"],
        "Full Path": ["C:/path/to/12-file1.pdf", "C:/path/to/file2.pdf", None],
        "column3": ["34-textfile.doc", "0034-【本文】【鑑】example6.pdf", "78-example7.pdf"]
    }

    df = DataFrame(data)

    print("変更前のデータフレーム:")
    print(df)

    modified_df = modify_pdf_names_in_all_columns(df)

    print("\n変更後のデータフレーム:")
    print(modified_df)



