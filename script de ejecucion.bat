@echo off
REM Crea y activa el entorno virtual, instala dependencias y ejecuta el script
python -m venv venv
call .\venv\Scripts\activate
pip install PyQt5 pure-python-adb
python "BlackBox.py"
pause