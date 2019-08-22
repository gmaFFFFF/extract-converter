# Конвертирование выписок Росреестра в Esri Shape

Автор: Гришкин Максим

Лицензия: MIT License

## Настройка среды

1. Установить Python минимум версии 3.7. Рекомендую [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 

- Создать виртуальную среду (согласно инструкции к [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html))

- В файле kptRun.bat уточнить путь к интерпретатуру python 
  
   ```
   @CALL C:\Anaconda3\Scripts\activate.bat C:\Anaconda3\envs\dev
   ```
   
- Установить доп. пакеты для Python
  
   ```
   pip install -r requirements.txt
   ```

## Способ использования

1. Разместить xml в каталог in 
2. Запустить kptRun.bat
3. Забрать результат из каталога out
4. Bat'ник зациклен

## Ограничение

Поддерживает только земельные участки

## История изменений

**22.08.2019**
- Распознается название категории земель
- Уменьшено потребление оперативной памяти на больших xml

**20.08.2019**

- Добавлен экспорт в MS SQL Server query INSERT
- Переход на последнюю версию Python
- Переход на свежие библиотеки
- Улучшена производительность