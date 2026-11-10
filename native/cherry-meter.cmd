@echo off
rem Requires an existing Python 3.10+ on PATH; no download or installation.
python "%~dp0launch.py" %*
exit /b %errorlevel%
