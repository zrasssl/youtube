"""Семинар «Связи, регрессия, прогноз» на данных Online Retail II (UCI).

Запуск: python3 build.py <clean.pkl> <out_dir>
clean.pkl делает prep.py из online_retail_II.csv.
Строит: графики (PNG), книгу Excel с формулами, results.json с числами для отчёта.
"""
import json, sys, os
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter as L

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
R = {}
df = pd.read_pickle(src)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3 = "#2a6fdb", "#e07a1f", "#7a7a7a"

# ---------------------------------------------------------------- клиенты
cut, end = pd.Timestamp("2010-12-01"), pd.Timestamp("2011-12-01")
d = df[df["Customer ID"].notna()]
a = d[d.InvoiceDate < cut]
b = d[(d.InvoiceDate >= cut) & (d.InvoiceDate < end)]
g = a.groupby("Customer ID")
c = pd.DataFrame({
    "orders": g.Invoice.nunique(),
    "revenue": g.Revenue.sum(),
    "n_products": g.StockCode.nunique(),
    "units": g.Quantity.sum(),
    "first": g.InvoiceDate.min(),
    "last": g.InvoiceDate.max(),
    "active_months": g.InvoiceDate.apply(lambda s: s.dt.to_period("M").nunique()),
})
c["avg_check"] = c.revenue / c.orders
c["avg_price"] = c.revenue / c.units
c["lifetime_days"] = (c["last"] - c["first"]).dt.days
c["recency_days"] = (cut - c["last"]).dt.days
c["tenure_days"] = (cut - c["first"]).dt.days
c["revenue_next"] = b.groupby("Customer ID").Revenue.sum().reindex(c.index).fillna(0)
c.index = c.index.astype(int)

VARS = ["orders", "revenue", "avg_check", "n_products", "avg_price", "lifetime_days",
        "recency_days", "tenure_days", "active_months", "revenue_next"]
RU = {
    "orders": "Заказов (2010)", "revenue": "Выручка (2010), £", "avg_check": "Средний чек, £",
    "n_products": "Разных товаров", "avg_price": "Средняя цена ед., £", "lifetime_days": "Срок жизни, дн.",
    "recency_days": "Давность, дн.", "tenure_days": "Стаж клиента, дн.", "active_months": "Активных месяцев",
    "revenue_next": "Выручка след. 12 мес., £",
}
corr = c[VARS].corr()
R["n_customers"] = len(c)
R["corr"] = corr.round(3).to_dict()

# пары |r|>0.3 и их разметка (механическая / нет)
MECH = {
    ("orders", "revenue"): "Выручка = заказы × средний чек (формула)",
    ("revenue", "avg_check"): "Средний чек = выручка / заказы (формула)",
    ("orders", "n_products"): "Каждый заказ добавляет новые позиции: больше заказов — больше разных товаров при прочих равных (счётчик растёт с числом заказов)",
    ("orders", "lifetime_days"): "Через время: срок жизни = последняя − первая покупка; при 1 заказе он равен 0",
    ("orders", "tenure_days"): "Через время: чем раньше пришёл клиент, тем больше окно для заказов",
    ("orders", "active_months"): "Активный месяц существует только если в нём был заказ (активных месяцев ≤ заказов)",
    ("revenue", "n_products"): "Через формулу: выручка — сумма по строкам, больше разных позиций — больше строк",
    ("revenue", "active_months"): "Через заказы: активные месяцы ≤ заказов, а заказы входят в выручку",
    ("n_products", "active_months"): "Оба счётчика растут с числом заказов",
    ("n_products", "lifetime_days"): "Оба растут с числом заказов (общая механика окна)",
    ("lifetime_days", "recency_days"): "Через время: срок жизни + давность + (стаж − срок жизни − давность) = окно 12 мес.",
    ("lifetime_days", "tenure_days"): "Через время: срок жизни ≤ стаж по определению",
    ("lifetime_days", "active_months"): "Через время: больше месяцев между первой и последней покупкой",
    ("recency_days", "active_months"): "Через время: давно ушедший клиент не мог набрать активных месяцев в конце окна",
    ("tenure_days", "active_months"): "Через время: активных месяцев ≤ месяцев стажа",
    ("recency_days", "tenure_days"): "Через время: давность ≤ стаж",
}
HYP = {
    ("revenue", "revenue_next"): "Разные периоды, формулы не пересекаются. Гипотеза: размер бизнеса клиента устойчив — крупный оптовик остаётся крупным",
    ("orders", "revenue_next"): "Гипотеза: частота покупок отражает привычку/регулярный цикл закупок клиента, который сохраняется",
    ("avg_check", "revenue_next"): "Гипотеза: крупный чек = оптовый клиент с большим оборотом и в следующем году",
    ("n_products", "revenue_next"): "Гипотеза: широкий ассортимент = магазин-перепродавец, который закупает много и дальше",
    ("active_months", "revenue_next"): "Гипотеза: регулярность в прошлом году предсказывает объём в следующем",
    ("avg_check", "n_products"): "Гипотеза: оптовики берут и больше позиций, и больше на чек",
}
pairs = []
for i, x in enumerate(VARS):
    for y in VARS[i + 1:]:
        r = corr.loc[x, y]
        if abs(r) > 0.3:
            key = (x, y) if (x, y) in MECH or (x, y) in HYP else (y, x)
            mech = key in MECH
            pairs.append({"x": x, "y": y, "r": round(float(r), 2), "mech": mech,
                          "why": MECH.get(key) or HYP.get(key) or "—"})
R["pairs"] = pairs

# 1.3 диаграммы рассеяния
def scatter(x, y, fname, title):
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    ax[0].scatter(c[x], c[y], s=6, alpha=.35, color=C1)
    ax[0].set(xlabel=RU[x], ylabel=RU[y], title=f"{title}: все клиенты, r = {c[x].corr(c[y]):.2f}")
    ax[1].scatter(c[x], c[y], s=6, alpha=.35, color=C1)
    ax[1].set(xscale="symlog", yscale="symlog", xlabel=RU[x] + " (лог)", ylabel=RU[y] + " (лог)", title="Та же связь в логарифмах")
    fig.tight_layout(); fig.savefig(f"{out}/{fname}", dpi=130); plt.close(fig)

scatter("revenue", "revenue_next", "1_scatter_revenue.png", "Выручка 2010 → след. год")
scatter("orders", "revenue_next", "1_scatter_orders.png", "Заказы 2010 → выручка след. года")

# выбросы: убираем 1% крупнейших по каждой из переменных пары
def trim_r(x, y):
    q = c[x].quantile(.99), c[y].quantile(.99)
    t = c[(c[x] <= q[0]) & (c[y] <= q[1])]
    return float(c[x].corr(c[y])), float(t[x].corr(t[y])), len(c) - len(t)
R["outliers"] = {}
for x in ["revenue", "orders"]:
    r0, r1, n = trim_r(x, "revenue_next")
    R["outliers"][x] = {"r_all": round(r0, 3), "r_trim": round(r1, 3), "removed": n}
R["spearman"] = {x: round(float(c[x].corr(c.revenue_next, method="spearman")), 3) for x in ["revenue", "orders"]}

# ---------------------------------------------------------------- регрессия
FACT = ["orders", "avg_check", "n_products", "recency_days", "avg_price"]
EXP = {"orders": "+", "avg_check": "+", "n_products": "+", "recency_days": "−", "avg_price": "−"}
X = sm.add_constant(c[FACT]); m = sm.OLS(c.revenue_next, X).fit()
R["reg"] = {"r2": round(m.rsquared, 3), "r2adj": round(m.rsquared_adj, 3), "n": int(m.nobs),
            "se": round(float(np.sqrt(m.mse_resid)), 1),
            "coef": {k: {"b": float(m.params[k]), "p": float(m.pvalues[k]), "lo": float(m.conf_int().loc[k, 0]), "hi": float(m.conf_int().loc[k, 1])} for k in m.params.index}}
# проверка на робастность: та же модель в логарифмах (для раздела «форма модели»)
lc = c.copy()
for k in ["revenue_next", "orders", "avg_check", "n_products", "avg_price"]:
    lc[k] = np.log1p(lc[k])
ml = sm.OLS(lc.revenue_next, sm.add_constant(lc[FACT])).fit()
R["reg_log"] = {"r2": round(ml.rsquared, 3), "coef": {k: {"b": float(ml.params[k]), "p": float(ml.pvalues[k])} for k in ml.params.index}}
# без 1% крупнейших клиентов
q = c.revenue_next.quantile(.99); ct = c[c.revenue_next <= q]
mt = sm.OLS(ct.revenue_next, sm.add_constant(ct[FACT])).fit()
R["reg_trim"] = {"r2": round(mt.rsquared, 3), "coef": {k: {"b": float(mt.params[k]), "p": float(mt.pvalues[k])} for k in mt.params.index}}
R["zero_next_share"] = round(float((c.revenue_next == 0).mean()), 3)

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].scatter(m.fittedvalues, m.resid, s=6, alpha=.35, color=C1); ax[0].axhline(0, color=C3, lw=1)
ax[0].set(xlabel="Предсказанная выручка след. года, £", ylabel="Остаток, £", title="Остатки vs предсказание")
ax[1].scatter(m.fittedvalues, m.resid, s=6, alpha=.35, color=C1); ax[1].axhline(0, color=C3, lw=1)
ax[1].set(xlim=(-3000, 15000), ylim=(-20000, 20000), xlabel="Предсказание (увеличено, до £15 тыс.)", ylabel="Остаток, £", title="Увеличенный фрагмент: воронка")
fig.tight_layout(); fig.savefig(f"{out}/2_residuals.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- ряд
s = df.set_index("InvoiceDate").Revenue.resample("MS").sum()
s = s[s.index < "2011-12-01"]  # декабрь 2011 — только 9 дней, исключаем
R["series"] = {k.strftime("%Y-%m"): round(float(v), 2) for k, v in s.items()}
n = len(s); t = np.arange(1, n + 1); H = 3; tr = n - H
ma = s.rolling(12).mean()
month = s.index.month

def season(k):
    """индексы по первым k месяцам: средний уровень месяца / общий средний"""
    return s[:k].groupby(month[:k]).mean() / s[:k].mean()

idx = season(tr); I = idx.reindex(month).values
slope, icpt = np.polyfit(t[:tr], s.values[:tr] / I[:tr], 1)      # тренд по ряду без сезонности
slope_raw, icpt_raw = np.polyfit(t[:tr], s.values[:tr], 1)        # для сравнения: по сырому ряду
trend = icpt + slope * t
fc = trend * I
fc_raw = (icpt_raw + slope_raw * t) * I
hold = pd.DataFrame({"fact": s.values[tr:], "model": fc[tr:], "model_raw": fc_raw[tr:],
                     "naive_prev": [s.values[tr - 1]] * H,
                     "naive_prev_1step": s.values[tr - 1:n - 1],
                     "naive_year": s.values[tr - 12:n - 12]}, index=s.index[tr:].strftime("%Y-%m"))
ape = lambda f: (hold.fact - f).abs() / hold.fact * 100
R["holdout"] = {col: {"values": hold[col].round(0).tolist(), "ape": ape(hold[col]).round(1).tolist(), "mape": round(float(ape(hold[col]).mean()), 2)}
                for col in ["model", "model_raw", "naive_prev", "naive_prev_1step", "naive_year"]}
R["holdout"]["fact"] = hold.fact.round(0).tolist(); R["holdout"]["months"] = list(hold.index)
R["trend_train"] = {"slope": round(float(slope), 1), "intercept": round(float(icpt), 1),
                    "slope_raw": round(float(slope_raw), 1), "intercept_raw": round(float(icpt_raw), 1)}
R["seasonal_train"] = {int(k): round(float(v), 3) for k, v in idx.items()}
# прогноз вперёд: индексы и тренд по всем 24 мес.
idx_all = season(n); IA = idx_all.reindex(month).values
sl2, ic2 = np.polyfit(t, s.values / IA, 1)
sl2_raw, _ = np.polyfit(t, s.values, 1)
fit_all = (ic2 + sl2 * t) * IA
ins_mape = float((np.abs(s.values - fit_all) / s.values * 100).mean())
fut_t = np.arange(n + 1, n + 4); fut_m = [12, 1, 2]
fut = (ic2 + sl2 * fut_t) * idx_all.reindex(fut_m).values
band = max(R["holdout"]["model"]["ape"]) / 100   # худшая ошибка модели на отложенных месяцах
R["seasonal_all"] = {int(k): round(float(v), 3) for k, v in idx_all.items()}
R["trend_all"] = {"slope": round(float(sl2), 1), "intercept": round(float(ic2), 1), "slope_raw": round(float(sl2_raw), 1)}
R["insample_mape"] = round(ins_mape, 1); R["band"] = round(band * 100, 1)
R["future"] = [{"month": mm, "point": round(float(v), 0), "lo": round(float(v * (1 - band)), 0), "hi": round(float(v * (1 + band)), 0)}
               for mm, v in zip(["2011-12", "2012-01", "2012-02"], fut)]
R["ma12"] = {k.strftime("%Y-%m"): round(float(v), 0) for k, v in ma.dropna().items()}
# частичный декабрь 2011 (1–9 дек.) против той же доли декабря 2010
dec11 = float(df[df.InvoiceDate >= "2011-12-01"].Revenue.sum())
d10 = df[(df.InvoiceDate >= "2010-12-01") & (df.InvoiceDate < "2011-01-01")]
share10 = float(d10[d10.InvoiceDate < "2010-12-10"].Revenue.sum() / d10.Revenue.sum())
R["dec_check"] = {"dec2011_1_9": round(dec11, 0), "dec2010_share_1_9": round(share10, 3), "dec2011_implied": round(dec11 / share10, 0)}

fig, ax = plt.subplots(figsize=(10, 4.4))
ax.plot(s.index, s.values / 1e3, "-o", ms=3, color=C1, label="Выручка, тыс. £")
ax.plot(ma.index, ma.values / 1e3, color=C2, lw=2.2, label="Скользящее среднее, 12 мес.")
ax.plot(s.index[:tr], trend[:tr] / 1e3, "--", color=C3, lw=1, label="Тренд (ряд без сезонности, 21 мес.)")
ax.plot(s.index[tr:], fc[tr:] / 1e3, "s", color="#c0392b", ms=6, label="Прогноз на отложенные 3 мес.")
fi = pd.date_range("2011-12-01", periods=3, freq="MS")
ax.plot(fi, fut / 1e3, "D", color="#8e44ad", ms=5, label="Прогноз вперёд (дек–фев), полоса ±%.0f%%" % (band * 100))
ax.fill_between(fi, fut * (1 - band) / 1e3, fut * (1 + band) / 1e3, color="#8e44ad", alpha=.15)
ax.axvspan(s.index[tr] - pd.Timedelta(days=15), s.index[-1] + pd.Timedelta(days=15), color="#c0392b", alpha=.06)
ax.set(ylabel="тыс. £", title="Online Retail II: помесячная выручка, тренд и прогноз")
ax.legend(fontsize=8, loc="upper left", frameon=False); fig.tight_layout()
fig.savefig(f"{out}/3_series.png", dpi=130); plt.close(fig)

# ---------------------------------------------------------------- Excel
wb = Workbook()
H1 = Font(bold=True, size=12); B = Font(bold=True)
FILL = PatternFill("solid", fgColor="DDE8F8"); NOTE = Font(italic=True, color="666666")

def header(ws, row, vals, col=1):
    for j, v in enumerate(vals):
        cell = ws.cell(row, col + j, v); cell.font = B; cell.fill = FILL
        cell.alignment = Alignment(wrap_text=True, vertical="top")

def widths(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[L(i)].width = x

# лист: о данных
ws = wb.active; ws.title = "О данных"
info = [
    ("Датасет", "Online Retail II (UCI): транзакции британского онлайн-магазина подарков, 01.12.2009–09.12.2011"),
    ("Очистка", "Убраны возвраты (счета на «C»), строки с количеством/ценой ≤ 0, служебные коды (почта, комиссии, ручные корректировки)"),
    ("Клиенты (части 1–2)", f"{len(c)} клиентов с ID, купивших хотя бы раз в окне 01.12.2009–30.11.2010. Признаки — по этому окну, отклик — выручка 01.12.2010–30.11.2011"),
    ("Ряд (части 3–4)", "Помесячная выручка 12.2009–11.2011, 24 мес. Декабрь 2011 исключён: в данных только 9 дней"),
    ("Как пересчитать", "Корреляция: Данные → Анализ данных → Корреляция, диапазон листа «Клиенты» B1:K… с подписями. Регрессия: Анализ данных → Регрессия, Y = K, X = B,D,E,H,F (поставить «Остатки» и «График остатков»). Лист «Ряд» считается формулами сам"),
]
for i, (k, v) in enumerate(info, 1):
    ws.cell(i, 1, k).font = B; ws.cell(i, 2, v).alignment = Alignment(wrap_text=True)
widths(ws, [22, 110])

# лист: клиенты
wsC = wb.create_sheet("Клиенты")
header(wsC, 1, ["ID клиента"] + [RU[v] for v in VARS])
for i, (cid, row) in enumerate(c[VARS].iterrows(), 2):
    wsC.cell(i, 1, cid)
    for j, v in enumerate(VARS, 2):
        wsC.cell(i, j, round(float(row[v]), 2))
widths(wsC, [11] + [14] * len(VARS)); wsC.freeze_panes = "B2"
last = len(c) + 1

# лист: корреляция (формулы CORREL по листу «Клиенты»)
wsK = wb.create_sheet("Корреляция")
wsK.cell(1, 1, "1.1. Корреляционная матрица (формулы КОРРЕЛ по листу «Клиенты»)").font = H1
header(wsK, 2, [""] + [RU[v] for v in VARS])
for i, x in enumerate(VARS):
    wsK.cell(3 + i, 1, RU[x]).font = B
    for j, y in enumerate(VARS):
        cx, cy = L(2 + i), L(2 + j)
        cell = wsK.cell(3 + i, 2 + j, f"=CORREL('Клиенты'!{cx}2:{cx}{last},'Клиенты'!{cy}2:{cy}{last})")
        cell.number_format = "0.00"
r0 = 3 + len(VARS) + 2
wsK.cell(r0, 1, "1.2. Пары с |r| > 0,3").font = H1
header(wsK, r0 + 1, ["Пара переменных", "r", "Механическая?", "Если да — почему / если нет — рабочая гипотеза"])
for k, p in enumerate(pairs):
    rr = r0 + 2 + k
    wsK.cell(rr, 1, f"{RU[p['x']]} — {RU[p['y']]}")
    wsK.cell(rr, 2, p["r"]).number_format = "0.00"
    wsK.cell(rr, 3, "да" if p["mech"] else "нет")
    wsK.cell(rr, 4, p["why"]).alignment = Alignment(wrap_text=True)
rr = r0 + 3 + len(pairs)
wsK.cell(rr, 1, "1.3. Выбросы: r до и после удаления 1% крупнейших значений").font = H1
header(wsK, rr + 1, ["Пара", "r (все)", "r (без 1%)", "Убрано клиентов", "r Спирмена (ранговый)"])
for k, x in enumerate(["revenue", "orders"]):
    o = R["outliers"][x]
    for j, v in enumerate([f"{RU[x]} — {RU['revenue_next']}", o["r_all"], o["r_trim"], o["removed"], R["spearman"][x]], 1):
        wsK.cell(rr + 2 + k, j, v)
img = XLImage(f"{out}/1_scatter_revenue.png"); img.width, img.height = 760, 304; wsK.add_image(img, f"A{rr + 6}")
img = XLImage(f"{out}/1_scatter_orders.png"); img.width, img.height = 760, 304; wsK.add_image(img, f"A{rr + 23}")
widths(wsK, [34] + [13] * len(VARS))
wsK.column_dimensions["D"].width = 13

# лист: регрессия
wsR = wb.create_sheet("Регрессия")
wsR.cell(1, 1, "2.1. Постановка: Y = выручка клиента за 12.2010–11.2011; факторы — поведение за 12.2009–11.2010").font = H1
header(wsR, 2, ["Фактор", "Входит в формулу Y?", "Ожидаемый знак", "Почему так ожидаем"])
WHY = {"orders": "частые покупатели продолжают покупать", "avg_check": "крупный чек = оптовик",
       "n_products": "широкая корзина = магазин-перепродавец", "recency_days": "давно не покупал — скорее ушёл",
       "avg_price": "дорогие единицы = розничный покупатель с редкими подарочными заказами"}
for k, f in enumerate(FACT):
    for j, v in enumerate([RU[f], "нет (другой период)", EXP[f], WHY[f]], 1):
        wsR.cell(3 + k, j, v)
wsR.cell(8, 1, "Не включены: выручка 2010 (= заказы × чек — дублирует два фактора), срок жизни/стаж/активные месяцы (механически связаны с заказами и давностью)").font = NOTE
wsR.cell(10, 1, "2.3. Результат (МНК, то же, что выдаёт «Пакет анализа» → Регрессия)").font = H1
header(wsR, 11, ["Фактор", "Коэффициент", "Ст. ошибка 95%: нижн.", "95%: верхн.", "p-значение", "Значим (p<0,05)?", "Знак совпал с ожиданием?"])
for k, f in enumerate(["const"] + FACT):
    co = R["reg"]["coef"][f]
    sign = "+" if co["b"] > 0 else "−"
    vals = ["Пересечение" if f == "const" else RU[f], co["b"], co["lo"], co["hi"], co["p"],
            "да" if co["p"] < .05 else "нет — связи не обнаружено",
            "—" if f == "const" else ("да" if sign == EXP[f] else f"нет ({sign})")]
    for j, v in enumerate(vals, 1):
        cell = wsR.cell(12 + k, j, v)
        if j in (2, 3, 4): cell.number_format = "0.00"
        if j == 5: cell.number_format = "0.0000"
wsR.cell(19, 1, "R²").font = B; wsR.cell(19, 2, R["reg"]["r2"])
wsR.cell(20, 1, "R² скорр.").font = B; wsR.cell(20, 2, R["reg"]["r2adj"])
wsR.cell(21, 1, "Наблюдений").font = B; wsR.cell(21, 2, R["reg"]["n"])
wsR.cell(22, 1, "Ст. ошибка регрессии, £").font = B; wsR.cell(22, 2, R["reg"]["se"])
img = XLImage(f"{out}/2_residuals.png"); img.width, img.height = 760, 304; wsR.add_image(img, "A25")
widths(wsR, [26, 20, 16, 16, 14, 26, 24])

# лист: ряд и прогноз (всё формулами)
wsS = wb.create_sheet("Ряд")
wsS.cell(1, 1, "3–4. Помесячная выручка, тренд, сезонность, прогноз и проверка. Обучение = строки с флагом 1 (12.2009–08.2011), отложено = 09–11.2011").font = H1
header(wsS, 2, ["Месяц", "t", "Выручка, £", "Обучение (1/0)", "Скольз. ср. 12 мес.", "№ месяца",
                "Сез. индекс (обуч.)", "Без сезонности = выручка / индекс", "Тренд", "Прогноз = тренд × индекс",
                "Ошибка, %", "Без сезонности (индексы 24 мес.)"])
F, Lr = 3, 2 + n
TB = "$O$11:$Q$22"  # таблица индексов
for i, (dt, v) in enumerate(s.items()):
    r = F + i
    wsS.cell(r, 1, dt.to_pydatetime()).number_format = "mmm yyyy"
    wsS.cell(r, 2, i + 1)
    wsS.cell(r, 3, round(float(v), 2)).number_format = "#,##0"
    wsS.cell(r, 4, 1 if i < tr else 0)
    if i >= 11:
        wsS.cell(r, 5, f"=AVERAGE(C{r-11}:C{r})").number_format = "#,##0"
    wsS.cell(r, 6, f"=MONTH(A{r})")
    wsS.cell(r, 7, f"=VLOOKUP(F{r},{TB},2,FALSE)").number_format = "0.000"
    wsS.cell(r, 8, f"=C{r}/G{r}").number_format = "#,##0"
    wsS.cell(r, 9, f"=$P$3+$P$2*B{r}").number_format = "#,##0"
    wsS.cell(r, 10, f"=I{r}*G{r}").number_format = "#,##0"
    if i >= tr:
        wsS.cell(r, 11, f"=ABS(C{r}-J{r})/C{r}*100").number_format = "0.0"
    wsS.cell(r, 12, f"=C{r}/VLOOKUP(F{r},{TB},3,FALSE)").number_format = "#,##0"
tf, tl = F, F + tr - 1
lab = [("Наклон тренда (НАКЛОН по ряду без сезонности)", f"=SLOPE(H{tf}:H{tl},B{tf}:B{tl})", "#,##0.0"),
       ("Пересечение (ОТРЕЗОК)", f"=INTERCEPT(H{tf}:H{tl},B{tf}:B{tl})", "#,##0"),
       ("Для сравнения: наклон по сырому ряду", f"=SLOPE(C{tf}:C{tl},B{tf}:B{tl})", "#,##0.0"),
       ("Для сравнения: пересечение по сырому ряду", f"=INTERCEPT(C{tf}:C{tl},B{tf}:B{tl})", "#,##0"),
       ("Средний уровень (обучение)", f"=AVERAGE(C{tf}:C{tl})", "#,##0"),
       ("Средний уровень (все 24 мес.)", f"=AVERAGE(C{F}:C{Lr})", "#,##0")]
for k, (t_, f_, nf) in enumerate(lab):
    wsS.cell(2 + k, 14, t_).font = B
    wsS.cell(2 + k, 16, f_).number_format = nf
wsS.cell(9, 14, "3.3. Сезонные индексы").font = H1
header(wsS, 10, ["№", "Индекс (обуч. 21 мес.)", "Индекс (все 24 мес.)", "Месяцев в обуч."], col=15)
for k in range(12):
    r = 11 + k
    wsS.cell(r, 15, k + 1)
    wsS.cell(r, 16, f"=AVERAGEIFS($C${F}:$C${Lr},$F${F}:$F${Lr},O{r},$D${F}:$D${Lr},1)/$P$6").number_format = "0.000"
    wsS.cell(r, 17, f"=AVERAGEIF($F${F}:$F${Lr},O{r},$C${F}:$C${Lr})/$P$7").number_format = "0.000"
    wsS.cell(r, 18, f"=COUNTIFS($F${F}:$F${Lr},O{r},$D${F}:$D${Lr},1)")
# 4.1–4.2
r = Lr + 2
wsS.cell(r, 1, "4.1–4.2. Отложенный период: модель против наивных прогнозов").font = H1
header(wsS, r + 1, ["Месяц", "Факт", "Модель", "Ошибка, %", "Модель с сырым трендом", "Ошибка, %",
                    "«Как в прошлом мес.» (авг.)", "Ошибка, %", "«Как в прошлом мес.» (на шаг)", "Ошибка, %",
                    "«Как год назад»", "Ошибка, %"])
for k in range(H):
    rr, sr = r + 2 + k, F + tr + k
    wsS.cell(rr, 1, f"=A{sr}").number_format = "mmm yyyy"
    wsS.cell(rr, 2, f"=C{sr}")
    wsS.cell(rr, 3, f"=J{sr}")
    wsS.cell(rr, 5, f"=($P$5+$P$4*B{sr})*G{sr}")
    wsS.cell(rr, 7, f"=$C${F + tr - 1}")
    wsS.cell(rr, 9, f"=C{sr - 1}")
    wsS.cell(rr, 11, f"=C{sr - 12}")
    for fcol in (3, 5, 7, 9, 11):
        wsS.cell(rr, fcol + 1, f"=ABS(B{rr}-{L(fcol)}{rr})/B{rr}*100").number_format = "0.0"
    for col in (2, 3, 5, 7, 9, 11):
        wsS.cell(rr, col).number_format = "#,##0"
mr = r + 2 + H
wsS.cell(mr, 1, "MAPE, %").font = B
for ecol in (4, 6, 8, 10, 12):
    wsS.cell(mr, ecol, f"=AVERAGE({L(ecol)}{r+2}:{L(ecol)}{r+1+H})").number_format = "0.00"
wsS.cell(mr + 1, 1, "«На шаг» использует факт сентября и октября, которого на дату прогноза (конец августа) ещё нет; честное сравнение — столбец «авг.»").font = NOTE
# прогноз вперёд
fr = mr + 3
wsS.cell(fr, 1, "3.4. Прогноз вперёд: индексы и тренд пересчитаны по всем 24 мес.").font = H1
wsS.cell(fr + 1, 1, "Наклон (24 мес., без сезонности)").font = B; wsS.cell(fr + 1, 5, f"=SLOPE(L{F}:L{Lr},B{F}:B{Lr})").number_format = "#,##0.0"
wsS.cell(fr + 2, 1, "Пересечение (24 мес.)").font = B; wsS.cell(fr + 2, 5, f"=INTERCEPT(L{F}:L{Lr},B{F}:B{Lr})").number_format = "#,##0"
wsS.cell(fr + 3, 1, "Ширина полосы, ±%").font = B; wsS.cell(fr + 3, 5, f"=MAX(D{r+2}:D{r+1+H})").number_format = "0.0"
wsS.cell(fr + 3, 6, "худшая ошибка модели на отложенных месяцах — грубая эмпирическая полоса, а не доверительный интервал").font = NOTE
header(wsS, fr + 5, ["Месяц", "t", "№ мес.", "Индекс (24 мес.)", "Тренд", "Прогноз", "Нижняя граница", "Верхняя граница"])
for k, (mm, tt, mo) in enumerate(zip(["дек 2011", "янв 2012", "фев 2012"], fut_t, fut_m)):
    rr = fr + 6 + k
    wsS.cell(rr, 1, mm); wsS.cell(rr, 2, int(tt)); wsS.cell(rr, 3, mo)
    wsS.cell(rr, 4, f"=VLOOKUP(C{rr},{TB},3,FALSE)").number_format = "0.000"
    wsS.cell(rr, 5, f"=$E${fr+2}+$E${fr+1}*B{rr}").number_format = "#,##0"
    wsS.cell(rr, 6, f"=E{rr}*D{rr}").number_format = "#,##0"
    wsS.cell(rr, 7, f"=F{rr}*(1-$E${fr+3}/100)").number_format = "#,##0"
    wsS.cell(rr, 8, f"=F{rr}*(1+$E${fr+3}/100)").number_format = "#,##0"
img = XLImage(f"{out}/3_series.png"); img.width, img.height = 800, 352; wsS.add_image(img, f"A{fr + 11}")
widths(wsS, [12, 6, 13, 10, 13, 8, 11, 14, 12, 14, 9, 14, 3, 40, 8, 13, 13, 10])

wb.save(f"{out}/Seminar_OnlineRetailII.xlsx")
json.dump(R, open(f"{out}/results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: R[k] for k in ["n_customers", "pairs", "outliers", "spearman", "reg", "reg_log", "reg_trim", "zero_next_share",
                                    "holdout", "trend_train", "trend_all", "seasonal_train", "seasonal_all", "insample_mape", "band", "future", "dec_check"]},
                 ensure_ascii=False, indent=0, default=str))
