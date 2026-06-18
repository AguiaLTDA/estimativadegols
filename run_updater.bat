@echo off
cd /d "%~dp0"
echo Running Estimativa de Gols automatic updater...
python update_results.py
echo Update completed.
