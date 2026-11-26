import pandas as pd, numpy as np, sys
src = sys.argv[1]
df = pd.read_csv(src, dtype={'Invoice':str,'StockCode':str}, parse_dates=['InvoiceDate'])
n0=len(df)
df = df[~df.Invoice.str.startswith('C')]
df = df[(df.Quantity>0)&(df.Price>0)]
# служебные коды (почта, ручные корректировки, комиссии)
svc = df.StockCode.str.upper().isin(['POST','DOT','M','D','C2','BANK CHARGES','AMAZONFEE','S','B','PADS','ADJUST','ADJUST2','TEST001','TEST002','CRUK','GIFT'])
df = df[~svc & df.StockCode.str.match(r'^\d')]
df['Revenue']=df.Quantity*df.Price
print(n0, len(df))
df.to_pickle(sys.argv[2])
m = df.set_index('InvoiceDate').Revenue.resample('MS').sum()
o = df.set_index('InvoiceDate').Invoice.resample('MS').nunique()
print(pd.DataFrame({'rev':m.round(0),'orders':o}))
print(df.InvoiceDate.max())
