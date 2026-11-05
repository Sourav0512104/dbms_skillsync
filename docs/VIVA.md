# Viva cheat sheet

**Why PostgreSQL?** Fixed relational structure, FK integrity, joins, transactions, constraints and query planning.

**Why MongoDB?** Resume/portfolio/project-context documents are heterogeneous and naturally retrieved as documents.

**Why embeddings?** They capture semantic similarity so paraphrased skills can match without exact keywords.

**Why BGE-small?** Retrieval-oriented, 384-dimensional and feasible on CPU; model can be swapped through an environment variable.

**Why CrossEncoder?** It jointly scores the role/profile pair and is used only after cheap retrieval because pairwise scoring is more expensive.

**Why HNSW?** Approximate nearest-neighbor graph indexing trades some recall for lower vector-search latency.

**Why extended statistics?** They give PostgreSQL multivariate information when columns are correlated and can improve planner estimates.

**Why workload shift?** It tests whether a tuning choice remains useful after query frequency/distribution changes.

**Why row locking?** Two concurrent applicants must not both consume the same final slot. `SELECT ... FOR UPDATE` serializes access to the role row.

**What is the research contribution?** Not a new embedding algorithm. It is a reproducible DBMS/system study integrating relational integrity, document storage, hybrid semantic retrieval, reranking, vector indexing, query tuning and workload drift.
