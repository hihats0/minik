"""Erken cikis tavani (fikir 183/202): D4 modelinin her katmaninda bagli cikisla tahmin; son katmanla
ayni mi, ek parcasinda mi kelime basinda mi. Cagiran: elle `PYTHONPATH=. python araclar/erken_cikis_olc.py` (CPU).
"""
import torch, torch.nn.functional as F, numpy as np, sentencepiece as spm
from cocuk import degerlendir as dg, egit_araclari as ea
torch.manual_seed(0)
model,_=dg.yukle("d4-transformer", torch.device("cpu"))
sp=spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
ek=np.array([not sp.id_to_piece(i).startswith("▁") and sp.id_to_piece(i).isalpha() for i in range(sp.get_piece_size())])
v=ea.veri_ac("dogrulama"); P=40; L=512
sonuc={k:[] for k in range(7)}; ekm=[]; dogru=[]
with torch.no_grad():
  for i in range(P):
    ids=torch.from_numpy(v[i*20000:i*20000+L+1].astype(np.int64))[None]
    x=model.gomme(ids[:,:-1]); ara=[]
    for b in model.bloklar:
      x=b(x,model.cos,model.sin); ara.append(F.linear(model.son_norm(x),model.gomme.weight))
    son=ara[-1].argmax(-1)
    for k,lg in enumerate(ara):
      p=lg.softmax(-1); g,a=p.max(-1); sonuc[k].append(torch.stack([(a==son).float(),g,(a==ids[:,1:]).float()],-1)[0])
    ekm.append(torch.from_numpy(ek[ids[0,1:].numpy()]))
ekm=torch.cat(ekm)
for k in range(7):
  r=torch.cat(sonuc[k]); g=r[:,1]>0.9
  print(f"katman {k+1}: son ile ayni %{100*r[:,0].mean():.1f} | eminlik>0.9 olan %{100*g.float().mean():.1f} (onlarda son ile ayni %{100*r[g,0].mean():.1f}) | ek tokeninda ayni %{100*r[ekm,0].mean():.1f}, kelime basinda %{100*r[~ekm,0].mean():.1f} | dogru %{100*r[:,2].mean():.1f}")
r=torch.cat(sonuc[6]); print("ek token orani", round(ekm.float().mean().item(),3), "| son katman dogru: ek %", round(100*r[ekm,2].mean().item(),1), "kelime basi %", round(100*r[~ekm,2].mean().item(),1), "| ek ort eminlik", round(r[ekm,1].mean().item(),3), "kelime basi", round(r[~ekm,1].mean().item(),3))
