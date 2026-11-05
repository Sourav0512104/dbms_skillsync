import os,subprocess,json,time
from pathlib import Path
R=Path('/app/results'); R.mkdir(exist_ok=True)
def run(c):
 print('>>>',c); p=subprocess.run(c,shell=True); p.check_returncode()
if __name__=='__main__':
 run('python -m app.bootstrap'); run('python scripts/seed_pgvector.py'); run('python benchmarks/run_sql_benchmark.py'); run('python benchmarks/vector_benchmark.py')
 (R/'experiment_manifest.json').write_text(json.dumps({'embedding_model':os.getenv('EMBEDDING_MODEL'),'reranker_model':os.getenv('RERANKER_MODEL'),'timestamp':time.strftime('%Y-%m-%dT%H:%M:%S'),'experiments':['matching','sql_tuning','exact_vs_hnsw','workload_shift','concurrency']},indent=2))
