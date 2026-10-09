# Changelog

This repository now consolidates the separate kojiPDF version repositories into the main `Code4Construct/kojiPDF` repository.

## Unreleased

- Ported the browser-style Viewer layout from the withdrawn kojiPDFviewer v0.4.0 change while keeping the toolbar: page navigation, fit mode, hand tool, and fullscreen now sit above the PDF; list switching and display settings sit above the list; the count sits below it.
- Added mail list and bookmark list display settings (card or one-line layout, sort order, grouping by subject, visible fields, font size, density), saved automatically.
- Moved favorites to a ☆/★ button on each tab and added reindexing and recent PDFs to the tab context menu.
- Detected plain-text URLs and email addresses in the PDF body as links, and highlighted links on hover with the target in the tooltip and status bar.
- Kept the visible page position when switching fit mode, resizing, hiding the list, or entering and leaving fullscreen.
- Restored the window size and list visibility after leaving fullscreen.
- Added a Viewer toolbar button to launch kojiPDF and close the Viewer after successful launch.
- Shortened the Japanese Viewer launch button label to kojiPDFviewer起動.
- Increased PDF mouse-wheel scrolling to 12 times the previous amount and added Ctrl+wheel zoom.
- Added Space+left-drag panning and a hand-icon toolbar toggle while preserving text selection.
- Included PDF rendering, sticky-note, and review modules in the publish source tree.
- Improved large PDF loading in the Viewer: display pages before indexing, avoid full-page text extraction above 2,000 pages, and speed up bookmark range calculation.
- Use on-demand PyMuPDF page rendering for PDFs over 2,000 pages when Qt PDF cannot load the full document.
- Keep PDF pages and built-in bookmarks visible when a sidecar index cannot be written, with a status message explaining the indexing failure.
- Restore external links and add responsive PDF body search in the large-document renderer.

## v2.6.0

- Integrated kojiPDFViewer as a separate Python package in the kojiPDF source application.
- Added a bilingual Viewer launch button and optional existing-PDF handoff.
- Pinned the shared PyMuPDF runtime to 1.28.2.
- Verified the Python source workflow with 73 tests and an end-to-end PDF-to-Viewer smoke check; Nuitka/MSI packaging remains deferred.

## v2.5.0

- Migrated the standalone kojiPDF interface from Tkinter/ttkbootstrap to PySide6.
- Preserved the PDF engine, JSON launch configuration, saved presets, and worker progress/confirmation flows.
- Updated the Nuitka build configuration for PySide6; the current source revision has not yet been packaged or installer-tested.
- Recreated the bilingual compact layout and kept the existing PDF generation and bookmark destinations.

## v2.4.5

- Fixed collisions between shortened nested Office attachment paths so each source produces a distinct PDF.
- Added rendering support for CID-linked EMZ images, VML fallbacks, and positioned image overlays in mail bodies.
- Added bounded retries and clearer diagnostics for transient Word, Excel, and PowerPoint automation failures.
- Updated build, installer, GUI, and documentation version labels to v2.4.5.
- Clarified third-party dependency license notices, including extract-msg GPL usage.
- Stabilized signed/protected `.msg` mail conversion by extracting normal body and attachments while ignoring signature payloads.
- Improved Word mail-body conversion cleanup to avoid save prompts and residual converted-body false positives.
- Preserved final PDF candidate files when output replacement fails because the destination PDF is locked.

## v2.4.3

- Updated build, installer, GUI, and documentation version labels to v2.4.3.
- Removed the final bookmark-tree rebuild used only for `.pdf` suffix cleanup, avoiding MuPDF save warnings from stale outline xrefs.
- Kept `.pdf` suffix cleanup behavior by applying it before bookmark creation.

## v2.4.0

- Added JSON launch configuration support with `kojiPDFv2.py config.json` and `kojiPDFv2.exe config.json`.
- Added support for launching kojiPDF from external scripts such as PowerShell by generating and passing a JSON config.
- Updated build, installer, GUI, and documentation version labels to v2.4.0.

## v2.3.1 integrated release

- Integrated the v1.5.0 changes from `Code4Construct/kojiPDFv150`.
- Integrated the v2.0.0 changes from `Code4Construct/kojiPDFv200`.
- Integrated the v2.3.1 changes from `Code4Construct/kojiPDFv210`.
- Updated project links so the integrated project points back to `Code4Construct/kojiPDF`.
- Updated the usage command to run `kojiPDFv2.py`, matching the v2.3.1 application entry point.

## v2.3.1

- Added the v2 application entry point as `kojiPDFv2.py`.
- Expanded the Windows build workflow and installer configuration.
- Added WiX installer files and release license text.
- Moved application icons under `assets/icons/`.
- Improved PDF preflight, invalid PDF handling, resizing, page numbering, bookmarks, and save warning behavior.
- Updated UI and README messaging for paperless meeting materials, email data cleanup, and construction document inspections with ASP support.
- Clarified support for organizing folder hierarchy, email attachments, and ZIP contents as multi-level bookmarks.
- Updated dependency documentation for Office, Outlook, Edge/Chrome, PyMuPDF, Pillow, pywin32, ttkbootstrap, and Nuitka.

## v2.0.0

- Added bilingual GUI resources and updated the main GUI flow.
- Added Windows build and installer support.
- Added code-signing policy documentation.
- Added PDF resize and page-numbering modules.
- Added bookmark cleanup and ASP-oriented bookmark formatting.
- Updated dependencies and project documentation.

## v1.5.0

- Updated README content.
- Added image listing helper script.
- Improved folder selection behavior.
- Updated bookmark handling and the main application script.
- Removed the old PyInstaller spec file.

## v1.4.2 and earlier

- Original main repository history before the split version repositories were integrated.
