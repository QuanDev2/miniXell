# miniXell Implementation Plan

Learn by building. Each phase produces something that runs; concepts are
explained when the phase needs them.

Each phase lists:

- **Build**: what exists at the end.
- **Learn along the way**: concepts the phase teaches.
- **Done when**: observable check.
- **Interview line**: what the phase lets you say with evidence.

## MVP goal

Four things to show:

1. Parity test passing, plus a bug it caught.
2. E-distance three ways in Spark (plain Python, pandas batches, Scala), each
   parity-checked.
3. Live API call: a perturbation's similar perturbations and Claude's
   explanation.
4. Live agent question: an open question answered with the trail of lookups
   behind it.

## Repo layout

```
miniXell/
├── README.md
├── docs/                    # architecture, plan, notes/
├── data/                    # downloaded + converted datasets (git-ignored)
├── pipeline/
│   ├── convert.py           # h5ad → Parquet
│   ├── legacy_signatures.py # single-machine reference
│   ├── spark_signatures.py  # PySpark job
│   └── load_mongo.py        # results → MongoDB
├── scala/edistance/         # sbt project → jar loaded by PySpark
├── api/                     # FastAPI app; static/ = demo page (phase 6); agent/ = research assistant (phase 7)
├── tests/                   # unit, parity, API; fixtures/ = tiny dataset
├── docker-compose.yml       # local MongoDB
├── pyproject.toml
└── .github/workflows/ci.yml
```

## Datasets

From scPerturb (Zenodo record 13350497).

| Use | File | Size |
|---|---|---|
| Development and parity | `NormanWeissman2019_filtered.h5ad` | 666 MB |

---

## Phase 0: Toolchain and skeleton (0.5 day)

**Build**
- Python 3.12 via `uv`, Java 17 (Spark needs it), Docker Desktop, sbt.
- Repo layout, `.gitignore`, `pyproject.toml`.
- `docker-compose.yml` running MongoDB.

**Learn along the way**
- Python packaging and virtual environments vs .NET projects and NuGet.
- Docker and docker-compose.
- Why Spark needs Java.

**Done when**: `docker compose up` starts MongoDB; `uv run python -c "import pyspark"` works; `sbt --version` works.

**Interview line**: "Local environment matches production through containers."

## Phase 1: Data → Parquet (0.5 day)

**Build**
- `pipeline/convert.py`: download the Norman h5ad; scale counts (per 10,000,
  then log); keep the 2,000 most variable genes; compute 50 principal
  components per cell; write `cells.parquet`, `expression.parquet` (non-zero
  values only), `cell_pcs.parquet`.

**Learn along the way**
- h5ad structure; sparse data (store only non-zeros).
- Parquet: columns, compression, row groups; inspect a file with `pyarrow`.
- Wide vs long tables.

**Done when**: three Parquet files exist; cell, gene, and perturbation counts printed and sane.

**Interview line**: "Converted a scientific format into a Spark-ready columnar layout, like your Parquet work on Tahoe-100M."

## Phase 2: Legacy reference (0.5 day)

**Build**
- `pipeline/legacy_signatures.py` (pandas, all in memory):
  signatures → top 50 genes per perturbation → Euclidean distance between
  signatures → E-distance on sampled cells' principal components → top 20
  matches per metric.
- Deterministic cell sampling rule (up to 100 cells per perturbation, chosen
  by a fixed hash of cell_id), documented for reuse by Spark.
- Saved output = the answer key.

**Learn along the way**
- pandas group-by vs LINQ `GroupBy`.
- Log fold change; Euclidean distance; E-distance.

**Done when**: answer key written; spot check: each single-gene perturbation's own target gene moves strongly in its signature.

**Interview line**: "Built the single-machine baseline first and froze its outputs as the reference."

## Phase 3: PySpark job + parity (1 day)

**Build**
- `pipeline/spark_signatures.py` in local mode: read Parquet → join cells to
  expression → (sum, count) per perturbation and gene → broadcast control
  averages → signatures → top 50 genes (window function) → Euclidean distance
  → top 20 matches.
- `tests/test_parity.py`: values within tolerance, identical top-10 gene
  rankings, identical neighbor rankings, matching counts.
- Tiny fixture dataset in `tests/fixtures/`.
- Use Claude as a coding assistant for the pandas → PySpark translation; log
  what it got wrong and what parity caught in `docs/notes/`.

**Learn along the way**
- Driver, workers, tasks; lazy evaluation.
- Shuffles and why they're expensive; broadcast joins; window functions.
- Spark UI: stages, tasks, shuffle sizes, spill.
- Floating-point summation order and why parity needs a tolerance.

**Done when**: parity passes on the fixture and the full Norman dataset; one deliberately introduced bug (e.g. averaging averages) is caught by parity.

**Interview line**: "Migrated the analysis to PySpark and proved equivalence with an automated parity test."

## Phase 4: E-distance three ways (1 day)

Benchmarks dropped (user's call): no benchmark scripts, charts, or Replogle
dataset. The job log's stage times are the only timings.

**Build**
- Spark sampling with the legacy MD5 rule: `sampled_cells`,
  `sampled_cell_count`.
- E-distance in Spark three ways: plain Python `udf`, pandas in batches,
  Scala function from `scala/edistance/` (sbt → jar, loaded by PySpark);
  writes `edistance`, `similar_edistance`.
- All three parity-checked against the legacy answer key; parity tests extended.

**Learn along the way**
- Why data crossing between the Java runtime and Python costs time; batch
  (Arrow) vs row-by-row transfer.
- Scala basics: syntax, types, sbt, jars.

**Done when**: all three implementations pass parity on the fixture and Norman; Spark output covers every MongoDB document field.

**Interview line**: "Ported the heaviest calculation three ways, from Python to Scala, and proved each matches the reference."

## Phase 5: MongoDB + FastAPI + CI (1 day)

**Build**
- `pipeline/load_mongo.py`: one document per perturbation (see ARCHITECTURE.md);
  index on name; index for gene lookups.
- `api/`: FastAPI endpoints from ARCHITECTURE.md; MongoDB queries in
  `api/repository.py` (reused by phase 7 tools); async MongoDB driver;
  Pydantic response models; tests against a test database.
- `.github/workflows/ci.yml`: lint, unit tests, API tests, parity on fixture.

**Learn along the way**
- Document modeling: embed vs reference; indexes and `explain()`.
- MongoDB aggregation pipeline vs LINQ.
- FastAPI vs ASP.NET Core: routing, dependency injection, async; Pydantic vs DTOs.
- GitHub Actions basics.

**Done when**: `/docs` page lists all endpoints; queries use indexes per `explain()`; CI green on GitHub.

**Interview line**: "Python backend with typed contracts, tested in CI, with parity as a merge gate."

## Phase 6: Claude explain endpoint + demo page (1–1.5 days)

**Build**
- Fetch public gene descriptions (NCBI Gene via mygene.info) for signature
  genes; store in MongoDB.
- `POST /perturbations/{name}/explain`: signature + descriptions → Claude →
  explanation.
- Guardrail: reject explanations naming genes absent from the signature or
  descriptions.
- Decide access: Anthropic API key (simplest locally) or Amazon Bedrock
  (needs AWS account; matches post-MVP).
- Demo page `api/static/index.html`: one static HTML page served by FastAPI,
  plain JavaScript, no build step. Search box → perturbation's top genes and
  similar list → Explain button shows Claude's text, or the guardrail's
  rejection.

**Learn along the way**
- Calling an LLM API; prompt design; token cost and latency.
- Grounding (retrieval-augmented generation): fetch facts first, let the model
  explain only those.
- Serving a static page from FastAPI; calling the API from the browser with
  `fetch`.

**Done when**: explanations return for several perturbations, from the demo page; guardrail test rejects a planted made-up gene.

**Interview line**: "AI explains computed results and is blocked from inventing them, matching protoXell's rule."

## Phase 7: Research assistant agent (1–1.5 days)

Needs phase 5 (query layer) and phase 6 (`genes` collection, Claude access,
guardrail). Design: ARCHITECTURE.md, "Research assistant agent".

**Build**
- `POST /ask`: Claude answers open questions by calling five read-only tools
  over MongoDB; returns the answer plus every lookup it made.
- Hand-written tool loop in `api/agent/` with limits (8 tool calls, 30 s,
  token cap); ledger + guardrail shared with phase 6; each run saved to
  `agent_runs`.
- Demo page gets an Ask box: answer plus its step list.
- Tests: tools against the test database, loop against a scripted fake model,
  guardrail with a planted made-up gene and a wrong number.
- `/ask` sits alongside the phase 6 explain endpoint; both stay.

**Learn along the way**
- Tool use: how a model requests an action and code carries it out.
- Agent loops: limits, stopping, running several tool requests at once with
  asyncio.
- Grounding for agents: checking answers against what the tools returned; run
  records for reproducibility.

**Done when**: `/ask` answers several open questions with step lists, from the
demo page; guardrail rejects a planted made-up gene and a wrong number; run
records saved.

**Interview line**: "The agent picks what to look up; code computes and verifies; every answer carries its trail."

---

## After the MVP

| Phase | Build |
|---|---|
| 8 | AWS: S3 zones, Spark job + Scala jar on EMR Serverless, MongoDB Atlas, API on ECS Fargate via ECR, secrets in Secrets Manager, billing alarm |
| 9 | CD: GitHub Actions deploys to AWS on merge, OIDC credentials |
| 10 | Insight service: explain and agent move behind SQS into their own ECS service; dead-letter queue |

Stretch, unordered: tiny Node.js legacy API migrated to FastAPI with an API
parity test; AI migration agent (Claude translates legacy code, parity
judges); run records (dataset, code version, model, prompt) per result;
pathway-level analysis.

## If time runs short

Cut in this order: phase 7 (agent; depends on phase 6) → phase 6 (explain
becomes a whiteboard answer) → Scala implementation (keep plain Python vs
pandas batches). Phases 0–3 are the minimum credible demo.

## Alongside every phase

- 60–90 minutes of LeetCode in Python daily: hash maps, two pointers, sliding
  window, binary search, BFS/DFS, heaps, intervals.
- Short notes per phase in `docs/notes/`, in your own words.
