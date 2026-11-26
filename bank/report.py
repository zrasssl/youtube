"""Короткий отчёт (docx). Все числа берутся из книги, пересчитанной Excel/LibreOffice.
Запуск: python3 report.py <пересчитанная книга.xlsx> <out_dir>
"""
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import load_workbook
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

src, out = sys.argv[1], sys.argv[2]
wb = load_workbook(src, data_only=True)
K, R, P_ = wb["Связи"], wb["Регрессия"], wb["Прогноз"]
v = lambda ws, c: ws[c].value
d = pd.read_excel(src, sheet_name="Данные", usecols="R:Z")
d.columns = ["age", "balance", "housing", "campaign", "prev", "duration", "y", "pred", "res"]


def f(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


# ---------- простые графики (те же, что в Excel)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
BLUE = "#2a6fdb"
fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
ax[0].scatter(d.duration, d.y, s=4, color=BLUE); ax[0].set(xlabel="Длительность звонка, сек", ylabel="Открыл вклад (0/1)", title="Длительность → вклад")
ax[1].scatter(d.prev, d.y, s=30, color=BLUE); ax[1].set(xlabel="Успех прошлой кампании (0/1)", ylabel="Открыл вклад (0/1)", title="Прошлый успех → вклад", xticks=[0, 1], yticks=[0, 1])
fig.tight_layout(); fig.savefig(f"{out}/1_scatter.png", dpi=130); plt.close(fig)

fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
ax[0].scatter(d.pred, d.res, s=3, color=BLUE); ax[0].axhline(0, color="grey", lw=1)
ax[0].set(xlabel="Прогноз модели", ylabel="Остаток", title="Остатки против прогноза")
ages = [f"{v(R, f'A{r}')}" for r in range(35, 42)]; res = [v(R, f"C{r}") for r in range(35, 42)]
ax[1].plot(ages, res, "-o", color=BLUE); ax[1].axhline(0, color="grey", lw=1)
ax[1].set(xlabel="Возраст (начало группы)", ylabel="Средний остаток", title="Средний остаток по возрасту")
fig.tight_layout(); fig.savefig(f"{out}/2_residuals.png", dpi=130); plt.close(fig)

months = [v(P_, f"A{r}") for r in range(5, 35)]
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.plot(months, [v(P_, f"C{r}") for r in range(5, 35)], "-o", ms=3, color=BLUE, label="Открыто вкладов")
ax.plot(months, [v(P_, f"F{r}") for r in range(5, 35)], color="#e07a1f", lw=2, label="Скользящее среднее 12 мес.")
ax.plot(months, [v(P_, f"J{r}") for r in range(5, 35)], "--", color="grey", label="Тренд × индекс")
ax.set(ylabel="Вкладов", title="Открытые вклады по месяцам"); ax.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(f"{out}/3_series.png", dpi=130); plt.close(fig)

# ---------- документ
doc = Document()
sec = doc.sections[0]; sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2); sec.top_margin = sec.bottom_margin = Cm(1.6)
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5); st.paragraph_format.space_after = Pt(4)
doc.styles["Heading 1"].font.size = Pt(13); doc.styles["Heading 1"].font.color.rgb = RGBColor(0x1F, 0x3B, 0x73)


def P(text, lead=None):
    p = doc.add_paragraph()
    if lead: p.add_run(lead).bold = True
    p.add_run(text)


def T(rows, widths):
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Light Grid Accent 1"; t.autofit = False
    for j, w in enumerate(widths): t.columns[j].width = Cm(w)
    for i, row in enumerate(rows):
        for j, x in enumerate(row):
            c = t.cell(i, j); c.width = Cm(widths[j]); c.text = ""
            r = c.paragraphs[0].add_run(str(x)); r.font.size = Pt(9.5); r.bold = i == 0
    doc.add_paragraph()


h = doc.add_heading("Связи, регрессия и прогноз: Bank Marketing", 0); h.runs[0].font.size = Pt(16)
P(f"Данные: {f(v(R, 'B30'))} клиентов банка, которым звонили с предложением открыть вклад. Все расчёты — формулами в книге Seminar_BankMarketing.xlsx.")

doc.add_heading("1. Связи", 1)
P("В матрицу вошли 7 показателей: возраст, баланс, жилищный кредит, звонков в кампании, успех прошлой кампании, длительность звонка, открыл вклад. "
  "Пар с |r| > 0,3 две:")
T([["Связь", "r", "Механическая?", "Почему / гипотеза"],
   ["Длительность звонка — открыл вклад", f(v(K, "B13"), 2), "да", "длительность известна только после звонка — это следствие согласия"],
   ["Успех прошлой кампании — открыл вклад", f(v(K, "B14"), 2), "нет", "кто согласился раньше, соглашается снова"]],
  [5.5, 1.2, 2.3, 8])
P(f"Обе связи на диаграммах нелинейные (рис. 1): доля открывших растёт с {f(v(K, 'D38') * 100)}% у коротких звонков до {f(v(K, 'D42') * 100)}% у длинных; "
  f"с прошлым успехом вклад открыли {f(v(K, 'D46') * 100)}%, без него — {f(v(K, 'D45') * 100)}%.", "Проверка 1. ")
P(f"Без 1% самых длинных звонков r почти не меняется: {f(v(K, 'B53'), 3)} → {f(v(K, 'B54'), 3)}. Связь держится не на выбросах.", "Проверка 2. ")
P(f"Связь «прошлый успех → вклад» может объясняться общей причиной: у таких клиентов больше денег ({f(v(K, 'B60'))} € против {f(v(K, 'C60'))} €) и реже ипотека. "
  f"Возможен и отбор: прошлый успех есть только у {f(v(K, 'B63') * 100)}% клиентов, которым банк уже звонил. "
  "Обратная причинность исключена: прошлая кампания была раньше. Связь помогает выбрать, кому звонить, но не доказывает причину.", "Проверка 3. ")

doc.add_heading("2. Модель", 1)
P("Y — открыл вклад (1/0). Факторы: возраст, баланс, жилищный кредит, число звонков, успех прошлой кампании. "
  "Ни один не входит в формулу Y. Длительность звонка не включена, потому что связь механическая.")
rows = [["Фактор", "Ожид. знак", "Коэффициент", "p-значение", "Значим?", "Знак совпал?"]]
for r in range(23, 28):
    rows.append([v(R, f"A{r}"), v(R, f"C{r - 20}"), f"{v(R, f'B{r}'):.5f}".replace(".", ","),
                 "< 0,001" if v(R, f"E{r}") < 0.001 else f(v(R, f"E{r}"), 3), v(R, f"F{r}"), v(R, f"G{r}")])
T(rows, [4.8, 2, 2.6, 2.4, 2, 2.6])
P(f"При успехе прошлой кампании вероятность открыть вклад в среднем выше на {f(v(R, 'B27') * 100, 1)} п.п., при жилищном кредите — ниже на "
  f"{f(-v(R, 'B25') * 100, 1)} п.п., каждый лишний звонок снижает её на {f(-v(R, 'B26') * 100, 2)} п.п., каждые 1 000 € баланса добавляют "
  f"{f(v(R, 'B24') * 100000, 2)} п.п. (при прочих равных). У возраста знак не совпал с ожиданием.", "Коэффициенты. ")
P(f"Форма модели неверна (рис. 2): остатки лежат двумя полосами, {v(R, 'B43')} прогнозов вероятности меньше нуля, "
  f"а по возрасту есть изгиб — у молодых и пожилых средний остаток положительный ({f(v(R, 'C35'), 2)} и {f(v(R, 'C41'), 2)}). "
  "Отсюда и «неправильный» знак возраста: зависимость U-образная, а не прямая.", "Остатки. ")
P(f"R² = {f(v(R, 'B29'), 3)}. Модель объясняет около {f(v(R, 'B29') * 100)}% различий между клиентами, остальное — доход вне банка, ставки конкурентов, "
  f"качество звонка и жизненные события. С длительностью звонка R² вырос бы до {f(v(R, 'B31'), 3)}, но это эффект механической переменной.", "Вывод. ")

doc.add_heading("3. Прогноз", 1)
P("В данных нет года, но строки идут по датам (май 2008 – ноябрь 2010), поэтому год восстановлен по порядку строк. "
  "Ряд — число открытых вкладов в месяц, 30 месяцев (ноябрь 2010 неполный и не включён), 2 полных цикла.")
P(f"Скользящее среднее сначала растёт (максимум {f(max(v(P_, f'F{r}') for r in range(16, 35)))}), а с весны 2010 падает до {f(v(P_, 'F34'))}. "
  "Самый сильный месяц — май, самый слабый — декабрь. Это не спрос клиентов, а график кампаний банка: в 2008 году в сентябре и декабре почти не звонили (рис. 3).")
T([["Месяц", "Прогноз", "Границы"]] +
  [[v(P_, f"A{r}").strftime("%m.%Y"), f(v(P_, f"F{r}")), f"{f(v(P_, f'G{r}'))} – {f(v(P_, f'H{r}'))}"] for r in range(46, 49)], [3, 3, 4])

doc.add_heading("4. Проверка", 1)
T([["Прогноз", "MAPE, %"], ["Тренд × сезонность", f(v(P_, "D41"), 1)], ["Как в прошлом месяце", f(v(P_, "F41"), 1)],
   ["Как год назад", f(v(P_, "H41"), 1)]], [5, 3])
P("Модель не бьёт простой прогноз «как в прошлом месяце». Горизонт — не больше месяца: у каждого месяца всего 2–3 значения, а годы не похожи. "
  "Прогноз сломают: 1) запуск или остановка кампании банком; 2) изменение ставок по вкладам (ЕЦБ, конкуренты).")

doc.add_heading("5. Чего мы не знаем", 1)
for t in ["Какие ставки и условия предлагали клиентам.", "Как банк выбирал, кому звонить повторно.",
          "Доходы и сбережения клиентов вне банка.", "Работают ли выводы сейчас: данные 2008–2010 годов, время кризиса."]:
    doc.add_paragraph(t, style="List Bullet")

doc.add_page_break()
doc.add_heading("Приложение. Графики", 1)
for fn, cap in [("1_scatter.png", "Рис. 1. Диаграммы рассеяния"), ("2_residuals.png", "Рис. 2. Остатки регрессии"),
                ("3_series.png", "Рис. 3. Открытые вклады по месяцам")]:
    doc.add_picture(f"{out}/{fn}", width=Cm(16.5))
    p = doc.add_paragraph(cap); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
doc.save(f"{out}/Otchet_seminar_Bank.docx")
print("ok")
