from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import copy, hashlib, json, math, os, random, time
import numpy as np
import pandas as pd


def tcn_receptive_field(kernel_size: int=3, dilations=(1,2,4,8,16,32), convs_per_block: int=2) -> int:
    return 1 + convs_per_block*(kernel_size-1)*sum(dilations)


def _targets(panel: pd.DataFrame) -> pd.DataFrame:
    p=panel.sort_values(['code','market_session_id']).reset_index(drop=True).copy()
    g=p.groupby('code',sort=False)
    sid1=g['market_session_id'].shift(-1); close1=g['close'].shift(-1)
    p['aux_ret1']=np.log(close1/p['close'])
    p.loc[(sid1-p['market_session_id'])!=1,'aux_ret1']=np.nan
    # realised 5-session future volatility only if all 5 next market sessions exist contiguously
    fut=[]
    for h in range(1,6):
        fut.append(np.log(g['close'].shift(-h)/g['close'].shift(-(h-1))))
    arr=np.column_stack([s.to_numpy(float) for s in fut])
    sids=np.column_stack([g['market_session_id'].shift(-h).to_numpy(float) for h in range(1,6)])
    expected=p['market_session_id'].to_numpy(float)[:,None]+np.arange(1,6)[None,:]
    ok=np.isfinite(arr).all(1)&np.isfinite(sids).all(1)&(sids==expected).all(1)
    rv=np.full(len(p),np.nan); rv[ok]=np.sqrt(np.mean(arr[ok]**2,axis=1))
    p['aux_rv5']=rv
    return p[['code','date','market_session_id','aux_ret1','aux_rv5']]


@dataclass
class AuxSplit:
    train_end_session: int
    dev_start_session: int
    dev_end_session: int


def choose_aux_split(sessions: np.ndarray, dev_fraction: float=.2, embargo: int=5) -> AuxSplit:
    u=np.sort(np.unique(sessions.astype(int)))
    if len(u)<100:
        raise ValueError('need at least 100 sessions for AUX time split')
    dev_n=max(20,int(round(len(u)*dev_fraction)))
    dev_start_i=len(u)-dev_n
    train_end_i=dev_start_i-embargo-1
    if train_end_i<30:
        raise ValueError('not enough pre-dev sessions after embargo')
    return AuxSplit(int(u[train_end_i]),int(u[dev_start_i]),int(u[-1]))


def build_sequence_index(frame: pd.DataFrame, window: int, split: AuxSplit):
    """Return anchor row indices whose last `window` rows are consecutive sessions."""
    train=[]; dev=[]
    for _, idx in frame.groupby('code',sort=False).groups.items():
        idx=np.asarray(list(idx),dtype=int)
        s=frame.loc[idx,'market_session_id'].to_numpy(int)
        eligible=frame.loc[idx,['aux_ret1','aux_rv5']].notna().all(axis=1).to_numpy()
        for j in range(window-1,len(idx)):
            if not eligible[j]: continue
            w=s[j-window+1:j+1]
            if not np.all(np.diff(w)==1): continue
            anchor=int(s[j])
            if anchor<=split.train_end_session: train.append(int(idx[j]))
            elif split.dev_start_session<=anchor<=split.dev_end_session: dev.append(int(idx[j]))
    return np.asarray(train,dtype=int), np.asarray(dev,dtype=int)


def run_aux_tcn(features: pd.DataFrame, panel: pd.DataFrame, feature_cols: list[str], out_dir: Path,
                *, seed: int=17, window: int=128, max_epochs: int=30, patience: int=5,
                batch_size: int=256, lr: float=1e-3, weight_decay: float=1e-3,
                deadline_monotonic: float | None=None, resume: bool=True, data_signature: str | None=None) -> dict:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError as e:
        return {'status':'BLOCKED_ENV','reason':f'torch unavailable: {e}'}
    os.environ.setdefault('OMP_NUM_THREADS','4'); os.environ.setdefault('MKL_NUM_THREADS','4')
    torch.set_num_threads(min(4,max(1,torch.get_num_threads())))
    torch.manual_seed(seed); np.random.seed(seed); random.seed(seed)
    f=features.sort_values(['code','market_session_id']).reset_index(drop=True).copy()
    ps=panel.copy(); ps['date']=pd.to_datetime(ps['date']); ps=ps.sort_values(['code','date']).reset_index(drop=True)
    sid_map=f[['code','date','market_session_id']].copy(); sid_map['date']=pd.to_datetime(sid_map['date'])
    ps['code']=ps['code'].astype(str); sid_map['code']=sid_map['code'].astype(str)
    ps=ps.merge(sid_map,on=['code','date'],how='left',validate='one_to_one')
    tgt=_targets(ps)
    # align on code/date after sorting; defensive merge avoids silent row-order assumption
    f=f.merge(tgt,on=['code','date','market_session_id'],how='left',validate='one_to_one')
    split=choose_aux_split(f['market_session_id'].to_numpy())
    train_idx,dev_idx=build_sequence_index(f,window,split)
    if len(train_idx)<1000 or len(dev_idx)<200:
        return {'status':'BLOCKED_DATA','reason':f'insufficient AUX windows train={len(train_idx)} dev={len(dev_idx)}'}
    X=f[feature_cols].apply(pd.to_numeric,errors='coerce').to_numpy('float32')
    # train-only robust normalization, NaN->0 after explicit mask
    train_rows=f['market_session_id'].to_numpy()<=split.train_end_session
    med=np.nanmedian(X[train_rows],axis=0); q1=np.nanquantile(X[train_rows],.25,axis=0); q3=np.nanquantile(X[train_rows],.75,axis=0)
    scale=q3-q1; scale[~np.isfinite(scale)|(scale<1e-6)]=1.0; med[~np.isfinite(med)]=0.0
    mask=np.isfinite(X).astype('float32'); X=np.where(np.isfinite(X),(X-med)/scale,0).astype('float32')
    Z=np.concatenate([X,mask],axis=1)
    y_cls=(f['aux_ret1'].to_numpy(float)>0).astype('float32'); y_rv=np.log1p(f['aux_rv5'].to_numpy(float)*100).astype('float32')
    sid=f['market_session_id'].to_numpy(int); codes=f['code'].astype(str).to_numpy()
    code_groups={c:np.asarray(list(idx),dtype=int) for c,idx in f.groupby('code',sort=False).groups.items()}
    pos_in_group=np.empty(len(f),dtype=int); start_for=np.empty(len(f),dtype=int)
    for c,idx in code_groups.items():
        for j,row in enumerate(idx): pos_in_group[row]=j; start_for[row]=idx[max(0,j-window+1)]
    class SeqDS(Dataset):
        def __init__(self,anchors): self.anchors=np.asarray(anchors,dtype=int)
        def __len__(self): return len(self.anchors)
        def __getitem__(self,k):
            a=int(self.anchors[k]); c=codes[a]; idx=code_groups[c]; j=pos_in_group[a]; rows=idx[j-window+1:j+1]
            return torch.from_numpy(Z[rows]), torch.tensor(y_cls[a]), torch.tensor(y_rv[a]), torch.tensor(a)
    class CausalBlock(nn.Module):
        def __init__(self,cin,cout,dilation,drop=.1):
            super().__init__(); pad=2*dilation
            self.c1=nn.Conv1d(cin,cout,3,dilation=dilation); self.c2=nn.Conv1d(cout,cout,3,dilation=dilation)
            self.pad=pad; self.drop=nn.Dropout(drop); self.act=nn.ReLU(); self.proj=nn.Conv1d(cin,cout,1) if cin!=cout else nn.Identity()
        def _conv(self,x,conv): return conv(torch.nn.functional.pad(x,(self.pad,0)))
        def forward(self,x):
            r=self.proj(x); y=self.drop(self.act(self._conv(x,self.c1))); y=self.drop(self.act(self._conv(y,self.c2))); return self.act(y+r)
    class TCN(nn.Module):
        def __init__(self,nin):
            super().__init__(); blocks=[]; c=nin
            for d in (1,2,4,8,16,32): blocks.append(CausalBlock(c,32,d)); c=32
            self.net=nn.Sequential(*blocks); self.cls=nn.Linear(32,1); self.rv=nn.Linear(32,1)
        def forward(self,x):
            h=self.net(x.transpose(1,2))[:,:,-1]; return self.cls(h).squeeze(1), self.rv(h).squeeze(1)
    # CPU is the default: availability is not authorization to occupy a GPU.
    device=torch.device('cpu')
    out_dir.mkdir(parents=True,exist_ok=True)
    model=TCN(Z.shape[1]).to(device); opt=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=weight_decay)
    bce=nn.BCEWithLogitsLoss(); mse=nn.MSELoss()
    train_gen=torch.Generator(); train_gen.manual_seed(seed)
    train_loader=DataLoader(SeqDS(train_idx),batch_size=batch_size,shuffle=True,num_workers=0,generator=train_gen)
    dev_loader=DataLoader(SeqDS(dev_idx),batch_size=batch_size,shuffle=False,num_workers=0)
    if data_signature is None:
        data_signature=hashlib.sha256(pd.util.hash_pandas_object(f[['code','date',*feature_cols,'aux_ret1','aux_rv5']],index=False).to_numpy().tobytes()).hexdigest()
    config_payload={'data_signature':data_signature,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'feature_cols':feature_cols,'seed':int(seed),'window':int(window),'batch_size':int(batch_size),'lr':float(lr),'weight_decay':float(weight_decay),'patience':int(patience)}
    config_hash=hashlib.sha256(json.dumps(config_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    hist=[]; best=math.inf; best_state=None; best_optimizer=None; best_epoch=0; wait=0; start_epoch=0; resumed=False
    last_path=out_dir/'last.pt'
    if resume and last_path.exists():
        ck=torch.load(last_path,map_location='cpu',weights_only=False)
        ck_hash=ck.get('config_hash')
        if ck_hash != config_hash:
            return {'status':'BLOCKED_CHECKPOINT_MISMATCH','seed':seed,'reason':'existing last.pt was created with a different training configuration','checkpoint_config_hash':ck_hash,'requested_config_hash':config_hash,'checkpoint':str(last_path)}
        if ck.get('feature_cols')==feature_cols and int(ck.get('seed',-1))==int(seed) and int(ck.get('window',window))==int(window):
            model.load_state_dict(ck['model']); opt.load_state_dict(ck['optimizer'])
            best=float(ck.get('best',math.inf)); best_state=ck.get('best_model'); best_optimizer=ck.get('best_optimizer'); best_epoch=int(ck.get('best_epoch',0)); wait=int(ck.get('wait',0)); start_epoch=int(ck.get('epoch',0)); hist=list(ck.get('history',[])); resumed=True
            if 'train_generator_state' in ck: train_gen.set_state(ck['train_generator_state'])
            if 'torch_rng_state' in ck: torch.set_rng_state(ck['torch_rng_state'])
            if 'numpy_rng_state' in ck: np.random.set_state(ck['numpy_rng_state'])
            if 'python_rng_state' in ck: random.setstate(ck['python_rng_state'])
    def _checkpoint(path, epoch_number):
        payload={'model':copy.deepcopy(model.state_dict()),'optimizer':copy.deepcopy(opt.state_dict()),'seed':seed,'feature_cols':feature_cols,'median':med,'scale':scale,'split':split.__dict__,'rf':tcn_receptive_field(),'window':window,'epoch':epoch_number,'best':best,'best_model':best_state,'best_optimizer':best_optimizer,'best_epoch':best_epoch,'wait':wait,'history':hist,'train_generator_state':train_gen.get_state(),'torch_rng_state':torch.get_rng_state(),'numpy_rng_state':np.random.get_state(),'python_rng_state':random.getstate(),'config_hash':config_hash,'config_payload':config_payload}
        temporary=Path(str(path)+'.tmp'); torch.save(payload,temporary); os.replace(temporary,path)
    start=time.time(); interrupted=False
    for epoch in range(start_epoch,max_epochs):
        if deadline_monotonic is not None and time.monotonic()>=deadline_monotonic:
            interrupted=True; break
        model.train(); losses=[]; grad_pre=[]
        for xb,yb,rvb,_ in train_loader:
            if deadline_monotonic is not None and time.monotonic()>=deadline_monotonic:
                interrupted=True; break
            xb=xb.to(device); yb=yb.to(device); rvb=rvb.to(device); opt.zero_grad(set_to_none=True)
            lc,lrh=model(xb); loss=bce(lc,yb)+0.25*mse(lrh,rvb); loss.backward()
            gn=torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); grad_pre.append(float(gn)); opt.step(); losses.append(float(loss.detach().cpu()))
        if interrupted:
            _checkpoint(last_path,epoch); break
        model.eval(); dl=[]; probs=[]; dev_y=[]; pred_rv=[]; true_rv=[]; anchor=[]
        with torch.no_grad():
            for xb,yb,rvb,ai in dev_loader:
                lc,lrh=model(xb.to(device)); loss=bce(lc,yb.to(device))+0.25*mse(lrh,rvb.to(device)); dl.append(float(loss.cpu()))
                probs.extend(torch.sigmoid(lc).cpu().numpy().tolist()); dev_y.extend(yb.numpy().tolist()); pred_rv.extend(lrh.cpu().numpy().tolist()); true_rv.extend(rvb.numpy().tolist()); anchor.extend(ai.numpy().tolist())
        dloss=float(np.mean(dl)); row={'epoch':epoch+1,'train_loss':float(np.mean(losses)),'dev_loss':dloss,'grad_preclip_mean':float(np.mean(grad_pre)),'lr':opt.param_groups[0]['lr']}; hist.append(row)
        if dloss<best-1e-5:
            best=dloss; wait=0; best_epoch=epoch+1; best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}; best_optimizer=copy.deepcopy(opt.state_dict())
            _checkpoint(out_dir/'best.pt',epoch+1)
        else: wait+=1
        _checkpoint(last_path,epoch+1)
        (out_dir/'train_history.json').write_text(json.dumps(hist,indent=2),encoding='utf-8')
        if wait>=patience: break
    if interrupted:
        return {'status':'INTERRUPTED_BUDGET','seed':seed,'train_windows':int(len(train_idx)),'dev_windows':int(len(dev_idx)),'epochs':len(hist),'resume_from_epoch':int(hist[-1]['epoch']) if hist else start_epoch,'resumed':resumed,'device':str(device),'elapsed_sec':time.time()-start,'checkpoint':str(last_path)}
    if best_state is None:
        return {'status':'BLOCKED_TRAINING','reason':'no finite dev epoch produced a best checkpoint','seed':seed,'epochs':len(hist),'resumed':resumed}
    model.load_state_dict(best_state)
    # Rewrite best with a model/optimizer pair from the same best epoch; never pair best model with final optimizer.
    best_payload=torch.load(out_dir/'best.pt',map_location='cpu',weights_only=False)
    best_payload['model']=best_state; best_payload['optimizer']=best_optimizer; best_payload['epoch']=best_epoch; best_payload['best_epoch']=best_epoch; torch.save(best_payload,out_dir/'best.pt')
    (out_dir/'train_history.json').write_text(json.dumps(hist,indent=2),encoding='utf-8')
    # regenerate dev predictions from best
    model.eval(); rows=[]
    with torch.no_grad():
        for xb,yb,rvb,ai in dev_loader:
            lc,lrh=model(xb.to(device)); pp=torch.sigmoid(lc).cpu().numpy(); rr=lrh.cpu().numpy()
            for a,pv,rvp,yv,rvt in zip(ai.numpy(),pp,rr,yb.numpy(),rvb.numpy()):
                rows.append({'row_index':int(a),'code':str(f.loc[int(a),'code']),'date':str(pd.Timestamp(f.loc[int(a),'date']).date()),'score_ret_up':float(pv),'label_ret_up':float(yv),'pred_log_rv5':float(rvp),'label_log_rv5':float(rvt)})
    pred=pd.DataFrame(rows); pred.to_csv(out_dir/'dev_predictions.csv',index=False)
    eps=1e-6; y=pred.label_ret_up.to_numpy(float); pr=np.clip(pred.score_ret_up.to_numpy(float),eps,1-eps)
    logloss=float(-np.mean(y*np.log(pr)+(1-y)*np.log(1-pr))); brier=float(np.mean((pr-y)**2)); rv_rmse=float(np.sqrt(np.mean((pred.pred_log_rv5-pred.label_log_rv5)**2)))
    res={'status':'COMPLETE_AUX','seed':seed,'train_windows':int(len(train_idx)),'dev_windows':int(len(dev_idx)),'epochs':len(hist),'best_dev_loss':best,'logloss_ret_up':logloss,'brier_ret_up':brier,'rmse_log_rv5':rv_rmse,'device':str(device),'elapsed_sec':time.time()-start,'parameter_count':sum(p.numel() for p in model.parameters()),'receptive_field':tcn_receptive_field(),'representation_features':len(feature_cols),'best_epoch':best_epoch,'resumed':resumed,'last_checkpoint':str(last_path),'best_checkpoint':str(out_dir/'best.pt'),'config_hash':config_hash}
    (out_dir/'metrics.json').write_text(json.dumps(res,indent=2),encoding='utf-8'); return res
