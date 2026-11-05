# SkillSync Research Edition

## Hybrid Semantic Team Formation + Polyglot DBMS + Vector Search + Reranking + Workload Study

This is an expanded research-grade implementation of SkillSync. It uses PostgreSQL for structured transactional data, MongoDB for flexible profile documents, sentence embeddings for semantic matching, and a hybrid ranking pipeline. It also includes triggers, views, indexes, pgvector/HNSW experiments, concurrency testing, scale generation and workload-shift experiments.

## 1. What you are building

```text
User/Project Owner
      |
      v
Next.js web app --> FastAPI
       |              |
       |              +--> Password hashing + signed bearer tokens
       |                    User-scoped profile/application APIs
       +---- HttpOnly session cookie / same-origin API proxy
                       |
          +------------+-------------+
          |                          |
          v                          v
     PostgreSQL                   MongoDB
 structured state             profile documents
 users/projects/roles         resume/bio/projects
 skills/applications          384-D embeddings
 transactions                 |
 views/statistics             |
 indexes/HNSW*                |
          |                    |
          +---------+----------+
                    v
             Hybrid matcher
                    |
        structured eligibility filter
                    |
          BGE semantic scoring
                    |
       candidate-pool shortlist
                    |
             CrossEncoder reranker
                    |
       explainable final hybrid score
                    |
              ranked teammates
```

`*` pgvector is an experimental comparison arm; MongoDB is still the document store in the main architecture.

## 2. Why this is stronger than the original lab version

### Original foundation retained
- 3NF relational schema
- MongoDB document store
- sentence embeddings
- structured filter + semantic ranking
- transactions and row-level locking
- trigger and view
- indexes, extended statistics, materialized views
- synthetic scale
- before/after tuning
- workload shift
- exact vs ANN vector comparison

### Added research/engineering depth
1. **Two-stage ranking**: PostgreSQL filters eligible users; BGE scores the candidate profiles by semantic similarity; a CrossEncoder then reranks the bounded candidate pool. This follows the retrieve-and-rerank pattern described by Sentence Transformers, with SQL filters rather than a vector index providing the initial pool.
2. **Explainable ranking**: the final score exposes semantic/reranker, skill-overlap, experience and availability components.
3. **pgvector HNSW arm**: embeddings mirrored into PostgreSQL so exact vector search and HNSW can be compared experimentally.
4. **Concurrency experiment**: the role row is locked before a slot is consumed.
5. **Planner experiment**: correlated predicates are measured before and after extended statistics.
6. **Workload drift**: profile-heavy and analytics-heavy mixes are measured separately.
7. **Reproducibility**: fixed random seed, environment variables, benchmark scripts and experiment manifest.
8. **Explicit validity limits**: synthetic data and model scores are not presented as real hiring evidence.
9. **Account-based workflows**: password-hashed sign-up/sign-in, short-lived signed sessions, private profile editing, profile visibility controls and application history.
10. **Product UI**: responsive Next.js workspace for role discovery, matching, profile management and project insights.

## 3. Model stack

### Main embedding model
`BAAI/bge-small-en-v1.5`

- English dense-retrieval sentence encoder based on a 12-layer BERT model.
- The model has a 384-dimensional hidden size and a configured maximum sequence
  length of 512 tokens. Sentence Transformers uses the model's CLS-token pooling
  configuration; longer input is truncated to the model's configured maximum.
- `embed()` requests L2-normalized embeddings and returns `float32` NumPy arrays.
- The role vector is compared with each eligible candidate's profile vector by
  cosine similarity. With normalized vectors, cosine similarity is their dot
  product (the helper still computes the cosine formula explicitly).

The model is configurable through `EMBEDDING_MODEL`. The project creates role
text from the role title, type, minimum experience and required skills. Profile
text is built from bio, resume, projects and skills. Saved profile embeddings
are stored in MongoDB alongside the profile document.

### Baseline embedding model
`sentence-transformers/all-MiniLM-L6-v2`

This is an optional alternative encoder, not the current default. Set
`EMBEDDING_MODEL` before starting the API and seeder to compare it:

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Reranker
`cross-encoder/ms-marco-MiniLM-L6-v2`

This six-layer MiniLM CrossEncoder was trained for MS MARCO passage ranking.
It receives each role/profile text pair together, allowing attention across
both texts, and returns a raw relevance score. It runs only on the bounded
candidate pool because scoring pairs is more expensive than independently
encoding texts. Its scores are ranking signals, not probabilities, and the
model has not been fine-tuned on SkillSync teammate data.

### Actual matching flow and final score

1. PostgreSQL filters profile-visible users by availability and minimum
   experience, excludes the requesting user and users with an active
   application, orders by experience, then applies `candidate_pool`.
2. The BGE model embeds the role and computes cosine similarity against the
   candidate profile embeddings. Missing profile vectors are generated and
   stored in MongoDB on demand.
3. If reranking is enabled for the request, the CrossEncoder scores the role
   against each candidate profile. The API/UI currently requests reranking.
4. The reranker scores are min-max normalized **within this candidate set**,
   then combined with non-model features:

   ```text
   final =
       0.55 * normalized_reranker
     + 0.25 * skill_overlap
     + 0.10 * experience_score
     + 0.10 * availability_score
   ```

`skill_overlap` is the fraction of role-required skills present in the
candidate's skills. Experience is capped using the role minimum plus two
years; availability is capped at 20 hours/week. The final score is a relative
ranking value, not a probability or a hiring recommendation.

**Important distinction:** the visible **Search roles** box uses PostgreSQL
text matching on role titles, project names and skill names. It does not invoke
the embedding model. Semantic teammate matching runs when **Find teammates**
is clicked. The main matcher computes BGE similarity over the SQL-filtered
candidate pool; it does not use pgvector HNSW to create that pool. `profile_vectors`
and HNSW are a separate experimental comparison path.

Model references: [BGE small English v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5),
[MS MARCO MiniLM L6 CrossEncoder](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2),
and [Sentence Transformers retrieve-and-rerank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html).

## 4. Setup

### Option A — Docker (recommended)

Install Docker Desktop and ensure its engine is running. From PowerShell in
the repository root, copy `.env.example` to `.env` and replace the example JWT
secret with a unique random value of at least 32 characters:

```powershell
Copy-Item .env.example .env
$secret = python -c "import secrets; print(secrets.token_hex(32))"
(Get-Content .env) -replace '^JWT_SECRET_KEY=.*$', "JWT_SECRET_KEY=$secret" | Set-Content .env
```

The example PostgreSQL password is suitable only for local development. For a
local demo it is used consistently in both `POSTGRES_PASSWORD` and
`DATABASE_URL`. For any shared or deployed environment, replace it in both
places with a strong secret. Never commit `.env`.

Build and start all services:

```powershell
docker compose up --build -d
```

The `seed` service initializes the demo dataset automatically after PostgreSQL
and MongoDB become healthy. The web service waits for seeding to finish. On a
fresh database, the embedding model must be downloaded while the seed creates
profile embeddings; this may take several minutes. Wait for the seed to finish
before opening the app. Follow startup with:

```powershell
docker compose ps -a
docker compose logs -f seed
```

`seed` should end with exit code 0. Check the API and app at
http://localhost:8000/health and http://localhost:3000.

Compose starts these services:

| Service | Purpose | Host port |
|---|---|---:|
| `postgres` | Structured data, SQL functions/views/triggers, and pgvector | 5432 |
| `mongo` | Profile and project-context documents | 27017 |
| `api` | FastAPI backend | 8000 |
| `web` | Next.js frontend | 3000 |
| `seed` | One-shot demo-data initializer; exits after success | — |

If `seed` exits with a non-zero status, inspect `docker compose logs seed`.
The web service waits for successful seeding, so it may remain stopped until
the seed error is fixed.

The seeder creates 250 visible synthetic profiles with varied engineering,
design, research, data, and security experience, plus five sample projects and
20 open roles. These profiles are for matching demonstrations only and do not
have login credentials. Seeding is safe to rerun and preserves existing member
accounts and application data. To intentionally reset the application dataset,
pass `--reset`; this deletes existing accounts, projects, roles, applications,
and profiles:

```bash
docker compose exec api python -m app.bootstrap --reset
```

To rerun the non-destructive demo seed manually:

```bash
docker compose run --rm seed
```

Open:

- http://localhost:3000 — SkillSync web app
- http://localhost:8000/docs — API documentation
- http://localhost:8000/health — health check

Create an account from the web app. In **Explore roles**, choose **Post a role**
to announce a project opportunity: enter a project name and type, role title
and area, required skills, number of openings, and minimum experience. The new
role appears in discovery for other members to find teammates and apply.
New member profiles are private to teammate matching until the member opts in
from **My profile**. Passwords are Argon2-hashed; the web app stores short-lived
signed sessions in HttpOnly cookies and proxies authenticated API requests.

The CrossEncoder model is downloaded when the first teammate-match request is
made. Both models are cached in a named Docker volume for later starts.

To mirror demo embeddings into the experimental pgvector table:

```bash
docker compose exec api python scripts/seed_pgvector.py
```

The API and database images use named persistent volumes. The Next.js container
is a production build; source folders are not bind-mounted into runtime
containers. Change both `POSTGRES_PASSWORD` and the matching `DATABASE_URL` in
`.env` if you customize the local database password. Never use example
credentials or a development secret in a public deployment.

Stop the containers but keep database and model data:

```bash
docker compose down
```

**Destructive:** remove the containers and all named database/model-cache
volumes (this deletes PostgreSQL and MongoDB data):

```bash
docker compose down -v
```

### Existing database volumes

The SQL scripts in `sql/` are PostgreSQL image initialization scripts. They run
when the PostgreSQL data directory is first initialized, not on every restart.
If you change the schema after a volume already exists, apply a migration or
the needed SQL manually; rebuilding the image alone does not recreate that
database. Do not remove the volume unless you intentionally want to erase its
data.

## Database architecture

SkillSync uses PostgreSQL and MongoDB for different data responsibilities.
PostgreSQL is the source of truth for structured entities, relationships,
constraints, applications and capacity transactions. MongoDB stores flexible
profile documents and their embeddings. A `user_id` is copied into each Mongo
profile as an application-level link; there is no cross-database foreign key
or atomic transaction between the two databases.

### PostgreSQL tables and relationships

| Table | Purpose and relationships |
|---|---|
| `users` | Account identity (`full_name`, unique `email`, `password_hash`), visibility, weekly availability, experience, and creation time. |
| `projects` | Project owner (`owner_id` → `users.user_id`), name, type, status, and creation time. |
| `project_roles` | Parent project, title/type, total and filled slots, open/closed status, minimum experience, and creation time. |
| `skills` | Unique canonical skill name, category, and optional description. |
| `user_skills` | User-to-skill many-to-many junction, with proficiency (1–5) and years used. Composite primary key: `(user_id, skill_id)`. |
| `role_skills` | Role-to-skill many-to-many junction, with importance (1–5). Composite primary key: `(role_id, skill_id)`. |
| `applications` | User, role, status (`pending`, `accepted`, `rejected`, `withdrawn`), and applied time. A unique constraint prevents duplicate `(user_id, role_id)` records. |
| `milestones` | Project, title, due time, and completion state. |
| `profile_vectors` | Optional user-linked, 384-dimensional pgvector embedding and update time for vector-search experiments; not the main API's profile store. |
| `benchmark_events` | Range-partitioned event time, optional user/project IDs, event type, and JSONB payload for research workloads. |

Relationship sketch:

```text
users 1 ──< projects 1 ──< project_roles 1 ──< applications >── 1 users
  │                              │
  │                              └──< role_skills >── skills
  └──< user_skills >─────────────────────────────── skills
projects 1 ──< milestones
```

Primary keys identify rows; foreign keys protect references. `UNIQUE` and
`CHECK` constraints enforce rules such as unique email, valid role/application
statuses, bounded availability and proficiency, and valid slot counts. Some
foreign keys cascade deletes—for example, deleting a role removes its
role-skills and applications. The application-status and role-capacity logic
is defined in `sql/01_schema.sql`.

The design is normalized around entities: skill details live once in `skills`,
and the junction tables represent associations rather than repeating skill
columns or comma-separated skill lists in relational rows. The composite
primary keys on those junctions prevent duplicate associations. The
`benchmark_events` user/project IDs are not foreign keys; that table is
partitioned research data rather than part of the application relationship
graph.

### MongoDB collections and document shape

The configured MongoDB database is `skillsync`, with:

- `user_portfolios`: profile documents containing `user_id`, `bio`,
  `resume_text`, `projects`, `skills_text`, and an optional 384-number
  `embedding`. The API creates a unique index on `user_id`.
- `project_context`: collection configured for project context documents; it
  is not currently used by the main API workflow.

MongoDB is useful here because portfolio content is flexible and may vary in
shape. It stores source text and embeddings; structured skills and eligibility
attributes remain in PostgreSQL.

### Indexes, partitioning and vector extension

`sql/00_extensions.sql` enables pgvector (`vector`) and
`pg_stat_statements`. `sql/01_schema.sql` defines B-tree indexes for common
filters/joins, a partial index for open roles, a cosine HNSW index on
`profile_vectors`, and yearly range partitions for `benchmark_events`.
`sql/02_auth.sql` adds the partial index for visible users. Indexes improve
reads but consume storage and add write/update cost.

pgvector/HNSW is a research comparison path. The default matcher reads profile
vectors from MongoDB and computes cosine similarity in Python after SQL
eligibility filtering; it does not query the HNSW index.

### View types used and discussed

- **Regular view (virtual view):** stores a query definition and evaluates it
  when queried. `project_application_summary` joins projects, roles and
  applications and computes status counts. The Insights API reads this view,
  so it reflects current base-table data.
- **Materialized view:** stores query results as a snapshot and must be
  refreshed. `project_monthly_application_stats` summarizes applications by
  project and month. The seed refreshes it when it exists; application writes
  do not automatically refresh it.
- **Updatable view:** some simple regular views can accept writes that
  PostgreSQL translates to base-table writes. The project summary is an
  aggregate/join view and is for reading, not direct updates.
- **Temporary view:** a session-scoped view, removed when the session ends;
  none is defined by this project.
- **Recursive view/query:** uses recursive SQL for hierarchical data; none is
  defined by this project.

### Trigger vs function

A **trigger** is database logic automatically invoked by a configured table
event. Triggers are commonly distinguished by timing (`BEFORE`, `AFTER`, or
`INSTEAD OF`), event (`INSERT`, `UPDATE`, or `DELETE`), and scope (once per
affected row or once per SQL statement). `trg_close_full_role` is a row-level
`BEFORE INSERT OR UPDATE OF
slots_filled, slots_total` trigger on `project_roles`. Its function,
`close_full_role()`, changes `NEW.status` to `closed` when the role is full.
It only closes full roles; it does not increment slots or automatically reopen
a closed role.

MongoDB has no trigger defined in this project. The project’s automatic
role-closing behavior is a PostgreSQL trigger; MongoDB profile writes are made
explicitly by the API/seeder.

`apply_to_role(user_id, role_id)` is a separate PostgreSQL function called by
the API, not a trigger. It locks the role row using `FOR UPDATE`, checks
availability and duplicate active applications, inserts/reactivates the
application, then increments `slots_filled`. PostgreSQL executes those steps
in the caller's transaction. The row lock prevents concurrent requests from
consuming the same final slot.

## Database CLI demonstration (PostgreSQL and MongoDB)

The commands below use the interactive clients installed **inside the database
containers**. No separate Windows installation of `psql` or `mongosh` is
required. First start the stack as described above.

### Connect to PostgreSQL interactively

In PowerShell, from the project directory:

```powershell
docker compose exec postgres psql -U skillsync -d skillsync
```

You are now at the `psql` prompt. These commands are entered **inside psql**:

```text
\conninfo
\pset pager off
\dt
\d+ users
\d+ projects
\d+ project_roles
\d+ applications
\dv+
\dm+
\df close_full_role
\df apply_to_role
```

`\dt` lists tables, `\d+ table_name` describes a table and its constraints,
`\dv+` lists views, `\dm+` lists materialized views, and `\df` lists functions.
Run SQL statements ending in semicolons. Exit with `\q`.

### Inspect actual relational records and joins

Run these at the `psql` prompt:

```sql
SELECT user_id, full_name, email, availability_hours, experience_years
FROM users ORDER BY user_id LIMIT 5;

SELECT project_id, owner_id, name, project_type, status
FROM projects ORDER BY project_id;

SELECT role_id, project_id, title, role_type,
       slots_filled, slots_total, status
FROM project_roles ORDER BY role_id;

SELECT r.title AS role, p.name AS project,
       s.canonical_name AS required_skill, rs.importance
FROM project_roles r
JOIN projects p ON p.project_id = r.project_id
JOIN role_skills rs ON rs.role_id = r.role_id
JOIN skills s ON s.skill_id = rs.skill_id
ORDER BY r.role_id, rs.importance DESC;
```

Show actual user-to-skill assignments:

```sql
SELECT u.full_name, s.canonical_name, us.proficiency, us.years_used
FROM user_skills us
JOIN users u ON u.user_id = us.user_id
JOIN skills s ON s.skill_id = us.skill_id
ORDER BY u.user_id, s.canonical_name
LIMIT 20;
```

To show the foreign-key relationships PostgreSQL has registered:

```sql
SELECT tc.table_name, kcu.column_name,
       ccu.table_name AS references_table,
       ccu.column_name AS references_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;
```

### Show the live view

At `psql`:

```sql
SELECT project_id, name, total_applications, accepted, pending, rejected
FROM project_application_summary
ORDER BY total_applications DESC, project_id;

SELECT pg_get_viewdef('project_application_summary'::regclass, true);
```

To show a working view in the web interface, submit an application through the
app and refresh **Insights**. The regular view reflects the new base-table data
when queried.

### Show the trigger safely (rollback the test)

First inspect the trigger and its function:

```sql
SELECT tgname, pg_get_triggerdef(oid)
FROM pg_trigger
WHERE tgrelid = 'public.project_roles'::regclass
  AND NOT tgisinternal;

SELECT pg_get_functiondef('close_full_role()'::regprocedure);
```

Now demonstrate it in a transaction. The update fills one currently open role;
the trigger changes the status to `closed`. The final `ROLLBACK` ensures the
demo does not alter saved data:

```sql
BEGIN;

UPDATE project_roles
SET slots_filled = slots_total
WHERE role_id = (
    SELECT role_id
    FROM project_roles
    WHERE status = 'open' AND slots_filled < slots_total
    ORDER BY role_id
    LIMIT 1
)
RETURNING role_id, title, slots_filled, slots_total, status;

ROLLBACK;
```

Explain that `NEW` is the row being inserted/updated, and the `BEFORE` trigger
edits it before PostgreSQL saves it. `RETURNING` displays the trigger-modified
row. The trigger does not increment capacity; the application function does.

### Show the application function and concurrency protection

Inspect the function:

```sql
SELECT pg_get_functiondef('apply_to_role(bigint,bigint)'::regprocedure);
```

The most realistic demo is to apply to a role from the UI, then inspect the
rows in `applications` and `project_roles`:

```sql
SELECT a.application_id, u.email, r.title, a.status, a.applied_at
FROM applications a
JOIN users u ON u.user_id = a.user_id
JOIN project_roles r ON r.role_id = a.role_id
ORDER BY a.applied_at DESC
LIMIT 10;

SELECT role_id, title, slots_filled, slots_total, status
FROM project_roles ORDER BY role_id;
```

The API calls `apply_to_role()` inside a PostgreSQL transaction. To demonstrate
concurrent attempts with the included script, run this from PowerShell:

```powershell
docker compose exec api python scripts/concurrency_demo.py
```

By default, the script tests role ID 1 with user IDs 100–105. For a controlled
presentation, choose a role with one slot remaining and suitable test user
IDs. You can override the role ID for that container command, for example:

```powershell
docker compose exec -e ROLE_ID=12 api python scripts/concurrency_demo.py
```

The script's user IDs are fixed in the script and may already have applications,
so use the seeded demo database and inspect the output. The safety property is that
the function's `FOR UPDATE` lock prevents successful applications from
exceeding capacity. Do not use a production database for this experiment.

### Show MongoDB interactively

Open a second PowerShell terminal:

```powershell
docker compose exec mongo mongosh skillsync
```

At the `mongosh` prompt:

```javascript
db.getName()
show collections
db.user_portfolios.countDocuments({})
db.project_context.countDocuments({})
db.user_portfolios.getIndexes()
```

Inspect a profile without dumping its large embedding vector:

```javascript
db.user_portfolios.findOne(
  {},
  { _id: 0, embedding: 0 }
)
```

Show a document's embedding dimension:

```javascript
const profile = db.user_portfolios.findOne(
  { embedding: { $exists: true } },
  { user_id: 1, embedding: 1 }
);
printjson({ user_id: profile.user_id, dimensions: profile.embedding.length });
```

Join the concept across databases manually: get a `user_id` from PostgreSQL,
then query MongoDB with the same numeric value:

```javascript
db.user_portfolios.findOne(
  { user_id: 1 },
  { _id: 0, embedding: 0 }
)
```

Replace `1` with an ID returned from the PostgreSQL `users` query. The matching
IDs are an application-level relationship, not a MongoDB foreign key. Exit
`mongosh` with `exit`.

### Materialized view and existing volumes

Check whether the optional monthly materialized view exists:

```sql
SELECT to_regclass('public.project_monthly_application_stats');
```

If it returns the view name, it can be refreshed and queried:

```sql
REFRESH MATERIALIZED VIEW project_monthly_application_stats;

SELECT *
FROM project_monthly_application_stats
ORDER BY month_start DESC;
```

If it returns `NULL`, the current PostgreSQL volume was initialized without
that view. The initialization SQL is not automatically reapplied to an
existing Docker volume; apply a migration or create the view explicitly rather
than deleting data just to rerun initialization.

## 5. Demo workflow

### Demo 1 — semantic matching

1. Start the stack and create an account.
2. Add skills, experience, availability and a short introduction to your profile.
3. Choose whether your profile can be considered for teammate matching.
4. Open **Explore roles** and search by project, role, or area of work. This is
   ordinary PostgreSQL text search, not semantic model search.
5. Click **Find teammates** to run semantic matching on eligible,
   profile-visible candidates.
6. Explain the combined ranking features. The UI shows the final match score
   and candidate attributes; the `/match` API response also includes component
   scores such as the reranker, skill overlap, experience and availability.

Then explain the key idea:

```text
"component-based JavaScript interfaces with TypeScript"
             ≈ semantic meaning ≈
"React / Next.js / TypeScript frontend experience"
```

This is the failure mode of exact keyword matching that motivated the supplied problem statement.

### Demo 2 — compare reranking modes

The frontend currently sends `rerank: true` for teammate matches. To compare
with CrossEncoder reranking disabled, call the authenticated `/match` API with
`"rerank": false` and compare the returned ranking and latency. This still uses
BGE cosine similarity plus the skill, experience and availability features;
it only skips CrossEncoder scoring. In this mode, the implementation uses the
BGE cosine score in the scoring slot otherwise filled by the CrossEncoder
score.

This gives a direct ablation:

```text
BGE similarity + structured features
vs
BGE + CrossEncoder
```

Record ranking changes and latency.

### Demo 3 — transaction/concurrency

Choose a role with two slots. Fill one slot first, then run:

```bash
docker compose exec api python scripts/concurrency_demo.py
```

Multiple sessions attempt to consume the remaining capacity. The database function locks the role row with `FOR UPDATE`, so the final slot cannot be consumed twice.

### Demo 4 — DBMS tuning

Generate scale data first:

```bash
docker compose exec api python benchmarks/generate_scale.py --users 100000 --events 500000
```

Then:

```bash
docker compose exec api python benchmarks/run_sql_benchmark.py
```

Compare:

```text
results/before_tuning.csv
results/after_tuning.csv
results/latency_before_after.csv
```

Use `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` to discuss execution time, planner estimates and buffer activity.

### Demo 5 — vector indexing

```bash
docker compose exec api python scripts/seed_pgvector.py
docker compose exec api python benchmarks/vector_benchmark.py
```

The script compares exact cosine search in NumPy with PostgreSQL pgvector HNSW and reports Recall@10.

### Demo 6 — workload shift

```bash
docker compose exec api python benchmarks/workload_shift.py
```

Discuss why a system optimized for one query mix may behave differently after the workload changes.

## 6. Research experiments

### E1: lexical vs dense vs reranked

Build a labeled evaluation set of at least 50 pairs. Include exact matches, paraphrases, synonyms, irrelevant profiles and ambiguous profiles.

Report:

- Precision@5
- Recall@10
- MRR
- nDCG@10
- retrieval latency
- reranking latency

### E2: exact vs HNSW

Use exact nearest-neighbor results as the reference. Vary:

```text
ef_search = 16, 32, 64, 128
```

Measure:

```text
Recall@10
median latency
p95 latency
```

### E3: SQL tuning

Run the same query set:

1. baseline
2. composite/partial indexes
3. extended statistics
4. materialized view

Capture:

```text
execution time
planning time
estimated rows
actual rows
shared hit blocks
shared read blocks
```

### E4: workload shift

W1:

```text
80% profile search
20% analytics
```

W2:

```text
30% profile search
70% analytics
```

Report how latency changes and which indexes/views become more or less useful.

### E5: storage comparison

For a separate stretch experiment, implement the same profile object in:

1. normalized PostgreSQL
2. PostgreSQL JSONB
3. MongoDB

Run identical operations:

- point lookup
- nested-field filter
- update
- full-document read
- vector retrieval where supported

## 7. Database features to point out in the viva

| Feature | Where | Why it matters |
|---|---|---|
| PK/FK | PostgreSQL | integrity |
| UNIQUE/CHECK | PostgreSQL | domain constraints |
| M:N tables | user_skills / role_skills | normalization |
| transaction | apply_to_role | atomic capacity update |
| `FOR UPDATE` | apply_to_role | race prevention |
| trigger | project_roles | automatic role closure |
| view | project_application_summary | reusable relational query |
| materialized view | monthly stats | precomputed analytics |
| B-tree/partial index | filters/joins | access path |
| extended statistics | users | planner estimation |
| partitioning | benchmark_events | scale/time locality |
| pg_stat_statements | PostgreSQL | query workload telemetry |
| pgvector HNSW | profile_vectors | ANN experiment |
| MongoDB | profiles/context | heterogeneous documents |

## 8. Why this is a research-grade DBMS project

A normal DBMS mini-project stops at CRUD + a UI. This one produces empirical evidence about:

```text
data model
   ↓
query design
   ↓
semantic retrieval
   ↓
vector index
   ↓
transaction correctness
   ↓
planner behavior
   ↓
index/statistics tuning
   ↓
workload shift
   ↓
measured trade-offs
```

The project does **not** claim that BGE, HNSW or CrossEncoders are novel algorithms. The research value is the controlled, reproducible system-level study and the comparison of alternatives.

## 9. Final report structure

1. Abstract
2. Introduction
3. Problem statement
4. Research questions and hypotheses
5. Related technologies
6. Requirements
7. ER model
8. Functional dependencies and normalization
9. PostgreSQL schema
10. MongoDB document model
11. Hybrid matching architecture
12. Embedding model and reranker
13. Concurrency design
14. Query workload
15. Experimental methodology
16. Matching-quality results
17. DBMS performance results
18. Vector exact-vs-HNSW results
19. Workload-shift results
20. Storage comparison
21. Threats to validity
22. Limitations
23. Conclusion
24. References

## 10. Key research questions for the viva

**Q: Why not SQL only?**
Structured records require integrity and transactions. Portfolio/resume data is heterogeneous. The project experimentally tests the polyglot choice rather than assuming it.

**Q: Why not Mongo only?**
The application has relational integrity and concurrency requirements. PostgreSQL gives a natural relational representation and rich query-planning/tuning facilities.

**Q: Why embeddings?**
Literal keyword matching misses semantic equivalents and paraphrases.

**Q: Why two stages?**
PostgreSQL first applies eligibility filters and caps the candidate pool. BGE
supplies semantic similarity within that pool, then the more expensive
CrossEncoder reranks the candidate/profile pairs. The current API does not use
HNSW to retrieve this pool.

**Q: Why HNSW?**
Exact search scans all vectors. HNSW uses an approximate graph index to trade recall for speed/memory/build cost.

**Q: Why extended statistics?**
Single-column statistics can be insufficient when predicates are correlated. Multivariate statistics provide the planner additional information.

**Q: Why synthetic data?**
Real student profiles are unavailable and would raise privacy issues. Synthetic data enables controlled scale experiments, but the report must clearly state that limitation.

**Q: What is novel?**
Do not say the embedding model or HNSW is novel. The contribution is the integrated, reproducible DBMS experiment and the analysis of how retrieval, storage and database tuning interact under changing workloads.
