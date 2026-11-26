"""Помесячный ряд из Bank Marketing: год восстанавливается по порядку строк (данные идут хронологически, 05.2008–11.2010)."""
import numpy as np, pandas as pd

MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

def year_month(raw):
    mn = raw.month.map({m: i for i, m in enumerate(MON, 1)}).values
    yr = 2008 + np.concatenate([[0], np.cumsum(np.diff(mn) < 0)])
    return yr, mn

def monthly(raw, d):
    yr, mn = year_month(raw)
    s = pd.DataFrame({"y": yr, "m": mn, "dep": d.y.values}).groupby(["y", "m"]).dep.agg(["sum", "size"])
    idx = pd.period_range("2008-05", "2010-10", freq="M")          # ноябрь 2010 неполный (до 17-го) — исключён
    dep = pd.Series([int(s["sum"].get((p.year, p.month), 0)) for p in idx], index=idx)
    calls = pd.Series([int(s["size"].get((p.year, p.month), 0)) for p in idx], index=idx)
    return dep, calls

def forecast(s, H=3):
    """Тренд (ЛИНЕЙН по сырому ряду без последних H мес.) × сезонный индекс (средний месяц / общий средний)."""
    n = len(s); t = np.arange(1, n + 1); tr = n - H; m = s.index.month
    idx = s[:tr].groupby(m[:tr]).mean() / s[:tr].mean()
    b, a = np.polyfit(t[:tr], s.values[:tr], 1)
    fc = (a + b * t) * idx.reindex(m).values
    fact = s.values[tr:]
    res = {"fact": fact, "model": fc[tr:], "naive_prev": np.repeat(s.values[tr - 1], H),
           "naive_prev_1step": s.values[tr - 1:n - 1], "naive_year": s.values[tr - 12:n - 12]}
    mape = {k: float(np.mean(np.abs(fact - v) / fact * 100)) for k, v in res.items() if k != "fact"}
    return dict(idx=idx, slope=b, icpt=a, fc=fc, res=res, mape=mape, tr=tr)
