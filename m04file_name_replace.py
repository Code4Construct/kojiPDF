from pandas import DataFrame  # pd.DataFrame のため
from pandas import set_option  # 表示オプション設定のため


def prepare_treedata_for_merge(df: DataFrame) -> DataFrame:
    """
    結合・しおり作成に必要な共通整形を行います。

    処理内容:
    - 'sortpath' 列で昇順ソート
    - 'Page Count' 列の累積値を 'Page All' として追加
    - 'Page All' をデータフレームの左端の列に移動

    Args:
        df (DataFrame): 修正対象のデータフレーム

    Returns:
        DataFrame: 修正後のデータフレーム
    """
    df = df.copy()
    df = df.sort_values(by='sortpath', ascending=True)

    # 'Page Count' を累積して 'Page All' を新たに追加
    df['Page All'] = df['Page Count'].shift(1).cumsum().fillna(0).astype(int)
    
    # 'Page All' を左端の列に移動
    cols = ['Page All'] + [col for col in df.columns if col != 'Page All']
    df = df[cols]

    return df


def modify_pdf_names_in_all_columns(df: DataFrame) -> DataFrame:
    """
    後方互換用: 電脳ASPer向けの名前調整を行ってから共通整形します。
    """
    import m14asper_format as asper_format

    return prepare_treedata_for_merge(asper_format.modify_pdf_names_in_all_columns(df))

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



