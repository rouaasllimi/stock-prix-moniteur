@echo off
cd /d "%PROJECT_ROOT%"
python scrape_competitors.py
python low_stock_alert.py
echo %date% %time% - Tâche terminée >> journal.txt