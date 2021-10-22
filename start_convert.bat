@echo off

rem Сохранить текущую кодировку консоли в переменной %ccp%
rem Источник https://www.dostips.com/forum/viewtopic.php?p=56647&sid=859d35fc5f1ead4cdd2370b10120f562#p56647
For /F "Tokens=*" %%A In ('ChCp') Do For %%B In (%%A) Do Set "ccp=%%~nB"

rem Переключение на кодировку windows-1251
chcp 1251 > nul

rem Проверка доступности pipenv. Если команда не найдена, то ERRORLEVEL == 1
where pipenv > nul
IF ERRORLEVEL 1  (
    rem Обновить переменную среды path
    call RefreshEnv.cmd
)

pipenv run py convert.py
)

rem Возврат исходной кодировки
chcp %ccp% > nul

pause