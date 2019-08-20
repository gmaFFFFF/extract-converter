@echo off

@CALL C:\Anaconda3\Scripts\activate.bat C:\Anaconda3\envs\dev

:start

python KPT.py

:Endscript
pause

goto :start