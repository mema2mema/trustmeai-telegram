@echo off
:loop
python telegram_bot.py
echo Bot crashed. Restarting in 5 seconds...
timeout /t 5
goto loop
