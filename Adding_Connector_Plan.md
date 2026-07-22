# kojiPDF Connector Development Plan

## Goal

This branch adds connector support for kojiPDF so that external tools can launch kojiPDF with a JSON configuration file.

The target launch style is:

```powershell
kojiPDFv2.exe "C:\path\to\config.json"
```

During development, the same behavior must be testable from the VSCode terminal without building an exe:

```powershell
python .\kojiPDFv2.py "C:\path\to\config.json"
```

This makes it possible to verify JSON loading, UI preset application, and automatic creation behavior before running the Nuitka build.

## Connector Concept

Outlook and Explorer integrations should not duplicate kojiPDF's PDF creation logic.

Instead, each connector should:

1. Collect or prepare source files.
2. Generate a JSON configuration file.
3. Start kojiPDF with the JSON file path as the first command-line argument.

kojiPDF itself should be responsible for:

1. Reading the JSON file.
2. Applying the same settings that the UI normally uses.
3. Either showing the UI with those settings pre-filled or starting PDF creation immediately.

## Recommended JSON Shape

```json
{
  "schema_version": 1,
  "mode": "mail",
  "run": {
    "auto_start": false,
    "write_error_report": true
  },
  "connector": {
    "cleanup_job_folder_after_launch": true
  },
  "paths": {
    "input_folder": "C:\\path\\to\\source",
    "output_pdf": "C:\\path\\to\\output\\mail_archive.pdf"
  },
  "settings": {
    "convert_office": true,
    "convert_mail": true,
    "eml_encoding": "auto",
    "ppt_slide_bookmarks": false,
    "confirm_temp_folder_delete": false,
    "resize_pdf": true,
    "resize_size": "A4",
    "preflight_detail_repair": false,
    "preflight_confirm": false,
    "save_mode": "balanced",
    "add_bookmark_page_number": true,
    "add_page": true,
    "expand_all": false,
    "collapse_level": 1,
    "keep_pdf_extension": false,
    "add_pdf_page_numbers": true,
    "page_number_position": "bottom_right",
    "page_number_format": "number",
    "page_start_page": 1,
    "page_start_number": 1,
    "page_font_size": 30,
    "page_margin_right": 10,
    "page_margin_bottom": 10,
    "page_font": "helv",
    "page_color": "red",
    "page_opacity": 0.2,
    "bookmark_view_mode": "fit_page",
    "scale_mode": "absolute",
    "scale_x": 1.0,
    "scale_y": 1.0,
    "base_view_width": 330,
    "base_view_height": 210,
    "asper_format": false
  }
}
```

`settings` should reuse the same keys as `DEFAULT_UI_SETTINGS` in `m05select_folder.py`.

The standard email data organization JSON should be based on `BUILT_IN_PRESETS["mail"]`.

`run.write_error_report` controls whether kojiPDF writes an error/warning report file.

Connector cleanup should stay on the connector side. For Outlook, `connector.cleanup_job_folder_after_launch` tells the VBA to wait for kojiPDF to finish and then delete only the temporary job folder it created, such as `mock/outlook_YYYYMMDD_HHMMSS`.

kojiPDF itself should not delete connector input folders. Outlook originals are never deleted; only the VBA-generated `.msg` working copies are removed when the VBA deletes its own job folder.

## Run Modes

### Confirm Before Creation

```json
"run": {
  "auto_start": false
}
```

kojiPDF loads the JSON, fills the UI, and waits for the user to press the create button.

This mode is useful for the first version and for debugging connector behavior.

### Start Immediately

```json
"run": {
  "auto_start": true
}
```

kojiPDF loads the JSON and starts PDF creation without asking the user to press the create button.

This mode is useful for stable connector workflows where the connector has already prepared the input folder and output path.

## Development Steps

### 1. Add JSON Launch Support To kojiPDF

- Update `kojiPDFv2.py` to inspect `sys.argv`.
- If no argument is supplied, keep the current UI-only behavior.
- If the first argument is a JSON file path, load the configuration.
- Log startup information to the existing startup log.
- Show a clear error if the JSON file does not exist or cannot be parsed.

### 2. Add A Launch Configuration Module

Add a small module such as:

```text
m52launch_config.py
```

Responsibilities:

- Load JSON with UTF-8.
- Validate `schema_version`.
- Merge `settings` over `DEFAULT_UI_SETTINGS` or the selected built-in preset.
- Support `mode: "mail"` by using `BUILT_IN_PRESETS["mail"]` as the base.
- Validate `paths.input_folder`.
- Normalize `paths.output_pdf`.
- Convert `save_mode` to `save_options`.
- Convert page-number margins from mm to points for `create_pdf`.
- Return data in the same shape that `kojiPDFv2.main()` already passes to `create_pdf`.

### 3. Allow The UI To Open With JSON Values

- Reuse `FileSelectorApp.apply_ui_settings()`.
- Add a way to set `selected_folder`, `selected_file`, `folder_text`, and `file_text` from JSON.
- With `auto_start: false`, show the UI after applying JSON values.
- The user can review or modify settings before pressing the create button.

### 4. Add Immediate Creation Mode

- With `auto_start: true`, skip the selection UI.
- Start PDF creation with the loaded paths and settings.
- Prefer showing the existing progress UI if practical.
- Keep the same error-report behavior as normal GUI execution.

### 5. Add Standard Email JSON Template

Add an example file such as:

```text
docs/examples/mail_connector_config.json
```

It should use:

- `mode: "mail"`
- `run.auto_start: false` for the first testable version
- `convert_office: true`
- `convert_mail: true`
- `resize_pdf: true`
- `resize_size: "A4"`
- `save_mode: "balanced"`
- bookmark page number and page count enabled
- merged PDF page numbers enabled

### 6. Add Outlook VBA Connector Folder

Create this folder:

```text
Outlook_VBA/
```

This folder should contain the Outlook-side connector files, for example:

- `README.md`
- `ExportSelectedMailToKojiPDF.bas`
- `sample_mail_connector_config.json`

Initial files in this branch:

- `Outlook_VBA/OutlookVBA4kojiPDF.bas`
- `Outlook_VBA/README.md`
- `Outlook_VBA/sample_mail_connector_config.json`

Expected Outlook VBA workflow:

1. Get currently selected Outlook mail items.
2. Save selected mails as `.msg` files into a temporary or user-selected working folder.
3. Generate a JSON configuration file that points `paths.input_folder` to that working folder.
4. Set `paths.output_pdf` to the desired output file.
5. Launch `kojiPDFv2.exe "<json path>"`.

The first VBA version can use `auto_start: false` so the user can confirm settings in kojiPDF before creation.

During development, the VBA should launch through the JSON `connector.launch_mode: "python"` setting:

```text
python C:\making_apps\kojiPDF\kojiPDFv2.py <config.json>
```

After the exe build is ready, switch the JSON setting to `connector.launch_mode: "exe"`. VBA code should not need to change for the normal Python-to-exe switch.

### 7. Update Installer Later

After the JSON launch path is stable:

- Include the connector helper files in the installed app folder.

Outlook VBA may remain a separate user-imported macro in the first release.

### 8. Test Plan

Test these cases before building the exe:

```powershell
python .\kojiPDFv2.py
python .\kojiPDFv2.py .\docs\examples\mail_connector_config.json
```

Then test after building:

```powershell
.\kojiPDFv2.dist\kojiPDFv2.exe .\docs\examples\mail_connector_config.json
```

Required checks:

- No JSON argument still opens the normal UI.
- JSON argument with `auto_start: false` opens the UI with settings filled.
- JSON argument with `auto_start: true` starts creation.
- Missing JSON file shows a useful error.
- Invalid JSON shows a useful error.
- Missing input folder shows a useful error.
- `.msg` and `.eml` mail conversion works.
- Attachments are organized under email bookmarks.
- ZIP files still expand and appear in bookmarks.
- Output PDF path conflicts are handled by the existing writable-file check.

## Suggested Implementation Order

1. Implement JSON parsing and validation.
2. Support `python .\kojiPDFv2.py config.json` in development.
3. Support `auto_start: false` with UI pre-fill.
4. Add the standard mail connector JSON example.
5. Support `auto_start: true`.
6. Add `Outlook_VBA/` connector files.
7. Update README.
8. Update installer.
9. Build exe and run final connector verification.
