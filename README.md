# kojiPDF v2.1.0 - 日本語 / English

## 概要 / Overview

kojiPDF は、選択したフォルダ内の PDF ファイルを結合し、ファイル名をしおり、フォルダ名を親しおりとして追加した構造化 PDF を作成する Windows 向けアプリです。工事検査資料の整理、情報共有システムの電子データ確認、ペーパーレス会議資料の作成などに利用できます。

kojiPDF creates a structured PDF by merging PDF files in a selected folder and adding bookmarks from file and folder names. It is designed for organizing construction inspection documents, reviewing information-sharing system records, and preparing paperless meeting materials.

## 主な機能 / Key Features

- **PDF 結合 / PDF merging**  
  複数の PDF ファイルを 1 つの PDF に結合します。

- **階層しおり / Hierarchical bookmarks**  
  ファイル名をしおり、フォルダ名を親しおりとして追加します。

- **Office ファイル変換 / Office-to-PDF conversion**  
  Word、Excel、PowerPoint ファイルを PDF へ変換してから結合できます。

- **PowerPoint スライドしおり / PowerPoint slide bookmarks**  
  PowerPoint 変換時に、出力 PDF のスライドしおりを保持できます。

- **ページ番号 / Page numbers**  
  結合 PDF へページ番号を追加できます。開始番号、文字サイズ、余白、色、不透明度を設定できます。

- **ページサイズ変更 / Page resizing**  
  PDF ページを A3、A4、A5、B4、B5 などの指定サイズへ変更できます。

- **しおり表示設定 / Bookmark display options**  
  しおり名へのページ数追加、全しおり展開、展開階層の指定に対応しています。

- **しおり名の `.pdf` 処理 / `.pdf` handling in bookmark names**  
  しおり名末尾の `.pdf` を既定で削除します。必要に応じて保持することもできます。

- **ASP 向けしおり名整形 / ASP bookmark name formatting**  
  工事情報共有システム（ASP）由来のファイル名を、結合後 PDF のしおりとして読みやすく整形できます。

- **日本語 / 英語 GUI / Japanese and English UI**  
  GUI 表示を日本語と英語で切り替えできます。

## v2.1.0 の主な変更 / Main Changes in v2.1.0

- README を v2.1.0 向けに整理し、日本語と英語の説明を読みやすく更新しました。  
  Updated the README for v2.1.0 with clearer Japanese and English descriptions.

- GUI 上のアプリ名表示を `kojiPDF v2.1.0` に更新しました。  
  Updated the GUI title display to `kojiPDF v2.1.0`.

- 配布手順書、署名ポリシー、リリース用ファイル名の例を v2.1.0 向けに更新しました。  
  Updated distribution notes, signing policy references, and release artifact examples for v2.1.0.

## 動作環境 / Requirements

- Windows
- Python 3.10 以上 / Python 3.10 or later
- Microsoft Office
  - Word / Excel / PowerPoint の PDF 変換機能を使う場合に必要です。
  - Required when using Word / Excel / PowerPoint to PDF conversion.

## インストール / Installation

```bash
pip install -r requirements.txt
```

## 実行方法 / Usage

```bash
python kojiPDFv2.py
```

## プロジェクトリンク / Project Links

- GitHub repository: https://github.com/Code4Construct/kojiPDF
- GitHub Releases: https://github.com/Code4Construct/kojiPDF/releases
- Release assets include the signed MSI installer and a portable ZIP containing the full `kojiPDFv2.dist` folder.
- Code signing policy: `CODE_SIGNING_POLICY.md`

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

このアプリは PyMuPDF / MuPDF を利用しているため、AGPL-3.0 の条件に従う必要があります。

商用利用自体は可能です。ただし、アプリを改変、再配布、またはネットワーク経由で提供する場合は、AGPL-3.0 に従ってソースコードを公開する必要があります。

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

- Office ファイルの変換には、Microsoft Office がインストールされている必要があります。  
  Microsoft Office must be installed to convert Office files.

- PDF のページサイズ変更や回転処理の結果は、元 PDF の構造に影響される場合があります。  
  Page resizing and rotation results may depend on the structure of the source PDF.

- ライブラリのライセンス条件については、各公式ドキュメントを確認してください。  
  Refer to the official documentation of each library for detailed license terms.
