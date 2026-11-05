import os,time,numpy as np,psycopg
DB=os.getenv('DATABASE_URL','postgresql://skillsync:skillsync@localhost:5432/skillsync')
def main():
 with psycopg.connect(DB) as c:
  with c.cursor() as cur: cur.execute('SELECT user_id,embedding FROM profile_vectors LIMIT 10000'); rows=cur.fetchall()
 if len(rows)<10: print('Run scripts/seed_pgvector.py first.'); return
 ids=np.array([r[0] for r in rows]); v=np.array([r[1] for r in rows],dtype=np.float32); q=v[0]/(np.linalg.norm(v[0])+1e-12)
 t=time.perf_counter(); sims=v@q; exact=ids[np.argsort(-sims)[:10]]; exact_ms=(time.perf_counter()-t)*1000
 with psycopg.connect(DB) as c:
  with c.cursor() as cur:
   cur.execute('SET hnsw.ef_search=64'); t=time.perf_counter(); cur.execute('SELECT user_id,1-(embedding <=> %s::vector) score FROM profile_vectors ORDER BY embedding <=> %s::vector LIMIT 10',(q.tolist(),q.tolist())); ann=cur.fetchall(); ann_ms=(time.perf_counter()-t)*1000
 overlap=len(set(exact.tolist()) & {x['user_id'] for x in ann})/10
 print({'exact_ms':exact_ms,'hnsw_ms':ann_ms,'recall_at_10':overlap,'exact_top10':exact.tolist(),'hnsw_top10':[x['user_id'] for x in ann]})
if __name__=='__main__': main()
