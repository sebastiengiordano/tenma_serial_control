@echo on
cd %CD%
call py -m venv env
call .\env\Scripts\activate.bat
call .\env\Scripts\python.exe -m pip install --upgrade pip
call .\env\Scripts\python.exe -m pip install -r requirements.txt
@pause