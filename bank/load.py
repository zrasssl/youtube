"""Читает лист «Данные» из файла студента и строит числовые переменные."""
import pandas as pd, numpy as np

def load(path):
    df = pd.read_excel(path, sheet_name="Данные", usecols="A:Q")
    df = df.rename(columns={" ": "campaign"})
    d = pd.DataFrame({
        "age": df.age, "balance": df.balance, "duration": df.duration, "campaign": df.campaign,
        "pdays": df.pdays, "previous": df.previous, "day": df.day,
        "housing": (df.housing == "yes").astype(int), "loan": (df.loan == "yes").astype(int),
        "default": (df.default == "yes").astype(int),
        "contacted_before": (df.pdays != -1).astype(int),
        "prev_success": (df.poutcome == "success").astype(int),
        "y": (df.y == "yes").astype(int),
    })
    return df, d
