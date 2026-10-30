@echo off
title PDF Hindi Extractor & 2-Up Stitcher GUI
cd /d "%~dp0"

echo =========================================================
echo  Starting PDF Hindi Extractor Web GUI...
echo  Opening browser at http://127.0.0.1:5000
echo =========================================================

start "" http://127.0.0.1:5000
python app.py
pause
