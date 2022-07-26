@echo off
cd %CD%
call .\env\Scripts\activate.bat
call python -m bench
cmd \k