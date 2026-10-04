# kojiPDF v2.6.0

kojiPDF is a Windows PDF utility for creating structured merged PDFs from folders that contain PDFs, Microsoft Office files, emails, images, text files, and ZIP archives.

It is designed for paperless meeting materials, email-data organization, and construction document inspection workflows. It can create multi-level bookmarks from folder hierarchy, email attachments, and ZIP contents, and it supports page numbers, page resizing, PDF repair, and compression-oriented output.

## Key Features

- Merge PDFs and converted files into one structured PDF.
- Preserve folder hierarchy as multi-level bookmarks.
- Include email bodies and attachments in the output structure.
- Expand ZIP files safely and include their contents.
- Convert Office files, images, text files, `.msg`, and `.eml` files when conversion is enabled.
- Add page numbers to merged PDF pages.
- Resize PDF pages to standard sizes such as A3, A4, A5, B4, and B5.
- Check, repair, and save PDFs with compression-oriented options.
- Switch the PySide6 GUI between Japanese and English.
- Launch from JSON configuration files such as `kojiPDFv2.py config.json` or `kojiPDFv2.exe config.json`.

## Main Changes in v2.6.0

- Added the integrated Viewer as a separate Python package within the same application.
- Added an Open Viewer button to the PDF creator; an existing selected output PDF opens directly in the Viewer.
- Standardized creator and Viewer on PyMuPDF 1.28.2 while preserving their separate tests.

The Viewer button is in the creator header. It opens the selected output PDF when that file already exists; otherwise it opens the Viewer for choosing a PDF. After successfully launching from the selection screen, the creator screen closes automatically and the Viewer becomes operable. Both use the same GUI process, which remains alive until the Viewer closes. Launching during PDF creation leaves the progress screen running. The Viewer isolates PDF rendering, searching, and body indexing in spawned worker processes. The Viewer modules live in `koji_viewer/` and can still be started separately with `python -m koji_viewer.main` during development.

All PDF sizes use the same PyMuPDF viewer, including continuous scrolling, searchable-text selection/copying, and internal/external links. Visible page regions are rendered on demand with a 64 MiB image cache. Enter moves to the next highlighted search segment; Shift+Enter moves back. Mail/document metadata appears first and body indexes complete in the background with visible progress, preserving read state. Until indexing finishes, body-based list filtering is incomplete. Image-only pages require OCR to provide searchable/selectable text; OCR is outside this Viewer change. Range windows, welcome thumbnails, and printing also use PyMuPDF.

### Viewer document review

The toolbar's **書類レビュー** button opens a resizable right panel in bookmark and mail modes. Enter **記入者**, select **＋ コメント**, click a PDF location, enter text and choose a color. Esc cancels placement. Click an icon to edit your comment; overlapping icons show a count and let you choose the comment. Double-clicking the list opens its editor. Existing PDF Text annotations remain visible and are kept unchanged until explicitly edited. Comments are excluded from body search.

Changes automatically persist to `資料_review_draft.json`. Named reviews retain author IDs, comment IDs, explicit deletions, submission revisions, judgments and history after PDF saving. Older `資料_付箋メモ.json` files migrate with the original JSON retained. The PDF stays unchanged until **コメント付きPDFに保存**, which defaults to a separate output. A tab's **＊** means comments are not yet reflected in the PDF. Failed JSON writes preserve the durable file and offer retry; closing offers retry, discard only unsaved changes, or cancel.

Use **書き出す** to submit your comments as `資料_review_山田_v001.json`; subsequent exports increment the revision. **取り込む** previews multiple submissions, checks the original PDF's content identity, prevents duplicate/old imports and compares conflicting updates. Other authors' original text is read-only; you can set **未確認 / 確認済み / 対応不要**, add a **取りまとめメモ**, or exclude and restore a comment. Updated original text returns to 未確認 while keeping your memo. Filter by author, state, exclusion and text. The adjacent menu includes **レビュー集約を保存 / 開く** (`資料_review_merged.json`) and **レビュー履歴**.

PDF outputs use `資料_review_山田_v001.pdf` or `資料_review_merged.pdf`; author, original text, status and coordinator memo are included in standard PDF notes. Continue editing the output PDF together with its retained draft JSON, or open a matching exported merged JSON. Keep JSON records for further imports: PDF alone does not retain submission/deletion history. The worker process verifies a staging PDF before atomic replacement, preserving pages, bookmarks, links and unrelated annotations. A source draft is removed only after the output draft is durable; interrupted saves recover through the recorded output hash. OS locks and file tokens prevent concurrent overwrites. `.json.lock` file presence alone does not mean a lock is active. Extracted page-range windows do not edit comments.

See [the review specification](specs/012-document-review/spec.md) and [validation guide](specs/012-document-review/quickstart.md). Source tests cover review and legacy sticky-note behavior; no compiled release is produced by this change.

## Main Changes in v2.5.0

- Replaced the standalone Tkinter/ttkbootstrap interface with PySide6 while preserving PDF creation settings, presets, and JSON launch configuration.
- Moved progress and confirmation dialogs into the Qt UI so worker requests remain responsive.
- Recreated the Japanese and English layouts, including the compact settings panels and scrollable display on smaller screens.

## Changes in v2.4.5

- Stabilized signed/protected `.msg` mail conversion.
- Added direct signed `.msg` parsing with `extract-msg` for cases where Outlook keeps signed mail files locked.
- Signature-only payloads are ignored while normal mail body and regular attachments are extracted.
- Improved Word mail-body conversion cleanup to avoid save prompts.
- Avoided false `Unconverted file list` entries for converted mail body HTML files.
- Preserved the final PDF candidate when replacing the output PDF fails because the destination PDF is locked.
- Fixed collisions between shortened nested Office attachment paths so each source produces a distinct PDF.
- Added rendering support for CID-linked EMZ images, VML fallbacks, and positioned image overlays in mail bodies.
- Added bounded retries and clearer diagnostics for transient Word, Excel, and PowerPoint automation failures.
- Updated build, installer, GUI, and documentation version labels to v2.4.5.

## Requirements

- Windows
- Python 3.12 for development and builds (not required to run the installed app)
- Microsoft Office
  - Required for Word / Excel / PowerPoint to PDF conversion.
- Microsoft Outlook
  - Used for ordinary `.msg` fallback conversion.
- Microsoft Edge or Google Chrome
  - Required for email HTML-body to PDF conversion.

## Dependencies

See `requirements.txt` for exact versions.

- PyMuPDF
- Pillow
- pywin32
- PySide6
- extract-msg
- Nuitka

### Development setup

Use Python 3.12 for source runs, tests, and Nuitka builds:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe kojiPDFv2.py
```

Build with the Python 3.12 virtual environment:

```powershell
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"
.\build_nuitka.bat
```

The build script checks that `python` resolves to Python 3.12.

In VS Code, choose `.venv\Scripts\python.exe` with **Python: Select Interpreter**. The system Python 3.12 installation does not automatically contain this project's packages.

## License Notice

kojiPDF itself is provided under AGPL-3.0. The application also uses third-party dependencies, and each dependency has its own license terms.

Commercial use is allowed. However, if the application is modified, redistributed, packaged for distribution, or provided over a network, you must comply with AGPL-3.0 and the license terms of the included dependencies.

PyMuPDF / MuPDF is available under GNU AGPL v3.0 or an Artifex commercial license. If your use or distribution model cannot comply with AGPL-3.0 for PyMuPDF / MuPDF, consider an Artifex commercial license.

extract-msg is published under GPL according to its package metadata. It is used by kojiPDF to directly parse signed/protected `.msg` files when Outlook-based conversion is not appropriate. If you distribute a build that includes or depends on extract-msg, review the GPL requirements for that distribution model.

This notice is a project documentation summary, not legal advice. For exact obligations, refer to each project's official license text and consult an appropriate professional when necessary.

## Copyright & Reference Links

### kojiPDF

- License: GNU AGPL v3.0
- Repository: https://github.com/Code4Construct/kojiPDF

### PyMuPDF / MuPDF

- License: GNU AGPL v3.0 or Artifex Commercial License
- https://pymupdf.readthedocs.io/
- https://pymupdf.io/

### Pillow

- License: HPND License
- https://python-pillow.org/

### pywin32

- License: Python Software Foundation License
- https://github.com/mhammond/pywin32

### PySide6 / Qt for Python

- License: LGPLv3/GPLv3 (Community Edition) or Qt commercial license
- https://doc.qt.io/qtforpython-6/

### extract-msg

- License: GPL
- Package import name: `extract_msg`
- Used for direct parsing of signed/protected `.msg` files.
- https://github.com/TeamMsgExtractor/msg-extractor

### Nuitka

- License: Apache License 2.0
- https://nuitka.net/

## Notes

- Office file conversion requires Microsoft Office.
- Ordinary `.msg` fallback conversion uses Microsoft Outlook.
- Signed/protected `.msg` files may be parsed directly with extract-msg so signature payloads can be ignored without changing the original mail.
- Email HTML-body conversion requires Microsoft Edge or Google Chrome.
- PDF page resizing and rotation results may depend on the source PDF structure.
- Always check the official license documentation for each dependency before redistribution.
