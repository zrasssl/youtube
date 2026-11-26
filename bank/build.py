"""Книга Excel по семинару на Bank Marketing.

Каждое число в книге — формула от листа «Данные». Вручную введены только:
сырые данные (A–Q), подписи и тексты выводов, ожидаемые знаки (их пишут до расчёта),
границы групп в таблицах и год первой строки (из описания датасета) — эти ячейки залиты жёлтым.
Все диаграммы — диаграммы Excel по ячейкам книги, без картинок.

Запуск: python3 build.py <файл студента.xlsx> <out_dir>
"""
import sys, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.chart import ScatterChart, LineChart, Reference, Series
from openpyxl.chart.legend import Legend

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
raw = pd.read_excel(src, sheet_name="Данные", usecols="A:Q")
N = len(raw); last = N + 1

wb = Workbook()
H1 = Font(bold=True, size=12); B = Font(bold=True); NOTE = Font(italic=True, color="666666")
FILL = PatternFill("solid", fgColor="DDE8F8"); INPUT = PatternFill("solid", fgColor="FFF2CC")


def header(ws, row, vals, col=1):
    for j, v in enumerate(vals):
        c = ws.cell(row, col + j, v); c.font = B; c.fill = FILL
        c.alignment = Alignment(wrap_text=True, vertical="top")


def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[L(i)].width = x


def lines(ws, row, items, col=1):
    """Строки текста; строка, начинающаяся с «=», — формула (числа подставляются из ячеек)."""
    for i, t in enumerate(items):
        ws.cell(row + i, col, t)
    return row + len(items)


def title(ws, cell, text, font=H1):
    ws[cell] = text; ws[cell].font = font


def axes(ch, xt, yt, w=15, h=8):
    ch.x_axis.title, ch.y_axis.title = xt, yt
    ch.width, ch.height = w, h
    ch.legend = None
    ch.x_axis.delete = False; ch.y_axis.delete = False
    return ch


def scatter(sheet, name, xcol, ycol, xt, yt):
    ch = ScatterChart(); ch.title = name; ch.style = 13
    x = Reference(sheet, min_col=xcol, min_row=2, max_row=last)
    y = Reference(sheet, min_col=ycol, min_row=2, max_row=last)
    s = Series(y, x); s.marker.symbol = "circle"; s.marker.size = 3
    s.graphicalProperties.line.noFill = True
    ch.series.append(s)
    return axes(ch, xt, yt)


# ============================================================ Данные
wsD = wb.active; wsD.title = "Данные"
cols = list(raw.columns); cols[12] = "campaign"          # в исходнике заголовок был пустым
# числовой блок R:X; факторы регрессии идут подряд (R:V) — так нужно для ЛИНЕЙН
NUM = [("age", "Возраст", "=A{r}"),
       ("balance", "Баланс, €", "=F{r}"),
       ("housing", "Жилищный кредит (1/0)", '=IF(G{r}="yes",1,0)'),
       ("campaign", "Звонков в кампании", "=M{r}"),
       ("prev", "Успех прошлой кампании (1/0)", '=IF(P{r}="success",1,0)'),
       ("duration", "Длительность звонка, сек", "=L{r}"),
       ("y", "Открыл вклад (1/0)", '=IF(Q{r}="yes",1,0)')]
C = {k: L(18 + i) for i, (k, _, _) in enumerate(NUM)}         # R..X
extra = ["Прогноз модели", "Остаток", "Длительность без 1% крупнейших", "Вклад (те же строки)", "№ месяца", "Год"]
header(wsD, 1, cols + [n for _, n, _ in NUM] + extra)
CO = lambda r_: f"Регрессия!$B${r_}"   # коэффициенты в таблице 2.3 (строки 22–27)
for i in range(N):
    r = i + 2
    for j, v in enumerate(raw.iloc[i].tolist(), 1):
        wsD.cell(r, j, v)
    for k, _, f in NUM:
        wsD[f"{C[k]}{r}"] = f.format(r=r)
    wsD[f"Y{r}"] = f"={CO(22)}+{CO(23)}*R{r}+{CO(24)}*S{r}+{CO(25)}*T{r}+{CO(26)}*U{r}+{CO(27)}*V{r}"
    wsD[f"Z{r}"] = f"=X{r}-Y{r}"
    wsD[f"AA{r}"] = f'=IF(W{r}<=Связи!$B$52,W{r},"")'
    wsD[f"AB{r}"] = f'=IF(W{r}<=Связи!$B$52,X{r},"")'
    wsD[f"AC{r}"] = f'=MATCH(K{r},{{"jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"}},0)'
    wsD[f"AD{r}"] = "=Прогноз!$O$2" if r == 2 else f"=AD{r-1}+IF(AC{r}<AC{r-1},1,0)"
wsD.freeze_panes = "A2"


def rng(k):
    return f"Данные!${C[k]}$2:${C[k]}${last}"


# ============================================================ Связи
wsK = wb.create_sheet("Связи")
V = ["age", "balance", "housing", "campaign", "prev", "duration", "y"]
SHORT = {"age": "Возраст", "balance": "Баланс", "housing": "Жилищный кредит", "campaign": "Звонков в кампании",
         "prev": "Успех прошлой кампании", "duration": "Длительность звонка", "y": "Открыл вклад"}
title(wsK, "A1", "1.1. Корреляционная матрица")
header(wsK, 2, ["Показатель"] + [SHORT[v] for v in V])
for i, a in enumerate(V):
    wsK.cell(3 + i, 1, SHORT[a]).font = B
    for j, b in enumerate(V):
        wsK.cell(3 + i, 2 + j, f"=CORREL({rng(a)},{rng(b)})").number_format = "0.000"
title(wsK, "A11", "1.2. Связи показателей")
header(wsK, 12, ["Связь показателей", "Корреляция", "Интерпретация", "|r| > 0,3?", "Механическая?", "Почему / рабочая гипотеза"])
ORDER = [("duration", "y"), ("prev", "y"), ("age", "housing"), ("housing", "y"), ("age", "balance"), ("housing", "prev"),
         ("campaign", "duration"), ("campaign", "y"), ("balance", "housing"), ("campaign", "prev"), ("balance", "y"),
         ("prev", "duration"), ("age", "prev"), ("balance", "prev"), ("age", "y"), ("housing", "campaign"),
         ("balance", "duration"), ("balance", "campaign"), ("housing", "duration"), ("age", "campaign"), ("age", "duration")]
WHY = {("duration", "y"): ("да", "Через время: длительность известна только после звонка, успешный звонок длиннее — это следствие, а не причина"),
       ("prev", "y"): ("нет", "Кто согласился в прошлый раз, соглашается снова: есть сбережения и доверие к банку")}
for k, (a, b) in enumerate(ORDER):
    r = 13 + k
    wsK.cell(r, 1, f"{SHORT[a]} — {SHORT[b]}")
    wsK.cell(r, 2, f"={L(2 + V.index(b))}{3 + V.index(a)}").number_format = "0.000"
    wsK.cell(r, 3, f'=IF(ABS(B{r})<0.1,"практически отсутствует",IF(ABS(B{r})<0.3,"слабая",IF(ABS(B{r})<0.5,"умеренная","сильная"))'
                   f'&IF(B{r}>0," положительная"," отрицательная"))')
    wsK.cell(r, 4, f'=IF(ABS(B{r})>0.3,"да","нет")')
    m, why = WHY.get((a, b), ("—", "—"))
    wsK.cell(r, 5, m); wsK.cell(r, 6, why)
title(wsK, "A35", "1.3. Три проверки")
title(wsK, "A36", "Проверка 1. Диаграммы рассеяния (справа) и доли открывших вклад", B)
header(wsK, 37, ["Длительность от, сек", "до, сек", "Звонков", "Доля открывших"])
for k, (lo, hi) in enumerate([(0, 120), (120, 240), (240, 480), (480, 900), (900, 99999)]):
    r = 38 + k
    for j, v in ((1, lo), (2, hi)):
        c = wsK.cell(r, j, v); c.fill = INPUT
    wsK.cell(r, 3, f'=COUNTIFS({rng("duration")},">="&A{r},{rng("duration")},"<"&B{r})')
    wsK.cell(r, 4, f'=AVERAGEIFS({rng("y")},{rng("duration")},">="&A{r},{rng("duration")},"<"&B{r})').number_format = "0%"
header(wsK, 44, ["Успех прошлой кампании", "", "Клиентов", "Доля открывших"])
for k, v in enumerate([0, 1]):
    r = 45 + k
    wsK.cell(r, 1, "да" if v else "нет")
    wsK.cell(r, 3, f"=COUNTIF({rng('prev')},{v})")
    wsK.cell(r, 4, f"=AVERAGEIF({rng('prev')},{v},{rng('y')})").number_format = "0%"
lines(wsK, 48, [
    '="Длительность → вклад: связь нелинейная — доля открывших растёт с "&FIXED(D38*100,0)&"% до "&FIXED(D42*100,0)&"%, но не по прямой."',
    '="Прошлый успех → вклад: обе переменные 0/1, на диаграмме 4 точки. Открыли вклад "&FIXED(D46*100,0)&"% с прошлым успехом и "&FIXED(D45*100,0)&"% без него."',
])
title(wsK, "A51", "Проверка 2. Выбросы: длительность звонка → вклад", B)
for r, (lab, f, nf) in enumerate([
        ("Порог: 99-й процентиль длительности, сек", f"=PERCENTILE({rng('duration')},0.99)", "0"),
        ("r по всем клиентам", f"=CORREL({rng('duration')},{rng('y')})", "0.000"),
        ("r без 1% самых длинных звонков", f"=CORREL(Данные!$AA$2:$AA${last},Данные!$AB$2:$AB${last})", "0.000"),
        ("Убрано звонков", f'=COUNTIF({rng("duration")},">"&B52)', "0")], 52):
    wsK.cell(r, 1, lab); wsK.cell(r, 2, f).number_format = nf
wsK["A56"] = '="Вывод: r изменился с "&FIXED(B53,3)&" до "&FIXED(B54,3)&" — связь держится на всех клиентах, а не на нескольких рекордных звонках."'
title(wsK, "A58", "Проверка 3. Механизм связи «успех прошлой кампании → вклад»", B)
header(wsK, 59, ["Показатель", "Успех был", "Успеха не было"])
for k, (lab, col, nf) in enumerate([("Средний баланс, €", "balance", "0"), ("Доля с жилищным кредитом", "housing", "0%"),
                                    ("Средний возраст", "age", "0.0")]):
    r = 60 + k
    wsK.cell(r, 1, lab)
    wsK.cell(r, 2, f"=AVERAGEIF({rng('prev')},1,{rng(col)})").number_format = nf
    wsK.cell(r, 3, f"=AVERAGEIF({rng('prev')},0,{rng(col)})").number_format = nf
wsK.cell(63, 1, "Доля клиентов, с кем банк связывался раньше")
wsK.cell(63, 2, f'=COUNTIF(Данные!$N$2:$N${last},"<>-1")/COUNT(Данные!$N$2:$N${last})').number_format = "0%"
lines(wsK, 65, [
    '="• Общая причина — да: у клиентов с прошлым успехом больше денег на счёте ("&FIXED(B60,0)&" € против "&FIXED(C60,0)&" €) и реже ипотека. Кто копит, соглашается и тогда, и сейчас."',
    '="• Отбор — да: прошлый успех бывает только у "&FIXED(B63*100,0)&"% клиентов, которым банк уже звонил, а кого обзванивать повторно, банк выбирал сам."',
    "• Обратная причинность — нет: прошлая кампания была раньше, будущее не влияет на прошлое.",
    "Вывод: связь помогает выбрать, кому звонить, но не доказывает, что прошлый успех сам повышает шанс.",
])
wsK.add_chart(scatter(wsD, "Длительность звонка → открыл вклад", 23, 24, "Длительность, сек", "Открыл вклад (0/1)"), "H36")
wsK.add_chart(scatter(wsD, "Успех прошлой кампании → открыл вклад", 22, 24, "Успех прошлой кампании (0/1)", "Открыл вклад (0/1)"), "H52")
widths(wsK, [42, 13, 28, 13, 15, 100, 13, 13])

# ============================================================ Регрессия
wsR = wb.create_sheet("Регрессия")
FACT = ["age", "balance", "housing", "campaign", "prev"]
title(wsR, "A1", "2.1. Постановка. Y = открыл вклад (1/0). Ожидаемые знаки записаны до расчёта")
header(wsR, 2, ["Фактор", "Входит в формулу Y?", "Ожидаемый знак", "Почему так ожидаем"])
EXP = {"age": ("+", "у старших больше сбережений"), "balance": ("+", "есть свободные деньги"),
       "housing": ("−", "деньги уходят на ипотеку"), "campaign": ("−", "кого уговаривают много раз, тот скорее откажет"),
       "prev": ("+", "уже открывал вклад и остался доволен")}
for k, f in enumerate(FACT):
    for j, v in enumerate([SHORT[f], "нет", EXP[f][0], EXP[f][1]], 1):
        wsR.cell(3 + k, j, v)
title(wsR, "A8", "Длительность звонка не включена: она известна только после результата (механическая связь).", NOTE)
title(wsR, "A10", "2.2. Расчёт: ЛИНЕЙН с полной статистикой (Excel выдаёт факторы в обратном порядке)")
header(wsR, 11, [SHORT[f] for f in reversed(FACT)] + ["Пересечение"], col=9)
wsR["I12"] = ArrayFormula("I12:N16", f"=IFERROR(LINEST({rng('y')},Данные!$R$2:$V${last},1,1),\"\")")
for k, lab in enumerate(["коэффициент", "ст. ошибка", "R² | ст. ош.", "F | df", "SS"]):
    wsR.cell(12 + k, 8, lab).font = NOTE
title(wsR, "A20", "2.3. Значимость и интерпретация")
header(wsR, 21, ["Фактор", "Коэффициент", "Ст. ошибка", "t", "p-значение", "Значим?", "Знак совпал?", "Интерпретация"])
TXT = {"age": ("При увеличении возраста на 1 год", 1), "balance": ("При увеличении баланса на 1 000 €", 1000),
       "housing": ("При наличии жилищного кредита", 1), "campaign": ("При увеличении числа звонков на 1", 1),
       "prev": ("При успехе прошлой кампании", 1)}
for k, f in enumerate(["const"] + FACT):
    r = 22 + k
    col = "N" if f == "const" else L(9 + len(FACT) - 1 - FACT.index(f))
    wsR.cell(r, 1, "Пересечение" if f == "const" else SHORT[f])
    wsR.cell(r, 2, f"={col}12").number_format = "0.000000"
    wsR.cell(r, 3, f"={col}13").number_format = "0.000000"
    wsR.cell(r, 4, f"=B{r}/C{r}").number_format = "0.00"
    wsR.cell(r, 5, f"=TDIST(ABS(D{r}),$J$15,2)").number_format = "0.0000"
    wsR.cell(r, 6, f'=IF(E{r}<0.05,"да","нет")')
    if f != "const":
        e = 3 + FACT.index(f)
        wsR.cell(r, 7, f'=IF(C{e}="+",IF(B{r}>0,"да","нет"),IF(B{r}<0,"да","нет"))')
        what, mult = TXT[f]
        wsR.cell(r, 8, f'=IF(E{r}>=0.05,"Связи не обнаружено","{what} вероятность открыть вклад в среднем меняется на "'
                       f'&FIXED(B{r}*{mult}*100,2)&" п.п., если остальные учтённые факторы не меняются")')
for r, (lab, f, nf) in enumerate([
        ("R²", "=I14", "0.000"),
        ("Наблюдений", f"=COUNT({rng('y')})", "0"),
        ("Проверка на круговую зависимость: R², если добавить длительность звонка",
         f"=INDEX(LINEST({rng('y')},Данные!$R$2:$W${last},1,1),3,1)", "0.000")], 29):
    wsR.cell(r, 1, lab).font = B; wsR.cell(r, 2, f).number_format = nf
title(wsR, "A33", "Остатки (графики справа)")
header(wsR, 34, ["Возраст от", "до", "Средний остаток"])
for k, (lo, hi) in enumerate([(18, 25), (25, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 100)]):
    r = 35 + k
    for j, v in ((1, lo), (2, hi)):
        c = wsR.cell(r, j, v); c.fill = INPUT
    wsR.cell(r, 3, f'=AVERAGEIFS(Данные!$Z$2:$Z${last},{rng("age")},">="&A{r},{rng("age")},"<"&B{r})').number_format = "0.000"
wsR["A43"] = "Отрицательных прогнозов вероятности"; wsR["B43"] = f'=COUNTIF(Данные!$Y$2:$Y${last},"<0")'
lines(wsR, 45, [
    "Анализ остатков: структура есть, форма модели неверна.",
    "• Две полосы на графике — так всегда бывает, когда Y равен 0 или 1.",
    '="• "&B43&" прогнозов вероятности меньше нуля — так быть не может."',
    '="• Изгиб по возрасту: средний остаток "&FIXED(C35,2)&" у молодых, около нуля в 30–60 лет и "&FIXED(C41,2)&" у 70+. Молодые и пожилые открывают вклады чаще, чем предсказывает прямая."',
    "",
    "2.4. Честный вывод",
    '="Модель объясняет "&FIXED(B29*100,0)&"% различий между клиентами. Главное — прошлый успех и свободные деньги (нет ипотеки, есть баланс)."',
    '="Не объяснено "&FIXED(100-B29*100,0)&"%: доход вне банка, ставки конкурентов, время и качество звонка, жизненные события — этого нет в данных."',
    '="R² низкий, круговой зависимости нет. С длительностью звонка R² вырос бы до "&FIXED(B31,3)&" — за счёт механической переменной, поэтому её в модели нет."',
])
wsR["A50"].font = H1
wsR.add_chart(scatter(wsD, "Остатки против прогноза", 25, 26, "Прогноз модели", "Остаток"), "J20")
lc = LineChart(); lc.title = "Средний остаток по возрасту"; lc.style = 12
lc.add_data(Reference(wsR, min_col=3, min_row=34, max_row=41), titles_from_data=True)
lc.set_categories(Reference(wsR, min_col=1, min_row=35, max_row=41))
wsR.add_chart(axes(lc, "Возраст (начало группы)", "Средний остаток"), "J37")
widths(wsR, [30, 13, 13, 9, 12, 9, 12, 100, 13, 13, 13, 13, 13, 13])

# ============================================================ Прогноз
wsP = wb.create_sheet("Прогноз")
title(wsP, "A1", "Части 3–4. Ряд: число открытых вкладов по месяцам")
title(wsP, "A2", "Год восстановлен по порядку строк: данные идут по датам, год растёт, когда номер месяца уменьшается. "
                 "Ноябрь 2010 неполный (до 17-го) — не включён.", NOTE)
wsP["M2"] = "Год первой строки (из описания датасета UCI)"; wsP["O2"] = 2008; wsP["O2"].fill = INPUT
header(wsP, 4, ["Месяц", "t", "Открыто вкладов", "Звонков", "Обучение (1/0)", "Скольз. ср. 12 мес.", "№ месяца",
                "Сез. индекс", "Тренд", "Прогноз (тренд × индекс)", "Ошибка, %"])
NM = 30; F0 = 5; LR = F0 + NM - 1                     # строки 5–34: май 2008 – окт 2010
DY, DM = f"Данные!$AD$2:$AD${last}", f"Данные!$AC$2:$AC${last}"
TR = f"$E${F0}:$E${LR}"
for i in range(NM):
    r = F0 + i
    wsP.cell(r, 1, "=DATE(Данные!AD2,Данные!AC2,1)" if i == 0 else f"=EDATE(A{r-1},1)").number_format = "mmm yyyy"
    wsP.cell(r, 2, f"=ROW()-{F0 - 1}")
    wsP.cell(r, 3, f"=COUNTIFS({DY},YEAR(A{r}),{DM},MONTH(A{r}),{rng('y')},1)")
    wsP.cell(r, 4, f"=COUNTIFS({DY},YEAR(A{r}),{DM},MONTH(A{r}))")
    wsP.cell(r, 5, f"=IF(B{r}<=MAX($B${F0}:$B${LR})-3,1,0)")
    if i >= 11:
        wsP.cell(r, 6, f"=AVERAGE(C{r-11}:C{r})").number_format = "0"
    wsP.cell(r, 7, f"=MONTH(A{r})")
    wsP.cell(r, 8, f"=VLOOKUP(G{r},$M$12:$N$23,2,FALSE)").number_format = "0.00"
    wsP.cell(r, 9, f"=$O$6+$O$5*B{r}").number_format = "0"
    wsP.cell(r, 10, f"=I{r}*H{r}").number_format = "0"
    wsP.cell(r, 11, f'=IF(E{r}=0,ABS(C{r}-J{r})/C{r}*100,"")').number_format = "0"
TL = LR - 3   # последняя обучающая строка
for k, (lab, f, nf) in enumerate([
        ("Наклон тренда (обучение)", f"=SLOPE(C{F0}:C{TL},B{F0}:B{TL})", "0.00"),
        ("Пересечение (обучение)", f"=INTERCEPT(C{F0}:C{TL},B{F0}:B{TL})", "0.0"),
        ("Средний уровень (обучение)", f"=AVERAGE(C{F0}:C{TL})", "0.0")]):
    wsP.cell(5 + k, 13, lab).font = B
    wsP.cell(5 + k, 15, f).number_format = nf
title(wsP, "M9", "3.3. Сезонные индексы (по обучающим месяцам)")
header(wsP, 11, ["№ мес.", "Индекс", "Значений"], col=13)
for k in range(12):
    r = 12 + k
    wsP.cell(r, 13, "=ROW()-11")
    wsP.cell(r, 14, f"=AVERAGEIFS($C${F0}:$C${LR},$G${F0}:$G${LR},M{r},{TR},1)/$O$7").number_format = "0.00"
    wsP.cell(r, 15, f"=COUNTIFS($G${F0}:$G${LR},M{r},{TR},1)")
r0 = LR + 2
title(wsP, f"A{r0}", "4.1–4.2. Проверка на последних 3 месяцах")
header(wsP, r0 + 1, ["Месяц", "Факт", "Модель", "Ошибка, %", "Как в прошлом месяце", "Ошибка, %", "Как год назад", "Ошибка, %"])
for k in range(3):
    r, s = r0 + 2 + k, TL + 1 + k
    wsP.cell(r, 1, f"=A{s}").number_format = "mmm yyyy"
    wsP.cell(r, 2, f"=C{s}")
    wsP.cell(r, 3, f"=J{s}").number_format = "0"
    wsP.cell(r, 5, f"=$C${TL}")
    wsP.cell(r, 7, f"=C{s - 12}")
    for c in (3, 5, 7):
        wsP.cell(r, c + 1, f"=ABS(B{r}-{L(c)}{r})/B{r}*100").number_format = "0"
MR = r0 + 5
wsP.cell(MR, 1, "MAPE, %").font = B
for c in (4, 6, 8):
    wsP.cell(MR, c, f"=AVERAGE({L(c)}{r0+2}:{L(c)}{r0+4})").number_format = "0.0"
title(wsP, f"A{MR + 1}", "«Как в прошлом месяце» = последний месяц до проверки, на все три месяца (других данных на момент прогноза нет).", NOTE)
fr = MR + 3
title(wsP, f"A{fr}", "3.4. Прогноз на 3 месяца вперёд")
header(wsP, fr + 1, ["Месяц", "t", "№ мес.", "Индекс", "Тренд", "Прогноз", "Нижняя граница", "Верхняя граница"])
for k in range(3):
    r = fr + 2 + k
    wsP.cell(r, 1, f"=EDATE(A{LR if k == 0 else r - 1},1)").number_format = "mmm yyyy"
    wsP.cell(r, 2, f"=B{LR}+{k + 1}")
    wsP.cell(r, 3, f"=MONTH(A{r})")
    wsP.cell(r, 4, f"=VLOOKUP(C{r},$M$12:$N$23,2,FALSE)").number_format = "0.00"
    wsP.cell(r, 5, f"=$O$6+$O$5*B{r}").number_format = "0"
    wsP.cell(r, 6, f"=E{r}*D{r}").number_format = "0"
    wsP.cell(r, 7, f"=MAX(F{r}*(1-MAX($D${r0+2}:$D${r0+4})/100),0)").number_format = "0"
    wsP.cell(r, 8, f"=F{r}*(1+MAX($D${r0+2}:$D${r0+4})/100)").number_format = "0"
title(wsP, f"A{fr + 5}", "Границы = прогноз ± худшая ошибка модели на проверке.", NOTE)
title(wsP, f"A{fr + 7}", "Выводы")
lines(wsP, fr + 8, [
    f'="3.1. В ряду "&COUNT(C{F0}:C{LR})&" месяцев — "&INT(COUNT(C{F0}:C{LR})/12)&" полных годовых цикла. Звонков в месяц — от "&MIN(D{F0}:D{LR})&" до "&MAX(D{F0}:D{LR})&": ряд неоднородный."',
    f'="3.2. Скользящее среднее: "&FIXED(F16,0)&" в апреле 2009, максимум "&FIXED(MAX(F16:F{LR}),0)&", в конце "&FIXED(F{LR},0)&" — сначала растёт, с весны 2010 падает."',
    '="3.3. Самый сильный месяц — "&MATCH(MAX(N12:N23),N12:N23,0)&"-й (индекс "&FIXED(MAX(N12:N23),2)&"), самый слабый — "&MATCH(MIN(N12:N23),N12:N23,0)&"-й ("&FIXED(MIN(N12:N23),2)&")."',
    "      Это не спрос клиентов, а график кампаний банка: в мае банк звонил больше всего, в сентябре и декабре 2008 почти не звонил.",
    f'="4.3. Модель НЕ бьёт наивный прогноз: MAPE "&FIXED(D{MR},1)&"% против "&FIXED(F{MR},1)&"% у «как в прошлом месяце» (у «как год назад» — "&FIXED(H{MR},1)&"%)."',
    "      Горизонт — не больше месяца: у каждого месяца года всего 2–3 значения, а годы не похожи друг на друга.",
    "      Прогноз сломают: 1) банк запустит или свернёт кампанию; 2) изменятся ставки по вкладам (решения ЕЦБ, ставки конкурентов).",
])
lc = LineChart(); lc.title = "Открытые вклады по месяцам"; lc.style = 12
for c in (3, 6, 10):
    lc.add_data(Reference(wsP, min_col=c, min_row=4, max_row=LR), titles_from_data=True)
lc.set_categories(Reference(wsP, min_col=1, min_row=F0, max_row=LR))
lc.x_axis.number_format = "mmm yy"
axes(lc, "Месяц", "Вкладов", w=22, h=9)
lc.legend = Legend(); lc.legend.position = "b"
wsP.add_chart(lc, "Q4")
widths(wsP, [12, 5, 11, 9, 9, 11, 8, 10, 9, 12, 10, 3, 42, 9, 10])

wb.save(f"{out}/Seminar_BankMarketing.xlsx")
print("saved")
