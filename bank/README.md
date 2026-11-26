# Семинар на Bank Marketing

- `output/Seminar_BankMarketing.xlsx` — книга: все числа считаются формулами от листа «Данные»;
  вручную (жёлтые ячейки) только границы групп в таблицах и год первой строки. Диаграммы — Excel, по ячейкам.
- `output/Otchet_seminar_Bank.docx` — отчёт (2 стр. + графики); числа взяты из пересчитанной книги.

Пересборка:
```
python3 build.py <файл студента.xlsx> output
soffice --headless --convert-to xlsx --outdir recalc output/Seminar_BankMarketing.xlsx   # пересчёт формул
python3 report.py recalc/Seminar_BankMarketing.xlsx output
```
