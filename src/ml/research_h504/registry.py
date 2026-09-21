from __future__ import annotations
import hashlib, json
from pathlib import Path


def stable_hash(payload) -> str:
    raw=json.dumps(payload,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()

class Registry:
    def __init__(self,path:Path): self.path=path; path.parent.mkdir(parents=True,exist_ok=True)
    def rows(self):
        if not self.path.exists(): return []
        out=[]
        for line in self.path.read_text(encoding='utf-8').splitlines():
            if line.strip(): out.append(json.loads(line))
        return out
    def has_complete(self,signature): return self.latest_complete(signature) is not None
    def latest_complete(self,signature):
        for r in reversed(self.rows()):
            if r.get('signature')==signature and str(r.get('status','')).startswith('COMPLETE'):
                return r
        return None
    def append(self,row):
        with self.path.open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False,default=str)+'\n')
