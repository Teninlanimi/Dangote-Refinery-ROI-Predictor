@echo off
REM Pull the latest Brent crude + USD/NGN data into the local database (instance\market.db)
cd /d "%~dp0"
py -m pipeline.ingest
pause
