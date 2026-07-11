@echo off
setlocal

python -m nuitka ^
  --standalone ^
  --assume-yes-for-downloads ^
  --enable-plugin=tk-inter ^
  --windows-console-mode=disable ^
  --windows-icon-from-ico=smallicon_v2.ico ^
  --include-data-files=smallicon_v2.ico=smallicon_v2.ico ^
  --include-data-files=smallicon_v2.png=smallicon_v2.png ^
  --include-data-files=assets/flag_jp.svg=assets/flag_jp.svg ^
  --include-data-files=assets/flag_gb.svg=assets/flag_gb.svg ^
  --output-filename=kojiPDF.exe ^
  kojiPDF.py

endlocal
