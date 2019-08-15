# Конвертирование выписок Росреестра в Esri Shape

Автор: Гришкин Максим

Лицензия: MIT License

## Настройка среды

- Установить Python минимум версии 3.5. Рекомендую [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 

- Создать виртуальную среду (согласно инструкции к [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html))

- В файле kptRun.bat уточнить путь к интерпретатуру python 
   
   ```
   "Путь к интерпретатуру\python.exe" KPT.py
   ```
   
- Установить доп. пакеты для Python
   
   ```
   pip install -r requirements.txt
   ```

## Способ использования

1. Разместить xml в каталог in 
2. Запустить kptRun.bat
3. Забрать результат из каталога out

## Ограничение

Поддерживает только земельные участки

