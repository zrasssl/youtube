"""Части 1–2 семинара на Bank Marketing (файл студента).
Запуск: python3 build.py <файл студента.xlsx> <out_dir>
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
from openpyxl.worksheet.formula import ArrayFormula
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
raw, d = load(src)
N = len(d); R = {"n": N}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3 = "#2a6fdb", "#e07a1f", "#7a7a7a"

# порядок важен: факторы регрессии идут подряд сразу после y (для ЛИНЕЙН)
FACT = ["age", "balance", "housing", "campaign", "prev_success"]
VARS = ["y"] + FACT + ["loan", "duration", "pdays", "previous", "contacted_before", "day"]
RU = {"y": "Открыл вклад (1/0)", "age": "Возраст", "balance": "Баланс, €", "housing": "Жилищный кредит (1/0)",
      "campaign": "Звонков в этой кампании", "prev_success": "Успех прошлой кампании (1/0)", "loan": "Потреб. кредит (1/0)",
      "duration": "Длительность звонка, сек", "pdays": "Дней с прошлого контакта", "previous": "Контактов до кампании",
      "contacted_before": "Был контакт раньше (1/0)", "day": "День месяца"}
FORMULA = {"y": 'IF(Q{r}="yes",1,0)', "age": "A{r}", "balance": "F{r}", "housing": 'IF(G{r}="yes",1,0)',
           "campaign": "M{r}", "prev_success": 'IF(P{r}="success",1,0)', "loan": 'IF(H{r}="yes",1,0)',
           "duration": "L{r}", "pdays": "N{r}", "previous": "O{r}", "contacted_before": "IF(N{r}<>-1,1,0)", "day": "J{r}"}
corr = d[VARS].corr()
R["corr"] = corr.round(3).to_dict()

MECH = {
    ("y", "duration"): "Через время: длительность известна только после звонка, а успешный звонок длиннее, потому что в нём оформляют вклад. Это следствие результата, а не причина",
    ("pdays", "previous"): "Через кодирование: pdays = −1 ровно тогда, когда previous = 0",
    ("pdays", "contacted_before"): "По определению: «был контакт» = (pdays ≠ −1)",
    ("previous", "contacted_before"): "По определению: «был контакт» = (previous > 0)",
    ("contacted_before", "prev_success"): "Через время: успех прошлой кампании возможен только у тех, с кем был контакт",
}
HYP = {("y", "prev_success"): "Согласившиеся в прошлый раз соглашаются снова: у них есть сбережения и доверие к банку"}
pairs = []
for i, x in enumerate(VARS):
    for y in VARS[i + 1:]:
        r = corr.loc[x, y]
        if abs(r) > 0.3:
            key = (x, y) if (x, y) in MECH or (x, y) in HYP else (y, x)
            pairs.append({"x": x, "y": y, "r": round(float(r), 3), "mech": key in MECH, "why": MECH.get(key) or HYP.get(key)})
pairs.sort(key=lambda p: -abs(p["r"]))
R["pairs"] = pairs

# 1.3 диаграммы рассеяния (для 0/1 — с разбросом точек и долей по группам)
rng = np.random.default_rng(1)
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
s = d.sample(8000, random_state=1)
ax[0].scatter(s.duration, s.y + rng.uniform(-.15, .15, len(s)), s=4, alpha=.25, color=C1)
bins = pd.qcut(d.duration, 20)
g = d.groupby(bins, observed=True).agg(x=("duration", "mean"), y=("y", "mean"))
ax[0].plot(g.x, g.y, "-o", color=C2, ms=4, label="Доля открывших по 20 группам")
ax[0].set(xlim=(0, 1500), xlabel=RU["duration"], ylabel="Открыл вклад (точки с разбросом)", title=f"Длительность → вклад, r = {corr.loc['duration','y']:.2f}")
ax[0].legend(frameon=False, fontsize=8)
sh = d.groupby("prev_success").y.mean()
ax[1].scatter(d.prev_success + rng.uniform(-.2, .2, N), d.y + rng.uniform(-.2, .2, N), s=2, alpha=.08, color=C1)
ax[1].plot([0, 1], sh.values, "-o", color=C2, ms=7, label="Доля открывших")
for k_, v in sh.items():
    ax[1].annotate(f"{v:.0%}", (k_, v), textcoords="offset points", xytext=(10, -14), color=C2, fontsize=10)
ax[1].set(xticks=[0, 1], xticklabels=["нет", "да"], xlabel="Успех прошлой кампании", ylabel="Открыл вклад (точки с разбросом)",
          title=f"Прошлый успех → вклад, r = {corr.loc['prev_success','y']:.2f}")
ax[1].legend(frameon=False, fontsize=8, loc="center")
fig.tight_layout(); fig.savefig(f"{out}/1_scatter.png", dpi=130); plt.close(fig)
R["share_by_prev_success"] = {int(k_): round(float(v), 3) for k_, v in sh.items()}
R["n_prev_success"] = int(d.prev_success.sum())
R["duration_bins"] = {"lo": round(float(g.y.iloc[0]), 3), "hi": round(float(g.y.iloc[-1]), 3)}

# выбросы: убираем 1% крупнейших значений непрерывной переменной
R["outliers"] = {}
for x in ["duration", "balance", "campaign"]:
    q = d[x].quantile(.99); t = d[d[x] <= q]
    R["outliers"][x] = {"r_all": round(float(d[x].corr(d.y)), 3), "r_trim": round(float(t[x].corr(t.y)), 3), "removed": int(N - len(t)), "cut": float(q)}
# механизм для prev_success: кто вообще попадает в группу «был контакт»
cb = d[d.contacted_before == 1]
R["selection"] = {"share_contacted": round(float(d.contacted_before.mean()), 3),
                  "y_contacted": round(float(cb.y.mean()), 3), "y_not": round(float(d[d.contacted_before == 0].y.mean()), 3),
                  "r_within_contacted": round(float(cb.prev_success.corr(cb.y)), 3),
                  "balance_succ": round(float(d[d.prev_success == 1].balance.median()), 0), "balance_other": round(float(d[d.prev_success == 0].balance.median()), 0),
                  "age_succ": round(float(d[d.prev_success == 1].age.mean()), 1), "age_other": round(float(d[d.prev_success == 0].age.mean()), 1),
                  "housing_succ": round(float(d[d.prev_success == 1].housing.mean()), 3), "housing_other": round(float(d[d.prev_success == 0].housing.mean()), 3)}

# ---------------------------------------------------------------- регрессия
EXP = {"age": "+", "balance": "+", "housing": "−", "campaign": "−", "prev_success": "+"}
WHY = {"age": "у старших больше сбережений", "balance": "есть свободные деньги — есть что положить",
       "housing": "деньги уходят на ипотеку", "campaign": "кого приходится уговаривать много раз, тот скорее откажет",
       "prev_success": "уже был клиентом вклада и остался доволен"}
m = sm.OLS(d.y, sm.add_constant(d[FACT])).fit()
ci = m.conf_int()
R["reg"] = {"r2": round(m.rsquared, 4), "r2adj": round(m.rsquared_adj, 4), "n": int(m.nobs), "se": round(float(np.sqrt(m.mse_resid)), 4),
            "coef": {k_: {"b": float(m.params[k_]), "se": float(m.bse[k_]), "p": float(m.pvalues[k_]), "lo": float(ci.loc[k_, 0]), "hi": float(ci.loc[k_, 1])} for k_ in m.params.index}}
pred = m.fittedvalues
R["pred_range"] = [round(float(pred.min()), 3), round(float(pred.max()), 3)]
R["pred_neg"] = int((pred < 0).sum())
# проверка формы: логистическая регрессия и возраст как U-образный
lg = sm.Logit(d.y, sm.add_constant(d[FACT])).fit(disp=0)
R["logit"] = {k_: {"b": float(lg.params[k_]), "p": float(lg.pvalues[k_]), "or": float(np.exp(lg.params[k_]))} for k_ in lg.params.index}
R["logit_pseudo_r2"] = round(float(lg.prsquared), 3)
ag = d.groupby(pd.cut(d.age, [17, 25, 30, 40, 50, 60, 100])).y.mean()
R["y_by_age"] = {str(k_): round(float(v), 3) for k_, v in ag.items()}
# с длительностью — чтобы показать, что R² «взлетает» от механической переменной
m2 = sm.OLS(d.y, sm.add_constant(d[FACT + ["duration"]])).fit()
R["r2_with_duration"] = round(m2.rsquared, 3)

fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].scatter(pred, m.resid, s=2, alpha=.15, color=C1); ax[0].axhline(0, color=C3, lw=1)
ax[0].set(xlabel="Предсказанная вероятность", ylabel="Остаток", title="Остатки: две полосы (Y = 0 или 1)")
ab = pd.cut(d.age, [17, 22, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 100])
gb = pd.DataFrame({"a": d.age, "r": m.resid}).groupby(ab, observed=True).mean()
ax[1].plot(gb.a, gb.r, "-o", color=C2, ms=5); ax[1].axhline(0, color=C3, lw=1)
ax[1].set(xlabel="Возраст (средний в группе)", ylabel="Средний остаток в группе", title="Средний остаток по возрасту: изгиб (U)")
fig.tight_layout(); fig.savefig(f"{out}/2_residuals.png", dpi=130); plt.close(fig)
R["resid_by_age"] = [[round(float(a), 1), round(float(b), 3)] for a, b in zip(gb.a, gb.r)]

# ---------------------------------------------------------------- Excel
wb = Workbook()
H1 = Font(bold=True, size=12); B = Font(bold=True); NOTE = Font(italic=True, color="666666")
FILL = PatternFill("solid", fgColor="DDE8F8")

def header(ws, row, vals, col=1):
    for j, v in enumerate(vals):
        c = ws.cell(row, col + j, v); c.font = B; c.fill = FILL; c.alignment = Alignment(wrap_text=True, vertical="top")

def widths(ws, w):
    for i, x in enumerate(w, 1): ws.column_dimensions[L(i)].width = x

wsD = wb.active; wsD.title = "Данные"
cols = list(raw.columns)
header(wsD, 1, cols + [RU[v] for v in VARS] + ["Прогноз модели", "Остаток", "№ месяца", "Год (по порядку строк)"])
V0 = len(cols) + 1                      # первая колонка числового блока (R)
VC = {v: L(V0 + i) for i, v in enumerate(VARS)}
PC, RC = L(V0 + len(VARS)), L(V0 + len(VARS) + 1)
last = N + 1
vals = raw.values
for i in range(N):
    r = i + 2
    for j, v in enumerate(vals[i], 1):
        wsD.cell(r, j, v.item() if hasattr(v, "item") else v)
    for k_, v in enumerate(VARS):
        wsD.cell(r, V0 + k_, "=" + FORMULA[v].format(r=r))
    wsD.cell(r, V0 + len(VARS), f"=Регрессия!$B$22+" + "+".join(f"Регрессия!$B${23+k_}*{VC[f_]}{r}" for k_, f_ in enumerate(FACT)))
    wsD.cell(r, V0 + len(VARS) + 1, f"={VC['y']}{r}-{PC}{r}")
    wsD.cell(r, V0 + len(VARS) + 2, f'=MATCH(K{r},{{"jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"}},0)')
    wsD.cell(r, V0 + len(VARS) + 3, 2008 if r == 2 else f"={L(V0+len(VARS)+3)}{r-1}+IF({L(V0+len(VARS)+2)}{r}<{L(V0+len(VARS)+2)}{r-1},1,0)")
wsD.freeze_panes = "A2"
wsD.cell(1, 13).value = "campaign"   # в исходнике заголовок был пустым

# связи
wsK = wb.create_sheet("Связи")
wsK.cell(1, 1, "1.1. Корреляционная матрица: 12 количественных переменных (формулы КОРРЕЛ по листу «Данные»)").font = H1
header(wsK, 2, [""] + [RU[v] for v in VARS])
for i, x in enumerate(VARS):
    wsK.cell(3 + i, 1, RU[x]).font = B
    for j, y in enumerate(VARS):
        c = wsK.cell(3 + i, 2 + j, f"=CORREL('Данные'!{VC[x]}2:{VC[x]}{last},'Данные'!{VC[y]}2:{VC[y]}{last})"); c.number_format = "0.00"
r0 = 3 + len(VARS) + 2
wsK.cell(r0, 1, "1.2. Все пары с |r| > 0,3").font = H1
header(wsK, r0 + 1, ["Пара переменных", "r", "Механическая?", "Если да — почему / если нет — рабочая гипотеза"])
for k_, p in enumerate(pairs):
    rr = r0 + 2 + k_
    wsK.cell(rr, 1, f"{RU[p['x']]} — {RU[p['y']]}"); wsK.cell(rr, 2, p["r"]).number_format = "0.00"
    wsK.cell(rr, 3, "да" if p["mech"] else "нет"); wsK.cell(rr, 4, p["why"]).alignment = Alignment(wrap_text=True)
rr = r0 + 3 + len(pairs)
wsK.cell(rr, 1, "1.3. Выбросы: r с «Открыл вклад» до и после удаления 1% крупнейших значений").font = H1
header(wsK, rr + 1, ["Переменная", "r (все)", "r (без 1%)", "Порог 99%", "Убрано строк"])
for k_, x in enumerate(["duration", "balance", "campaign"]):
    o = R["outliers"][x]
    for j, v in enumerate([RU[x], o["r_all"], o["r_trim"], o["cut"], o["removed"]], 1): wsK.cell(rr + 2 + k_, j, v)

widths(wsK, [34] + [12] * len(VARS)); wsK.column_dimensions["D"].width = 14

# регрессия
wsR = wb.create_sheet("Регрессия")
wsR.cell(1, 1, "2.1. Постановка. Y = открыл вклад (1/0), линейная модель вероятности").font = H1
header(wsR, 2, ["Фактор", "Входит в формулу Y?", "Ожидаемый знак", "Почему"])
for k_, f_ in enumerate(FACT):
    for j, v in enumerate([RU[f_], "нет", EXP[f_], WHY[f_]], 1): wsR.cell(3 + k_, j, v)
wsR.cell(8, 1, "Не включены: длительность звонка (известна только после результата — механическая связь через время); "
                "дней с прошлого контакта, контактов до кампании, «был контакт» (механически связаны с успехом прошлой кампании)").font = NOTE
wsR.cell(10, 1, "2.2. ЛИНЕЙН с полной статистикой (массив, порядок у Excel обратный: последний фактор слева)").font = H1
lin_ref = f"I12:{L(9 + len(FACT))}16"
header(wsR, 11, [RU[f_] for f_ in reversed(FACT)] + ["Пересечение"], col=9)
wsR[f"I12"] = ArrayFormula(lin_ref, f"=LINEST('Данные'!{VC['y']}2:{VC['y']}{last},'Данные'!{VC[FACT[0]]}2:{VC[FACT[-1]]}{last},1,1)")
for k_, lab in enumerate(["коэфф.", "ст. ошибка", "R² | ст. ош. Y", "F | df", "SS регр. | SS ост."]):
    wsR.cell(12 + k_, 8, lab).font = NOTE
# отдельная аккуратная таблица 2.3 ниже — чтобы не путаться с массивом
T0 = 20; nf = len(FACT)
wsR.cell(T0, 1, "2.3. Значимость (числа берутся из массива ЛИНЕЙН выше)").font = H1
header(wsR, T0 + 1, ["Фактор", "Коэффициент", "Ст. ошибка", "t", "p-значение", "Значим?", "Знак совпал с ожиданием?", "Интерпретация"])
for k_, f_ in enumerate(["const"] + FACT):
    r = T0 + 2 + k_
    col = L(9 + nf) if f_ == "const" else L(9 + nf - 1 - FACT.index(f_))
    co = R["reg"]["coef"][f_]
    wsR.cell(r, 1, "Пересечение" if f_ == "const" else RU[f_])
    wsR.cell(r, 2, f"={col}12").number_format = "0.000000"
    wsR.cell(r, 3, f"={col}13").number_format = "0.000000"
    wsR.cell(r, 4, f"=B{r}/C{r}").number_format = "0.00"
    wsR.cell(r, 5, f"=TDIST(ABS(D{r}),$J$15,2)").number_format = "0.0000"
    wsR.cell(r, 6, f'=IF(E{r}<0.05,"да","нет — связи не обнаружено")')
    if f_ != "const":
        sign = "+" if co["b"] > 0 else "−"
        wsR.cell(r, 7, "да" if sign == EXP[f_] else f"нет ({sign})")
INTERP = {
    "age": "При увеличении возраста на 1 год вероятность открыть вклад в среднем меняется на {b} п.п., если остальные учтённые факторы не меняются",
    "balance": "При увеличении баланса на 1 000 € вероятность открыть вклад в среднем растёт на {b1000} п.п., если остальные учтённые факторы не меняются",
    "housing": "Наличие жилищного кредита (0 → 1) в среднем снижает вероятность открыть вклад на {babs} п.п., если остальные учтённые факторы не меняются",
    "campaign": "Каждый дополнительный звонок в этой кампании в среднем связан с изменением вероятности на {b} п.п., если остальные учтённые факторы не меняются",
    "prev_success": "Успех прошлой кампании (0 → 1) в среднем связан с ростом вероятности открыть вклад на {b} п.п., если остальные учтённые факторы не меняются",
}
def pp(x): return f"{x*100:.2f}".replace(".", ",")
for k_, f_ in enumerate(FACT):
    b = R["reg"]["coef"][f_]["b"]
    txt = INTERP[f_].format(b=pp(b), b1000=pp(b * 1000), babs=pp(abs(b)))
    if R["reg"]["coef"][f_]["p"] >= .05: txt = "Связи не обнаружено"
    wsR.cell(T0 + 3 + k_, 8, txt).alignment = Alignment(wrap_text=True)
wsR.cell(T0 + 9, 1, "R²").font = B; wsR.cell(T0 + 9, 2, "=I14").number_format = "0.0000"
wsR.cell(T0 + 10, 1, "Наблюдений").font = B; wsR.cell(T0 + 10, 2, N)
wsR.cell(T0 + 11, 1, "Для сравнения: R² с длительностью звонка").font = B; wsR.cell(T0 + 11, 2, R["r2_with_duration"])
wsR.cell(T0 + 11, 3, "— рост R² даёт механическая переменная, поэтому она исключена").font = NOTE
widths(wsR, [30, 14, 14, 9, 12, 26, 14, 70, 13, 13, 13, 13, 13, 13])

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_extra.py"), encoding="utf-8").read())

wb.save(f"{out}/Seminar_BankMarketing.xlsx")
json.dump(R, open(f"{out}/results.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k_: R[k_] for k_ in ["pairs", "outliers", "selection", "share_by_prev_success", "n_prev_success", "duration_bins", "reg", "pred_range", "pred_neg",
                                       "logit", "logit_pseudo_r2", "y_by_age", "r2_with_duration", "resid_by_age"]}, ensure_ascii=False, default=str))
