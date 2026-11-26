# Выполняется внутри build.py (exec): дописывает в книгу пункты 1.3, 2.3–2.4 и части 3–4.
# Использует переменные build.py: wb, wsK, wsR, d, raw, R, N, last, VC, PC, RC, header, widths, H1, B, NOTE, rr, out.
from openpyxl.chart import ScatterChart, LineChart, Reference, Series
from series import monthly, forecast, year_month

YC, MC = L(V0 + len(VARS) + 3), L(V0 + len(VARS) + 2)   # колонки «Год» и «№ месяца» на листе «Данные»


def fn(x, nd=0):
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


def text(ws, row, lines, col=1):
    """Абзацы по одному в строке, без переноса (текст растекается вправо по пустым ячейкам)."""
    for i, ln in enumerate(lines):
        c = ws.cell(row + i, col, ln)
        if ln.endswith(":") or ln[:4].strip().replace(".", "").isdigit():
            c.font = B
    return row + len(lines)


def scatter(title, xt, yt, xref, yref, w=16, h=8.5, ymin=None, ymax=None, xmax=None):
    ch = ScatterChart(); ch.title = title; ch.style = 13; ch.legend = None
    ch.x_axis.title, ch.y_axis.title = xt, yt; ch.width, ch.height = w, h
    se = Series(yref, xref, title=title); se.marker.symbol = "circle"; se.marker.size = 3
    se.graphicalProperties.line.noFill = True
    ch.series.append(se)
    if ymin is not None: ch.y_axis.scaling.min = ymin
    if ymax is not None: ch.y_axis.scaling.max = ymax
    if xmax is not None: ch.x_axis.scaling.max = xmax
    ch.x_axis.delete = False; ch.y_axis.delete = False
    return ch


sh = {str(k): v for k, v in R["share_by_prev_success"].items()}; S, O = R["selection"], R["outliers"]

# ======================================================= 1.3 на листе «Связи»
r = rr + 6
r = text(wsK, r, [
    "1.3. Три проверки:",
    f"Проверка 1 — диаграммы рассеяния (ниже, построены прямо по листу «Данные»; рисунок с разнесёнными точками — ещё ниже).",
    f"   Длительность → вклад: связь НЕ линейная. Доля открывших почти 0 у коротких звонков и растёт до {R['duration_bins']['hi']*100:.0f}% у самых длинных — кривая выпуклая.",
    f"   Прошлый успех → вклад: обе переменные 0/1, точек всего четыре, вопрос о линейности не стоит. Вклад открыли {sh['1']*100:.0f}% с прошлым успехом против {sh['0']*100:.0f}% остальных.",
    f"Проверка 2 — выбросы: без 1% самых длинных звонков (> {fn(O['duration']['cut'])} сек., {O['duration']['removed']} строк) r почти не изменился: {fn(O['duration']['r_all'],3)} → {fn(O['duration']['r_trim'],3)}.",
    f"   Значит, связь держится на всей массе клиентов, а не на нескольких рекордных звонках. Для баланса r без 1% крупнейших даже вырос: {fn(O['balance']['r_all'],3)} → {fn(O['balance']['r_trim'],3)}.",
    "Проверка 3 — механизм главной связи «успех прошлой кампании → открыл вклад» (r = 0,31):",
    f"   Общая причина — ДА, вероятна: склонность к сбережениям и свободные деньги. У клиентов с прошлым успехом медианный баланс {fn(S['balance_succ'])} € против {fn(S['balance_other'])} €,",
    f"      жилищный кредит у {S['housing_succ']*100:.0f}% против {S['housing_other']*100:.0f}%. Кто сберегает, соглашается и тогда, и сейчас — само прошлое согласие может ничего не вызывать.",
    f"   Отбор — ДА, действует: «прошлый успех» есть только у тех {S['share_contacted']*100:.0f}% клиентов, кому банк звонил раньше, а кому звонить повторно, банк решал сам (вероятно, перспективным).",
    f"      Внутри этой группы связь даже сильнее (r = {fn(S['r_within_contacted'],2)}), то есть отбор связь не создаёт, но ограничивает, к кому вывод применим.",
    "   Обратная причинность — НЕТ: прошлая кампания была раньше нынешнего решения, будущее не влияет на прошлое.",
    "   Вывод: связь годится, чтобы выбирать, кому звонить, но не доказывает, что «прошлый успех» сам повышает шанс.",
])
dur = Reference(wsD, min_col=wsD[f"{VC['duration']}1"].column, min_row=2, max_row=last)
yv = Reference(wsD, min_col=wsD[f"{VC['y']}1"].column, min_row=2, max_row=last)
ps = Reference(wsD, min_col=wsD[f"{VC['prev_success']}1"].column, min_row=2, max_row=last)
wsK.add_chart(scatter("Длительность звонка → открыл вклад", "Длительность, сек", "Открыл вклад (0/1)", dur, yv, ymin=-0.1, ymax=1.1, xmax=3000), f"A{r + 1}")
wsK.add_chart(scatter("Успех прошлой кампании → открыл вклад", "Успех прошлой кампании (0/1)", "Открыл вклад (0/1)", ps, yv, ymin=-0.1, ymax=1.1), f"E{r + 1}")
# доли по группам (то, что не видно на точках 0/1)
header(wsK, r + 1, ["Успех прошлой кампании", "Клиентов", "Доля открывших"], col=11)
for k_, v in enumerate([0, 1]):
    rr2 = r + 2 + k_
    wsK.cell(rr2, 11, "да" if v else "нет")
    wsK.cell(rr2, 12, f"=COUNTIF('Данные'!{VC['prev_success']}2:{VC['prev_success']}{last},{v})")
    wsK.cell(rr2, 13, f"=AVERAGEIF('Данные'!{VC['prev_success']}2:{VC['prev_success']}{last},{v},'Данные'!{VC['y']}2:{VC['y']}{last})").number_format = "0.0%"
img = XLImage(f"{out}/1_scatter.png"); img.width, img.height = 760, 304; wsK.add_image(img, f"A{r + 20}")

# ======================================================= 2.3–2.4 на листе «Регрессия»
ra = R["resid_by_age"]; rg = R["reg"]["coef"]
r = 33
r = text(wsR, r, [
    "2.3. Остатки (графики ниже: остаток против прогноза и средний остаток по возрасту):",
    "   Структура ЕСТЬ, форма модели неверна:",
    "   • две параллельные полосы — неизбежно при отклике 0/1 (остаток либо 1 − прогноз, либо −прогноз);",
    f"   • {R['pred_neg']} прогнозов «вероятности» отрицательные (минимум {fn(R['pred_range'][0],2)}) — так быть не может;",
    f"   • ИЗГИБ по возрасту (U-форма): средний остаток +{fn(ra[0][1],2)} у самых молодых, около −0,02 в 35–60 лет и снова +{fn(ra[-1][1],2)} у 60+.",
    "     Студенты и пенсионеры открывают вклады чаще всех, а прямая по возрасту этого не ловит — поэтому знак возраста вышел «не тот».",
    "   Правильнее: логистическая регрессия и возраст группами.",
    "2.4. Честный вывод:",
    f"   Модель объясняет около {R['reg']['r2']*100:.0f}% различий между клиентами (R² = {fn(R['reg']['r2'],3)}). Почти всё объяснение — история отношений с банком",
    f"   (успех прошлой кампании: +{rg['prev_success']['b']*100:.0f} п.п.) и свободные деньги (нет ипотеки: +{-rg['housing']['b']*100:.1f} п.п., баланс).",
    f"   Необъяснёнными остаются {100-R['reg']['r2']*100:.0f}%: доход и сбережения вне банка, ставки конкурентов в момент звонка, время и качество звонка,",
    "   жизненные события (продажа квартиры, наследство, выход на пенсию) — ничего этого в данных нет.",
    f"   Проверка на круговую зависимость: с длительностью звонка R² вырос бы до {fn(R['r2_with_duration'],3)} — рост дала бы механическая переменная, поэтому её в модели нет.",
])
pr = Reference(wsD, min_col=wsD[f"{PC}1"].column, min_row=2, max_row=last)
rs = Reference(wsD, min_col=wsD[f"{RC}1"].column, min_row=2, max_row=last)
wsR.add_chart(scatter("Остатки против прогноза", "Прогноз модели (вероятность)", "Остаток", pr, rs), f"A{r + 1}")
# средний остаток по возрастным группам — формулы
AG = [(17, 23), (23, 26), (26, 31), (31, 36), (36, 41), (41, 46), (46, 51), (51, 56), (56, 61), (61, 66), (66, 71), (71, 100)]
header(wsR, r + 1, ["Возраст от", "до (не вкл.)", "Средний остаток"], col=10)
for k_, (lo, hi) in enumerate(AG):
    rr2 = r + 2 + k_
    wsR.cell(rr2, 10, lo); wsR.cell(rr2, 11, hi)
    rng_a = f"'Данные'!{VC['age']}2:{VC['age']}{last}"
    wsR.cell(rr2, 12, f"=AVERAGEIFS('Данные'!{RC}2:{RC}{last},{rng_a},\">=\"&J{rr2},{rng_a},\"<\"&K{rr2})").number_format = "0.000"
lc = LineChart(); lc.title = "Средний остаток по возрасту: изгиб"; lc.style = 12; lc.legend = None
lc.add_data(Reference(wsR, min_col=12, min_row=r + 1, max_row=r + 1 + len(AG)), titles_from_data=True)
lc.set_categories(Reference(wsR, min_col=10, min_row=r + 2, max_row=r + 1 + len(AG)))
lc.x_axis.title, lc.y_axis.title = "Возраст (начало группы)", "Средний остаток"; lc.width, lc.height = 14, 8.5
lc.x_axis.delete = False; lc.y_axis.delete = False
wsR.add_chart(lc, f"N{r + 1}")
img = XLImage(f"{out}/2_residuals.png"); img.width, img.height = 760, 304; wsR.add_image(img, f"A{r + 20}")

# ======================================================= части 3–4: лист «Прогноз»
dep, calls = monthly(raw, d)
FC = forecast(dep)
n = len(dep); H = 3; tr = FC["tr"]; t = np.arange(1, n + 1); mo = dep.index.month
ia = dep.groupby(mo).mean() / dep.mean()
b2, a2 = np.polyfit(t, dep.values, 1)
fut_t, fut_m = [n + 1, n + 2, n + 3], [11, 12, 1]
fut = [(a2 + b2 * tt) * ia[mm] for tt, mm in zip(fut_t, fut_m)]
ape_m = np.abs(FC["res"]["fact"] - FC["res"]["model"]) / FC["res"]["fact"] * 100
band = float(ape_m.max())
ma = dep.rolling(12).mean()
yr_, mn_ = year_month(raw)
nov10 = int(d.y[(yr_ == 2010) & (mn_ == 11)].sum())
R["series"] = {"months": [str(p) for p in dep.index], "dep": dep.tolist(), "calls": calls.tolist(),
               "ma12": {str(k): round(float(v), 1) for k, v in ma.dropna().items()},
               "idx_train": {int(k): round(float(v), 3) for k, v in FC["idx"].items()},
               "idx_all": {int(k): round(float(v), 3) for k, v in ia.items()},
               "slope": FC["slope"], "icpt": FC["icpt"], "slope_all": b2, "icpt_all": a2,
               "holdout": {k: [float(x) for x in v] for k, v in FC["res"].items()}, "ape_model": ape_m.round(1).tolist(),
               "mape": FC["mape"], "band": band, "nov2010_partial": nov10,
               "future": [{"m": m_, "point": float(v), "lo": float(max(v * (1 - band / 100), 0)), "hi": float(v * (1 + band / 100))}
                          for m_, v in zip(["ноя 2010", "дек 2010", "янв 2011"], fut)]}

wsP = wb.create_sheet("Прогноз")
wsP.cell(1, 1, "Части 3–4. Помесячный ряд: число открытых вкладов").font = H1
wsP.cell(2, 1, "Год восстановлен по порядку строк (данные идут хронологически 05.2008–11.2010; колонки «№ месяца» и «Год» на листе «Данные»). "
               "Ноябрь 2010 неполный (до 17-го) — исключён. Если преподаватель требует файл Nedelya-13, этот лист нужно пересчитать на нём.").font = NOTE
header(wsP, 4, ["Месяц", "t", "Открыто вкладов", "Звонков", "Обучение (1/0)", "Скольз. ср. 12 мес.", "№ месяца",
                "Сез. индекс (обуч.)", "Тренд", "Прогноз = тренд × индекс", "Ошибка, %"])
F0 = 5; Lr = F0 + n - 1
DY = f"'Данные'!${YC}$2:${YC}${last}"; DM = f"'Данные'!${MC}$2:${MC}${last}"; DYV = f"'Данные'!${VC['y']}$2:${VC['y']}${last}"
for i, per in enumerate(dep.index):
    r = F0 + i
    wsP.cell(r, 1, per.to_timestamp().to_pydatetime()).number_format = "mmm yyyy"
    wsP.cell(r, 2, i + 1)
    wsP.cell(r, 3, f"=COUNTIFS({DY},YEAR(A{r}),{DM},MONTH(A{r}),{DYV},1)")
    wsP.cell(r, 4, f"=COUNTIFS({DY},YEAR(A{r}),{DM},MONTH(A{r}))")
    wsP.cell(r, 5, 1 if i < tr else 0)
    if i >= 11: wsP.cell(r, 6, f"=AVERAGE(C{r-11}:C{r})").number_format = "0.0"
    wsP.cell(r, 7, f"=MONTH(A{r})")
    wsP.cell(r, 8, f"=VLOOKUP(G{r},$M$13:$O$24,2,FALSE)").number_format = "0.00"
    wsP.cell(r, 9, f"=$O$6+$O$5*B{r}").number_format = "0.0"
    wsP.cell(r, 10, f"=I{r}*H{r}").number_format = "0.0"
    if i >= tr: wsP.cell(r, 11, f"=ABS(C{r}-J{r})/C{r}*100").number_format = "0.0"
tl = F0 + tr - 1
for k_, (lab, f_, nf_) in enumerate([("Наклон тренда (НАКЛОН, обуч.)", f"=SLOPE(C{F0}:C{tl},B{F0}:B{tl})", "0.00"),
                                      ("Пересечение (ОТРЕЗОК, обуч.)", f"=INTERCEPT(C{F0}:C{tl},B{F0}:B{tl})", "0.0"),
                                      ("Средний уровень (обуч.)", f"=AVERAGE(C{F0}:C{tl})", "0.0"),
                                      ("Средний уровень (все 30 мес.)", f"=AVERAGE(C{F0}:C{Lr})", "0.0")]):
    wsP.cell(5 + k_, 13, lab).font = B; wsP.cell(5 + k_, 15, f_).number_format = nf_
wsP.cell(10, 13, "3.3. Сезонные индексы").font = H1
header(wsP, 12, ["№ мес.", "Индекс (обуч. 27 мес.)", "Индекс (все 30 мес.)", "Лет в обуч."], col=13)
for k_ in range(12):
    r = 13 + k_
    wsP.cell(r, 13, k_ + 1)
    wsP.cell(r, 14, f"=AVERAGEIFS($C${F0}:$C${Lr},$G${F0}:$G${Lr},M{r},$E${F0}:$E${Lr},1)/$O$7").number_format = "0.00"
    wsP.cell(r, 15, f"=AVERAGEIF($G${F0}:$G${Lr},M{r},$C${F0}:$C${Lr})/$O$8").number_format = "0.00"
    wsP.cell(r, 16, f"=COUNTIFS($G${F0}:$G${Lr},M{r},$E${F0}:$E${Lr},1)")
# индексы обучающей выборки лежат в N, а VLOOKUP смотрит на M:O колонку 2 = N — верно
# 4.1–4.2
r = Lr + 2
wsP.cell(r, 1, "4.1–4.2. Отложенный период (авг–окт 2010): модель против наивных прогнозов").font = H1
header(wsP, r + 1, ["Месяц", "Факт", "Модель", "Ошибка, %", "«Как в прошлом мес.» (июль)", "Ошибка, %",
                    "«Как в прошлом мес.» (на шаг)", "Ошибка, %", "«Как год назад»", "Ошибка, %"])
for k_ in range(H):
    rr2, sr = r + 2 + k_, F0 + tr + k_
    wsP.cell(rr2, 1, f"=A{sr}").number_format = "mmm yyyy"
    wsP.cell(rr2, 2, f"=C{sr}"); wsP.cell(rr2, 3, f"=J{sr}").number_format = "0.0"
    wsP.cell(rr2, 5, f"=$C${F0 + tr - 1}"); wsP.cell(rr2, 7, f"=C{sr - 1}"); wsP.cell(rr2, 9, f"=C{sr - 12}")
    for c_ in (3, 5, 7, 9):
        wsP.cell(rr2, c_ + 1, f"=ABS(B{rr2}-{L(c_)}{rr2})/B{rr2}*100").number_format = "0.0"
mr = r + 2 + H
wsP.cell(mr, 1, "MAPE, %").font = B
for c_ in (4, 6, 8, 10):
    wsP.cell(mr, c_, f"=AVERAGE({L(c_)}{r+2}:{L(c_)}{r+1+H})").number_format = "0.0"
wsP.cell(mr + 1, 1, "«На шаг» подставляет факт августа и сентября, которого на дату прогноза (конец июля) ещё нет; честное сравнение — столбец «июль».").font = NOTE
# прогноз вперёд
fr = mr + 3
wsP.cell(fr, 1, "3.4. Прогноз на 3 месяца вперёд (тренд и индексы пересчитаны по всем 30 мес.)").font = H1
wsP.cell(fr + 1, 1, "Наклон (30 мес.)").font = B; wsP.cell(fr + 1, 5, f"=SLOPE(C{F0}:C{Lr},B{F0}:B{Lr})").number_format = "0.00"
wsP.cell(fr + 2, 1, "Пересечение (30 мес.)").font = B; wsP.cell(fr + 2, 5, f"=INTERCEPT(C{F0}:C{Lr},B{F0}:B{Lr})").number_format = "0.0"
wsP.cell(fr + 3, 1, "Ширина интервала, ±%").font = B; wsP.cell(fr + 3, 5, f"=MAX(D{r+2}:D{r+1+H})").number_format = "0"
wsP.cell(fr + 3, 6, "худшая ошибка модели на отложенных месяцах; грубая эмпирическая полоса, не доверительный интервал").font = NOTE
header(wsP, fr + 5, ["Месяц", "t", "№ мес.", "Индекс (30 мес.)", "Тренд", "Прогноз", "Нижняя граница", "Верхняя граница"])
for k_, (mm, tt, mo_) in enumerate(zip(["ноя 2010", "дек 2010", "янв 2011"], fut_t, fut_m)):
    rr2 = fr + 6 + k_
    wsP.cell(rr2, 1, mm); wsP.cell(rr2, 2, int(tt)); wsP.cell(rr2, 3, mo_)
    wsP.cell(rr2, 4, f"=VLOOKUP(C{rr2},$M$13:$O$24,3,FALSE)").number_format = "0.00"
    wsP.cell(rr2, 5, f"=$E${fr+2}+$E${fr+1}*B{rr2}").number_format = "0.0"
    wsP.cell(rr2, 6, f"=E{rr2}*D{rr2}").number_format = "0"
    wsP.cell(rr2, 7, f"=MAX(F{rr2}*(1-$E${fr+3}/100),0)").number_format = "0"
    wsP.cell(rr2, 8, f"=F{rr2}*(1+$E${fr+3}/100)").number_format = "0"
# график ряда
lc = LineChart(); lc.title = "Открытые вклады по месяцам, скользящее среднее 12 мес. и прогноз"; lc.style = 12
lc.add_data(Reference(wsP, min_col=3, min_row=4, max_row=Lr), titles_from_data=True)
lc.add_data(Reference(wsP, min_col=6, min_row=4, max_row=Lr), titles_from_data=True)
lc.add_data(Reference(wsP, min_col=10, min_row=4, max_row=Lr), titles_from_data=True)
lc.set_categories(Reference(wsP, min_col=1, min_row=F0, max_row=Lr))
lc.series[2].graphicalProperties.line.dashStyle = "dash"
lc.x_axis.number_format = "mmm yy"; lc.y_axis.title = "Вкладов"; lc.width, lc.height = 24, 10
lc.x_axis.delete = False; lc.y_axis.delete = False
wsP.add_chart(lc, "R2")
# выводы
SR = R["series"]; mp = SR["mape"]; ma_v = list(SR["ma12"].values())
it = SR["idx_all"]; MN = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
best = max(it, key=it.get); worst = min(it, key=it.get)
tx = fr + 11
text(wsP, tx, [
    "3.1. Ряд:",
    f"   30 месяцев (май 2008 – октябрь 2010) — 2,5 годовых цикла, полных циклов два. В обучающей части 27 месяцев: у каждого месяца года всего 2–3 значения.",
    "   Ряд неоднороден: в 2008 банк делал тысячи звонков в месяц (до 7 957 в мае), с середины 2009 — 200–300, а доля согласий выросла с 3–6% до ~50%.",
    "   В сентябре 2008 звонков не было вовсе (0 вкладов), в декабре 2008 — 13 звонков. Это ряд работы колл-центра, а не спроса клиентов.",
    "3.2. Тренд:",
    f"   Скользящее среднее падает: {fn(ma_v[0],0)} вкладов в мес. (апр 2009) → около {fn(ma_v[11],0)} (мар 2010) → {fn(ma_v[-1],0)} (окт 2010). Направление менялось: рост до весны 2010, затем спад.",
    "3.3. Сезонность:",
    f"   Самый сильный месяц — {MN[best-1]} (индекс {fn(it[best],2)}), самый слабый — {MN[worst-1]} ({fn(it[worst],2)}).",
    "   Для банка это неправдоподобно как «спрос»: индексы показывают, в какие месяцы банк запускал кампании (май 2008 и 2009 — крупнейшие обзвоны),",
    "   а декабрь и сентябрь слабые потому, что в 2008 году в эти месяцы почти не звонили. Это сезонность решений банка, а не клиентов.",
    "3.4. Прогноз:",
    f"   Тренд по 27 мес.: {fn(SR['icpt'],1)} {'+' if SR['slope']>=0 else '−'} {fn(abs(SR['slope']),2)}·t. Прогноз вперёд: ноябрь 2010 ≈ {fn(fut[0])}, декабрь ≈ {fn(fut[1])}, январь 2011 ≈ {fn(fut[2])} вкладов, интервал ±{band:.0f}%.",
    f"   Проверка декабря на здравый смысл: декабрьский индекс держится на 1 вкладе в 2008 году, поэтому прогноз декабря почти наверняка занижен.",
    (f"   Проверка ноября: за 1–17 ноября 2010 открыто {nov10} вкладов; полный месяц — примерно {nov10*30//17}. " +
     (f"Это ниже нижней границы ({fn(SR['future'][0]['lo'])})." if nov10*30//17 < SR['future'][0]['lo'] else
      f"Это внутри интервала ({fn(SR['future'][0]['lo'])}–{fn(SR['future'][0]['hi'])}), но примерно вдвое ниже точечного прогноза {fn(fut[0])}: интервал широкий, потому что модель ошибается сильно.")),
    "4.3. Вывод:",
    f"   1) Бьёт ли модель наивные прогнозы? НЕТ. MAPE модели {mp['model']:.1f}% против {mp['naive_prev']:.1f}% у «как в прошлом месяце». «Как год назад» ({mp['naive_year']:.1f}%) модель бьёт,",
    "      но это слабая планка: год назад банк работал в другом режиме. Простое «как в прошлом месяце» оказалось не хуже модели — сезонность здесь не помогает.",
    "   2) Горизонт: не больше 1 месяца, и то наивным прогнозом. Два неполных цикла, у каждого месяца 2–3 значения, а сами циклы разные (режим 2008 ≠ режим 2010):",
    "      повторяемости, на которой держится сезонная модель, в данных нет.",
    "   3) Что сделает прогноз неверным:",
    "      • банк запустит или свернёт кампанию (как в сентябре 2008, когда звонков не было вовсе) — число вкладов определяется числом звонков, а не календарём;",
    "      • изменятся ставки по вкладам (решения ЕЦБ, кризис 2008–2010) или конкурент предложит ставку выше — доля согласий упадёт или вырастет независимо от сезона.",
])
widths(wsP, [12, 5, 11, 9, 9, 11, 8, 10, 9, 12, 10, 3, 30, 12, 12, 10])

# PNG ряда для отчёта
fig, ax = plt.subplots(figsize=(10, 4.2))
xs = dep.index.to_timestamp()
ax.plot(xs, dep.values, "-o", ms=3, color=C1, label="Открыто вкладов")
ax.plot(xs, ma.values, color=C2, lw=2.2, label="Скользящее среднее, 12 мес.")
ax.plot(xs[tr:], FC["res"]["model"], "s", color="#c0392b", ms=6, label="Прогноз модели на отложенные 3 мес.")
fx = pd.date_range("2010-11-01", periods=3, freq="MS")
ax.plot(fx, fut, "D", color="#8e44ad", ms=5, label=f"Прогноз вперёд, полоса ±{band:.0f}%")
ax.fill_between(fx, [max(v * (1 - band / 100), 0) for v in fut], [v * (1 + band / 100) for v in fut], color="#8e44ad", alpha=.15)
ax2 = ax.twinx(); ax2.bar(xs, calls.values, width=20, color=C3, alpha=.18); ax2.set_ylabel("Звонков (серые столбцы)", color=C3)
ax2.spines["top"].set_visible(False)
ax.axvspan(xs[tr] - pd.Timedelta(days=15), xs[-1] + pd.Timedelta(days=15), color="#c0392b", alpha=.06)
ax.set(ylabel="Вкладов в месяц", title="Bank Marketing: открытые вклады по месяцам (год восстановлен по порядку строк)")
ax.legend(fontsize=8, loc="upper right", frameon=False); fig.tight_layout()
fig.savefig(f"{out}/3_series.png", dpi=130); plt.close(fig)
