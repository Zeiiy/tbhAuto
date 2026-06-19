# Construit l'app native en UN seul fichier : dist\TBHBot.exe
# Usage :  .\build_exe.ps1   (depuis backend\, venv installe)
Set-Location $PSScriptRoot
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name TBHBot `
  --collect-data customtkinter `
  --add-data "templates;templates" `
  gui.py
Write-Output "EXIT=$LASTEXITCODE  ->  dist\TBHBot.exe"
