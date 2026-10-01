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

The Viewer button is in the creator header. It opens the selected output PDF when that file already exists; otherwise it opens the Viewer for choosing a PDF. Both windows share one Python process. The Viewer modules live in `koji_viewer/` and can still be started separately with `python -m koji_viewer.main` during development.

For PDFs over 2,000 pages, the Viewer renders one page at a time with PyMuPDF and indexes bookmark titles without extracting all page text at open time. The search box finds bookmark titles and searches PDF body text in the background; press Enter to move to the next matching page. External URL, email, and file links on the displayed page remain clickable.

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
