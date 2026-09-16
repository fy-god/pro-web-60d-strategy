import ctypes, pandas as pd, numpy as np, time, sys
class MS(ctypes.Structure):
    _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),
              ("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),
              ("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),
              ("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),
              ("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
m=MS(); m.dwLength=ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
print("RAM total GB", round(m.ullTotalPhys/1e9,1), "avail GB", round(m.ullAvailPhys/1e9,1))
t=time.time(); f=pd.read_parquet("outputs/ml/matrix_h10_t30_s5.parquet"); print("parquet read s", round(time.time()-t,2))
print("mem after read GB", round(f.memory_usage(deep=True).sum()/1e9,2))
print("sorted by code,date monotonic:", bool(f[['code','date']].apply(tuple,axis=1).is_monotonic_increasing) if len(f)<1 else "skip")
f2=f.sort_values(['code','date']).reset_index(drop=True)
print("equals sorted:", f.equals(f2))
print("code monotonic within consecutive blocks - checking head:", f['code'].head(3).tolist(), f['date'].head(3).tolist())
print("code values first 10:", f['code'].head(10).tolist())
print("date values first 10:", f['date'].head(10).astype(str).tolist())
