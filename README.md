# kojiPDF v2.0.0 - 日本語 / English

## 概要 / Overview

kojiPDF は、選択したフォルダ内のPDFファイルを結合し、ファイル名をしおり、フォルダ名を親しおりとして追加した構造化PDFを作成するアプリです。工事検査資料の整理、情報共有システムの電子データ確認、ペーパーレス会議資料の作成・閲覧などに利用できます。

kojiPDF creates a structured PDF by merging PDF files in a selected folder and adding bookmarks from file and folder names. It is designed for organizing construction inspection documents, reviewing information-sharing system records, and preparing or viewing paperless meeting materials.

## 主な機能 / Key Features

- **PDF結合 / PDF merging**  
  複数のPDFファイルを1つのPDFに結合します。  
  Merges multiple PDF files into a single PDF.

- **階層しおり / Hierarchical bookmarks**  
  ファイル名をしおり、フォルダ名を親しおりとして追加します。  
  Adds file names as bookmarks and folder names as parent bookmarks.

- **Officeファイル変換 / Office-to-PDF conversion**  
  Word、Excel、PowerPointファイルをPDFへ変換して結合できます。  
  Converts Word, Excel, and PowerPoint files to PDF before merging.

- **PowerPointスライドしおり / PowerPoint slide bookmarks**  
  PowerPoint変換時に、出力PDFのスライドしおりを保持できます。  
  Can retain slide bookmarks in the exported PDF when converting PowerPoint files.

- **ページ番号 / Page numbers**  
  結合PDFへ透明度を設定できるページ番号を追加できます。  
  Adds page numbers with configurable opacity to merged PDF pages.

- **ページサイズ変更 / Page resizing**  
  PDFページを指定サイズへ変更できます。  
  Resizes PDF pages to a selected page size.

- **しおり表示設定 / Bookmark display options**  
  しおり名へのページ数追加、全しおり展開、展開階層の指定に対応します。  
  Supports page counts in bookmark names, expanded bookmarks, and bookmark open levels.

- **しおり名の `.pdf` 処理 / `.pdf` handling in bookmark names**  
  しおり名末尾の `.pdf` を削除できます。必要に応じて保持することもできます。  
  Removes trailing `.pdf` from bookmark names by default, with an option to keep it.

- **ASP向けしおり名整形 / ASP bookmark name formatting**  
  工事情報共有システム（ASP）向けのしおり名整形に対応します。  
  Provides bookmark name formatting for construction information-sharing systems (ASP).

  - **「電脳ASPer用のしおり名に整える」をオンにした場合**

    電脳ASPerから出力したファイル名には、`【本文】`、`【鑑】`、`【添付1】` のような区分名や、並び順を管理するための先頭番号が含まれることがあります。  
    この機能をオンにすると、元のファイル自体は変更せず、結合後の PDF に付くしおり名だけを、閲覧しやすい形に整えます。

    実際には、しおり名に対して次の変換を行います。

    - PDF ファイル名の `【本文】` を削除します。
    - PDF ファイル名の `【鑑】` は、最終的に `打_` に置き換えます。
    - PDF ファイル名の `【添付1】`、`【添付2】` のような表記は、最終的なしおり名では削除します。
    - PDF ファイル名の先頭にある `00` + 2桁番号 + `-` を削除します。  
      例: `0001-`、`0012-`
    - フォルダ名の先頭にある 2桁番号 + `-` を削除します。  
      例: `01-`、`12-`

    例:

    - `0001-【本文】工事打合せ簿.pdf` → `工事打合せ簿.pdf`
    - `0002-【鑑】施工計画書.pdf` → `打_施工計画書.pdf`
    - `0003-【添付1】図面.pdf` → `図面.pdf`
    - `01-契約関係` → `契約関係`

    また、電脳ASPer向けの判別をしやすくするため、ファイルのしおりは種類に応じて色分けされます。

    When enabled, this option cleans up bookmark names generated from Dennoh ASPer file names without changing the original files. It removes `【本文】`, converts `【鑑】` to `打_`, removes markers such as `【添付1】`, drops leading control numbers such as `0001-` from PDF names and `01-` from folder names, and makes the final bookmark display easier to read. It also applies bookmark colors to help distinguish file types.

- **日本語・英語表示 / Japanese and English UI**  
  GUI表示を日本語と英語で切り替えできます。  
  The GUI can be switched between Japanese and English.

## v2.0.0 の主な変更 / Main Changes in v2.0.0

- GUIの構成、説明文、進行状況表示を見直しました。  
  Refined the GUI layout, descriptions, and progress display.

- v2用アイコンを追加しました。  
  Added a version 2 icon.

- Nuitka用ビルドスクリプト `build_nuitka.bat` を追加しました。  
  Added the Nuitka build script `build_nuitka.bat`.

- ASP専用のしおり名整形処理を通常処理から分離し、GUIで選択できるようにしました。  
  Separated ASP-specific bookmark formatting from the standard workflow and made it selectable in the GUI.

- しおり色分け処理は、ASP向け処理が有効な場合のみ動作するようにしました。  
  Bookmark color handling now runs only when ASP formatting is enabled.

- しおり名末尾の `.pdf` は初期設定で削除し、GUIで保持を選択できるようにしました。  
  Trailing `.pdf` is removed from bookmark names by default, with a GUI option to keep it.

- AGPL-3.0に関する注意書きをGUI上にも表示するようにしました。  
  Added AGPL-3.0 notices to the GUI.

## 動作環境 / Requirements

- Windows
- Python 3.10 以上 / Python 3.10 or later
- Microsoft Office
  - Word / Excel / PowerPoint のPDF変換機能を使う場合に必要です。
  - Required when using Word / Excel / PowerPoint to PDF conversion.

## インストール / Installation

```bash
pip install -r requirements.txt
```

## プロジェクトリンク / Project Links

- GitHub repository: https://github.com/Code4Construct/kojiPDFv200
- GitHub Releases: https://github.com/Code4Construct/kojiPDFv200/releases
- Code signing policy: `CODE_SIGNING_POLICY.md`

## 実行方法 / Usage

```bash
python kojiPDF.py
```

## 依存ライブラリ / Dependencies

詳細なバージョンは `requirements.txt` を確認してください。  
See `requirements.txt` for exact versions.

- PyMuPDF
- pandas
- openpyxl
- Pillow
- pywin32
- ttkbootstrap
- Nuitka

## ライセンス上の注意 / License Notice

本アプリは PyMuPDF / MuPDF を利用しているため、AGPL-3.0 の条件に従う必要があります。

商用利用自体は可能ですが、アプリを改変、再配布、またはネットワーク経由で提供する場合は、AGPL-3.0 に従いソースコードを公開する必要があります。

AGPL-3.0 の条件を満たせない場合は、Artifex の商用ライセンスを検討してください。

This application uses PyMuPDF / MuPDF and must comply with AGPL-3.0 terms.

Commercial use is allowed. However, if the application is modified, redistributed, or provided over a network, the source code must be published under AGPL-3.0.

If you cannot comply with AGPL-3.0, consider a commercial license from Artifex.

## 著作権・参照リンク / Copyright & Reference Links

### PyMuPDF

- License: GNU AGPL v3.0 または Artifex Commercial License  
  License: GNU AGPL v3.0 or Artifex Commercial License
- https://pymupdf.readthedocs.io/
- https://pymupdf.io/

### pandas

- License: BSD 3-Clause License
- https://github.com/pandas-dev/pandas/blob/main/LICENSE

### openpyxl

- License: MIT License
- https://openpyxl.readthedocs.io/

### Pillow

- License: HPND License
- https://python-pillow.org/

### pywin32

- License: Python Software Foundation License
- https://github.com/mhammond/pywin32

### ttkbootstrap

- License: MIT License
- https://ttkbootstrap.readthedocs.io/

### Nuitka

- License: Apache License 2.0
- https://nuitka.net/

## 注意事項 / Notes

- Officeファイルの変換には、Microsoft Officeがインストールされている必要があります。  
  Microsoft Office must be installed to convert Office files.

- PDFのページサイズ変更や回転処理の結果は、元PDFの構造に影響される場合があります。  
  Page resizing and rotation results may depend on the structure of the source PDF.

- ライブラリのライセンス条件については、各公式ドキュメントを確認してください。  
  Refer to the official documentation of each library for detailed license terms.
