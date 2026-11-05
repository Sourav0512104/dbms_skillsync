# Research design

## Core research question
How should a teammate-matching DBMS combine structured constraints, dense retrieval and neural reranking while remaining efficient under scale and workload drift?

## Experimental arms
1. Lexical/keyword baseline vs BGE dense retrieval vs BGE + CrossEncoder.
2. Exact cosine vs pgvector HNSW; report Recall@10 and latency.
3. SQL tuning: baseline vs composite/partial indexes vs extended statistics vs materialized views.
4. Workload shift: W1 profile-search heavy; W2 analytics heavy.
5. Polyglot storage: normalized PostgreSQL vs JSONB vs MongoDB for point reads, nested filters, updates and document retrieval.

## Metrics
Precision@K, Recall@K, MRR, nDCG@K; median and p95 latency; execution time; shared buffer hits/reads; planner estimated rows vs actual rows; HNSW recall.

## Important validity rule
Do not use the same labeled pairs to tune the model and report final performance. Keep development and final evaluation sets separate. Repeat DB benchmarks several times and report the machine specification, cache state and configuration.

## Research claim
The individual technologies are established. The research-grade contribution is the reproducible integrated study of hybrid retrieval, database design, vector indexing, concurrency and workload drift. Do not claim a new embedding model or new HNSW algorithm.
