# kojiPDF v2.4.0 - 日本語 / English

## 概要 / Overview

kojiPDF は、PDFを活用したペーパーレス会議資料の作成、メールデータ整理、工事書類検査（ASP対応）に役立つ Windows 向けアプリです。

選択フォルダ配下のすべての PDF、Microsoft Office、メール、画像、テキスト、ZIP ファイルを PDF 化して1つのファイルに結合し、フォルダ階層・メール添付・ZIP 内ファイルを複階層しおりとして整理した PDF を作成します。ページ番号、ページサイズ変更、PDF 修復・圧縮などの出力調整にも対応しています。

kojiPDF is a Windows app for creating paperless meeting materials with PDFs, organizing email data, and preparing construction document inspections with ASP-oriented workflows.

It converts PDFs, Microsoft Office files, emails, images, text files, and ZIP files under the selected folder into one PDF, while organizing folder hierarchy, email attachments, and ZIP contents as multi-level bookmarks. It also supports output adjustments such as page numbers, page resizing, PDF repair, and compression.

## 主な機能 / Key Features

- **構造化 PDF 作成 / Structured PDF creation**  
  選択フォルダ配下のファイルを PDF 化し、1つの PDF に結合します。

- **複階層しおり / Multi-level bookmarks**  
  フォルダ階層に加えて、メール添付ファイルや ZIP 内ファイルも親子しおりとして整理します。

- **多様な入力形式 / Multiple input formats**  
  PDF、Microsoft Office、メール（.msg / .eml）、画像、テキスト、ZIP ファイルに対応します。

- **Office ファイル変換 / Office-to-PDF conversion**  
  Word、Excel、PowerPoint ファイルを PDF へ変換してから結合できます。

- **メール・添付ファイル整理 / Email and attachment organization**  
  メール本文を PDF 化し、添付ファイルも階層構造の一部として整理できます。

- **ZIP 展開 / ZIP extraction**  
  ZIP ファイル内のファイルも展開し、複階層しおりに反映できます。

- **ページ番号 / Page numbers**  
  結合 PDF へページ番号を追加できます。開始番号、文字サイズ、位置、色、不透明度を設定できます。

- **ページサイズ変更 / Page resizing**  
  PDF ページを A3、A4、A5、B4、B5 などの指定サイズへ変更できます。

- **PDF 修復・圧縮 / PDF repair and compression**  
  PDF warning の検査、必要に応じた修復、圧縮重視保存に対応します。

- **しおり表示設定 / Bookmark display options**  
  しおり名へのページ数追加、全しおり展開、展開階層の指定に対応しています。

- **しおり名の `.pdf` 処理 / `.pdf` handling in bookmark names**  
  しおり名末尾の `.pdf` を既定で削除します。必要に応じて保持することもできます。

- **工事書類検査（ASP対応） / Construction document inspection (ASP support)**  
  工事情報共有システム（ASP）由来のファイル名を、結合後 PDF のしおりとして読みやすく整形できます。

- **日本語 / 英語 GUI / Japanese and English UI**  
  GUI 表示を日本語と英語で切り替えできます。

- **JSON 起動 / JSON launch**  
  JSON 設定ファイルを指定して、PowerShell などの外部スクリプトから kojiPDF を起動できます。  
  kojiPDF can be launched from external scripts such as PowerShell by passing a JSON configuration file.

## v2.4.0 の主な変更 / Main Changes in v2.4.0

- 用途説明を、ペーパーレス会議資料、メールデータ整理、工事書類検査（ASP対応）向けに整理しました。  
  Updated the product description for paperless meeting materials, email data cleanup, and construction document inspections with ASP support.

- メール添付ファイルと ZIP 内ファイルを複階層しおりとして整理できることを明確にしました。  
  Clarified support for organizing email attachments and ZIP contents as multi-level bookmarks.

- PDF 修復・圧縮、保存 warning の扱い、依存関係の説明を整理しました。  
  Clarified PDF repair/compression behavior, save-warning handling, and dependencies.

- GUI 上のアプリ名表示を `kojiPDF v2.4.0` に更新しました。  
  Updated the GUI title display to `kojiPDF v2.4.0`.

- `kojiPDFv2.py config.json` / `kojiPDFv2.exe config.json` の JSON 起動に対応しました。  
  Added JSON launch support with `kojiPDFv2.py config.json` and `kojiPDFv2.exe config.json`.

- PowerShell などの外部スクリプトから JSON を生成して kojiPDF に渡せるようにしました。  
  External scripts such as PowerShell can generate a JSON config and pass it to kojiPDF.

## 動作環境 / Requirements

- Windows
- Python 3.10 or later
- Microsoft Office
  - Word / Excel / PowerPoint の PDF 変換機能を使う場合に必要です。
  - Required when using Word / Excel / PowerPoint to PDF conversion.
- Microsoft Outlook
  - .msg メールを変換する場合に必要です。
  - Required when converting .msg email files.
- Microsoft Edge or Google Chrome
  - メール本文 HTML を PDF 化する場合に必要です。
  - Required when converting email HTML bodies to PDF.

## インストール / Installation

```bash
pip install -r requirements.txt
```

## 実行方法 / Usage

```bash
python kojiPDFv2.py
```

JSON 設定ファイルを指定して起動できます。  
You can also launch kojiPDF with a JSON configuration file.

```bash
python kojiPDFv2.py config.json
```

exe ビルド後は次の形式で起動できます。  
After building the exe, use:

```bash
kojiPDFv2.exe config.json
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
- Pillow
- pywin32
- ttkbootstrap
- Nuitka

## ライセンス上の注意 / License Notice

このアプリは PyMuPDF / MuPDF を利用しているため、AGPL-3.0 の条件に従う必要があります。

商用利用自体は可能です。ただし、アプリを改変・再配布、またはネットワーク経由で提供する場合は、AGPL-3.0 に従ってソースコードを公開する必要があります。

AGPL-3.0 の条件を満たせない場合は、Artifex の商用ライセンスを検討してください。

This application uses PyMuPDF / MuPDF and must comply with AGPL-3.0 terms.

Commercial use is allowed. However, if the application is modified, redistributed, or provided over a network, the source code must be published under AGPL-3.0.

If you cannot comply with AGPL-3.0, consider a commercial license from Artifex.

## 著作権・参考リンク / Copyright & Reference Links

### PyMuPDF

- License: GNU AGPL v3.0 or Artifex Commercial License
- https://pymupdf.readthedocs.io/
- https://pymupdf.io/

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

- .msg メールの変換には、Microsoft Outlook がインストールされている必要があります。  
  Microsoft Outlook must be installed to convert .msg email files.

- メール本文の PDF 化には、Microsoft Edge または Google Chrome が必要です。  
  Microsoft Edge or Google Chrome is required to convert email HTML bodies to PDF.

- PDF のページサイズ変更や回転処理の結果は、元 PDF の構造に影響される場合があります。  
  Page resizing and rotation results may depend on the structure of the source PDF.

- ライブラリのライセンス条件については、各公式ドキュメントを確認してください。  
  Refer to the official documentation of each library for detailed license terms.
