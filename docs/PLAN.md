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
2. E-distance two ways in Spark (plain Python, pandas batches), each
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

## Phase 4: E-distance two ways (done)

Benchmarks dropped (user's call): no benchmark scripts, charts, or Replogle
dataset. The job log's stage times are the only timings. Scala way deferred
(user's call: go with PySpark).

**Build**
- Spark sampling with the legacy MD5 rule: `sampled_cells`,
  `sampled_cell_count`.
- E-distance in Spark two ways: plain Python `udf` and pandas in batches,
  chosen by `--edistance`; writes `edistance`, `similar_edistance`.
- Both parity-checked against the legacy answer key; parity tests extended.

**Learn along the way**
- Why data crossing between the Java runtime and Python costs time; batch
  (Arrow) vs row-by-row transfer.

**Done when**: both implementations pass parity on the fixture and Norman; Spark output covers every MongoDB document field.

**Interview line**: "Ported the heaviest calculation to PySpark two ways, row-by-row and batched, and proved both match the reference."

## Phase 5: MongoDB + FastAPI + CI (done)

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

## Step 5.4 contract: API integration tests

**Revision:** 2.
**Status:** APPROVED; execution pending separate explicit authorization.
**User approval:** "save it", in response to "Mark contract APPROVED,
execution still pending?" This approves the contract, not implementation.
Saving this contract does not dispatch the implementer.

**Goal**

Add automated tests against the real API and a throwaway MongoDB database
filled from the tiny test dataset. Check every existing endpoint on each run,
so CI in step 5.5 can block broken changes.

**Design**

- Exercise the real application lifespan, routes, repository, and MongoDB.
  A test client sends requests in-process; no repository or database mocks.
- Reuse the tiny fixture's Spark outputs and the existing loader.
  Compare responses against source Parquet, not loader-produced documents.
  Numeric tolerance: `1e-9`.
- Preserve existing application behavior and parity coverage. Settled schema
  and endpoint design remain in [ARCHITECTURE.md](ARCHITECTURE.md).

**Scope and safety**

- Generate a unique disposable database per test session and configure the
  application before startup. Cleanup only that generated database, including
  setup or test failures. Never invoke the loader CLI targeting the main
  `minixell` database.
- Missing MongoDB or Java must produce a clear setup failure, not skipped API
  checks. Existing optional Norman parity skips remain unchanged.
- Include another dataset's distinguishable records in the disposable
  database; queries must remain dataset-scoped.

**Allowed changes**

| Where | File | Change | Why |
|---|---|---|---|
| Tests | tests/test_api.py | **New:** endpoint integration tests. | Verify serving behavior. |
| Tests | tests/conftest.py, tests/test_parity.py | Share tiny fixture setup without removing parity checks. | Avoid duplicate pipeline runs. |
| Dependencies | pyproject.toml, uv.lock | Add dev dependency `httpx`. | Support test client. |
| Documentation | docs/PLAN.md, docs/PROGRESS.md | Keep contract in plan; execution evidence and contract link in progress. | Keep handoff responsibilities separate. |

**Acceptance criteria**

Verify actual values and ordering, not merely successful status codes.
The tiny fixture has six perturbations and five neighbors each.

| Endpoint | Acceptance |
|---|---|
| `/health` | Connected database returns 200 with `{"status":"ok"}`; unreachable database returns 503 without stopping shared MongoDB. |
| `/perturbations/{name}` | Correct metadata, ranked genes, and both neighbor lists; no `_id`. Cover single-target and combination records. Unknown name returns 404. |
| `/perturbations` | Exact fixture records, sorted by name; a smaller limit returns the correct prefix. Unfiltered `gene_change` is null. |
| `/perturbations?gene=…` | Exact matching records and correct changes. Unknown or wrong-case symbol returns an empty list. |
| Limit validation | 1 and 236 are accepted; zero, negative, above 236, and non-integer values return 422. |
| `/perturbations/{name}/similar` | Correct neighbors, distances, and ordering for both metrics; default selects E-distance; no self-match. Unknown name returns 404; invalid metric returns 422. |

Both consecutive API test runs must pass without stale records or database-name
collisions. The demo database must remain untouched.

**Verification**

With existing MongoDB available:

```bash
uv run --env-file .env pytest tests/test_api.py -v
uv run --env-file .env pytest tests/test_api.py -v
uv run --env-file .env pytest -v
```

Expected: both API runs pass and the full suite has no regressions. Record
actual counts and existing optional Norman skips.

Separate live smoke: prepare a temporary database from the tiny fixture's
Spark outputs, launch Uvicorn against it, and send real HTTP requests covering
health, list/filter, detail, both similarity metrics, and error responses.
Record exact commands and results. Stop the server, close clients, drop only
the disposable database, and remove the temporary harness.

**Exclusions**

No application or pipeline changes, CI workflow, service startup or install,
commits, pushes, or adjacent cleanup. Uvicorn startup for the specified live
smoke is in scope once execution is authorized; starting shared MongoDB is not.
If an application bug blocks acceptance, report evidence and request a scope
amendment rather than changing application code under this contract.

**Handoff and completion**

After explicit execution approval, the implementer records IN PROGRESS in
[PROGRESS.md](PROGRESS.md) and owns that execution log until READY FOR REVIEW.
Record work completed, commands, actual results, cleanup evidence, commit hash
or "uncommitted", blockers, next step, and a link to this contract there.
Finish READY FOR REVIEW; user acceptance closes the step. Do not start step 5.5.

**Unresolved questions:** None.

## Step 5.5 contract: GitHub CI

**Revision:** 1.
**Status:** APPROVED; local implementation and gated publication authorized.
**User authorization:** "approve", then "ok dispatch it" (Lead-supervised
dispatch): local implementation, the Ruff dev dependency, and the local checks
below.
**Publication authorization:** user selected "Create public repo and push":
"Publish QuanDev2/miniXell and its tracked history publicly; after my review,
commit step 5.5 changes and push for CI verification." Gate: Lead reviews the
local changes and evidence first. Then create public `QuanDev2/miniXell`, set
`origin`, commit only step 5.5 changes, push without force, observe the hosted
run. No other publishing or cleanup.

**Goal**

Push or pull request → clean GitHub runner → lint, API integration tests, and
legacy-versus-Spark parity checks. Catches broken changes off the laptop,
without a local `.env`, downloaded Norman data, or existing database contents.
CI only, no deployment.

**Workflow behavior**

- `.github/workflows/ci.yml`, triggered on `push` and `pull_request`, no
  branch or path filters. One `ubuntu-24.04` job, `contents: read`.
- Python 3.12 from `.python-version`, Java 17, uv; install from the committed
  lockfile with `uv sync --locked`.
- Temporary `mongo:8` service with a readiness check.
  `MONGODB_URI=mongodb://127.0.0.1:27017`, `SPARK_LOCAL_IP=127.0.0.1`;
  `JAVA_HOME` comes from the Java setup action. No laptop `.env`, no database
  or cloud secrets.
- Ruff as a dev dependency, rules limited to correctness: `E9`, `F63`, `F7`,
  `F82`. No formatter, no style sweep.
- Run `uv run --no-sync ruff check .`, then one
  `uv run --no-sync pytest -v -ra`, so API and parity tests share the tiny
  fixture's pipeline run. Both E-distance ways (plain Python and pandas)
  stay covered. No new unit-test suite.
- Any install, lint, or test failure fails the job. No suppressed errors,
  `continue-on-error`, weakened assertions, or skips for missing Java/MongoDB.

**Allowed changes**

| Where | File | Change | Why |
|---|---|---|---|
| CI | .github/workflows/ci.yml | **New:** environment, MongoDB service, lint, tests. | Run checks on GitHub. |
| Dependencies | pyproject.toml, uv.lock | Add dev dependency `ruff`; narrow rule configuration. | Correctness lint. |
| Documentation | docs/PLAN.md, docs/PROGRESS.md | Contract here; execution log and hosted evidence in progress. | Keep handoff responsibilities separate. |

No application, pipeline math, existing test assertion, tolerance, or
sampling changes. A blocking code defect needs evidence and a scope amendment,
not blanket ignores.

**Acceptance criteria**

- A clean checkout installs from the lockfile and succeeds on GitHub without a
  Norman download or local setup files.
- Every API test and tiny-fixture parity test runs and passes, both E-distance
  ways included. Optional full-Norman tests may skip (outputs absent);
  report the skips.
- Tests use the existing unique disposable databases; no demo data touched.
  The hosted MongoDB service is temporary.
- A hosted run is observed succeeding through install, MongoDB readiness,
  lint, and tests; record results, tested commit, and run URL. Local success
  alone doesn't complete the step.
- Failed CI reports failure; blocking merges needs repository policy, outside
  this step.

**Verification**

Local, with existing Java and MongoDB:

```bash
uv sync --locked
uv run --no-sync ruff check .
uv run --no-sync --env-file .env pytest -v -ra
```

Expected: lint passes; existing suite has no regressions. Then, only after
separate authorization: connect the repository, push, observe the hosted run,
and fix workflow/environment issues within scope. No hosted run → verification
blocked, not complete.

**Exclusions**

Deployment, cloud infrastructure, secrets, releases, branch protection,
unrelated dependency upgrades or cleanup, and starting or changing shared
local services.

**Handoff and completion**

The implementer records IN PROGRESS in [PROGRESS.md](PROGRESS.md) and owns the
execution log until READY FOR REVIEW: work, exact commands and results, hosted
URL and tested commit, blockers, commit hash or "uncommitted", and a link to
this contract. READY FOR REVIEW only after hosted proof; user acceptance closes
the step. Do not start Phase 6.

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
| 8 | AWS: S3 zones, Spark job on EMR Serverless, MongoDB Atlas, API on ECS Fargate via ECR, secrets in Secrets Manager, billing alarm |
| 9 | CD: GitHub Actions deploys to AWS on merge, OIDC credentials |
| 10 | Insight service: explain and agent move behind SQS into their own ECS service; dead-letter queue |

Stretch, unordered: tiny Node.js legacy API migrated to FastAPI with an API
parity test; AI migration agent (Claude translates legacy code, parity
judges); run records (dataset, code version, model, prompt) per result;
pathway-level analysis.

## If time runs short

Cut in this order: phase 7 (agent; depends on phase 6) → phase 6 (explain
becomes a whiteboard answer). Phases 0–3 are the minimum credible demo.

## Alongside every phase

- 60–90 minutes of LeetCode in Python daily: hash maps, two pointers, sliding
  window, binary search, BFS/DFS, heaps, intervals.
- Short notes per phase in `docs/notes/`, in your own words.
