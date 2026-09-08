@echo off
:: The stage console is a route on the same server, not a second application.
:: Start Banco with start.bat, then this opens the console.
start "" http://127.0.0.1:8501/console
