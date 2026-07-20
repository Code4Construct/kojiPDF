@echo off
setlocal

pushd "%~dp0" || exit /b 1

python -m nuitka ^
  --standalone ^
  --remove-output ^
  --assume-yes-for-downloads ^
  --jobs=1 ^
  --low-memory ^
  --enable-plugin=tk-inter ^
  --noinclude-custom-mode=matplotlib:nofollow ^
  --noinclude-custom-mode=scipy:nofollow ^
  --noinclude-custom-mode=bs4:nofollow ^
  --noinclude-custom-mode=html5lib:nofollow ^
  --noinclude-custom-mode=lxml:nofollow ^
  --noinclude-custom-mode=pandas:nofollow ^
  --noinclude-custom-mode=numpy:nofollow ^
  --noinclude-custom-mode=pymupdf.mupdf:bytecode ^
  --noinclude-numba-mode=nofollow ^
  --noinclude-IPython-mode=nofollow ^
  --noinclude-pytest-mode=nofollow ^
  --report=build-report.xml ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=assets\icons\smallicon_v2.ico ^
  --windows-company-name="Code4Construct" ^
  --windows-product-name="kojiPDF" ^
  --windows-file-version=2.4.0.0 ^
  --windows-product-version=2.4.0.0 ^
  --windows-file-description=kojiPDF_PDF_tool ^
  --include-data-files=assets\icons\smallicon_v2.ico=assets\icons\smallicon_v2.ico ^
  --include-data-files=assets\icons\smallicon_v2.png=assets\icons\smallicon_v2.png ^
  --output-filename=kojiPDFv2.exe ^
  kojiPDFv2.py

if errorlevel 1 (
  echo.
  echo Nuitka build failed. Exit code: %errorlevel%
  popd
  exit /b %errorlevel%
)

echo.
echo Nuitka build completed successfully.

popd
endlocal
