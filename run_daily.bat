@echo off
cd /d %~dp0
python run.py >> daily.log 2>&1
