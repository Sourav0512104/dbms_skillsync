import json,re,numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer,CrossEncoder

def tok(s): return set(re.findall(r'[a-z0-9+#.]+',s.lower()))
def lexical(q,d): return len(tok(q)&tok(d))/max(1,len(tok(q)))
def cosine(a,b): return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-12))

def main():
 data=json.loads(Path('evaluation/gold_pairs.json').read_text())
 model=SentenceTransformer('BAAI/bge-small-en-v1.5'); rr=CrossEncoder('cross-encoder/ms-marco-MiniLM-L6-v2')
 # Turn each positive pair into a small retrieval set with controlled hard negatives.
 rows=[]
 for item in data:
  q=item['role']; pos=item['positive']
  negatives=[x['positive'] for x in data if x['positive']!=pos]
  docs=[pos]+negatives
  qv=model.encode(q,normalize_embeddings=True); dv=model.encode(docs,normalize_embeddings=True)
  dense=[cosine(qv,x) for x in dv]; lex=[lexical(q,x) for x in docs]; rer=[float(x) for x in rr.predict([(q,x) for x in docs])]
  for name,scores in [('lexical',lex),('dense',dense),('reranker',rer)]:
   rank=int(np.argsort(-np.array(scores))[0]); rows.append({'query':q,'method':name,'positive_rank':rank+1,'hit_at_1':int(rank==0)})
 out=Path('results'); out.mkdir(exist_ok=True); Path(out/'matching_metrics.csv').write_text('query,method,positive_rank,hit_at_1\n'+'\n'.join(f"{r['query']!r},{r['method']},{r['positive_rank']},{r['hit_at_1']}" for r in rows))
 print('Wrote results/matching_metrics.csv')
if __name__=='__main__': main()
