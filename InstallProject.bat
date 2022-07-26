@echo off
cd %CD%
call python -m venv env
call .\env\Scripts\activate.bat
call python -m pip install -–upgrade pip
call python -m pip install -r requirements.txt