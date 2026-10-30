# miniXell Progress

Handoff log: where the build stands, what's done, what's next. Updated after
every step. Phases are defined in [PLAN.md](PLAN.md); steps within a phase are
defined here.

Last updated: 2026-10-29.

## Current position

- **Done:** Phase 0, Phase 1, Phase 2, Phase 3 (step 3.7 skipped by user),
  Phase 4 (benchmarks dropped, Scala way 4.4 skipped for now by user),
  Phase 5 (step 5.5 accepted by user 2026-10-29: "commit").
  Remote: public `QuanDev2/miniXell` (`origin`); CI runs on every push.
  Last commit: `effbef4` (CI MongoDB pin).
- **In progress:** Phase 6 (Claude explain endpoint + demo page). Steps
  6.1–6.3 done, uncommitted (`pyproject.toml`, `uv.lock`,
  `pipeline/fetch_genes.py`, `api/`, `docs/ARCHITECTURE.md`, this file). User
  deleted `.env.example` after pasting the key into it; template not recreated.
- **Next:** user review of 6.1–6.3, then brief 6.4.

## Phase 0: Toolchain and skeleton (done)

Chat called these steps "3.1–3.5"; same steps.

| Step | What | Status | Commit |
|---|---|---|---|
| 0.1 | Install uv, sbt, Java 17; scope Java to project via `.env` | Done | `7a1960a` (AGENTS.md, `.gitignore`) |
| 0.2 | uv project with PySpark, folders, `.gitignore` | Done | `0fb1938` |
| 0.3 | MongoDB in Docker | Done | `52c6488` |
| 0.4 | Smoke test: Spark sum 1..1000 = 500500; `sbt --version` | Done | no files |
| 0.5 | Commit check | Done | nothing to commit |

## Phase 1: Data → Parquet (done)

| Step | What | Status | Commit |
|---|---|---|---|
| 1.1 | Add anndata, scanpy, pyarrow | Done | `482e3fb` |
| 1.2 | `pipeline/download.py`; download Norman h5ad (699 MB, MD5 verified) | Done | `482e3fb` |
| 1.3 | Inspect the file: cells, genes, `obs` columns, perturbation label column, control label, combination label format, whether `X` holds raw counts | Done | `62d333e` |
| 1.4 | Write and run `pipeline/convert.py` → `cells.parquet`, `expression.parquet`, `cell_pcs.parquet` in `data/processed/norman/` | Done | `95e0ce1` |
| 1.5 | Inspect Parquet output; target-gene check failed → fixed (2,000 variable + targeted genes; 102/105 targets) | Done | `cbc9338` |

## Phase 2: Legacy reference (done)

Run: `uv run python -m pipeline.legacy_signatures norman`.
Output: `data/processed/norman/legacy/`.

| Step | What | Status | Commit |
|---|---|---|---|
| 2.1 | Gene averages → signatures → top 50 genes → target check; writes `perturbations` (236 rows), `signatures` (487,576), `top_genes` (11,800) | Done | `43fd331` |
| 2.2 | Euclidean distance between all perturbation pairs → 20 closest each; writes `euclidean` (27,730 rows), `similar_euclidean` (4,720) | Done | `49b440a` |
| 2.3 | MD5 sampling rule (≤100 cells per perturbation), recipe in CONCEPTS.md §7; writes `sampled_cells` (23,290 rows), adds `sampled_cell_count` to `perturbations` | Done | `e8d9581` |
| 2.4 | E-distance on sampled cells' 50 PCs → 20 closest each; writes `edistance` (27,730 rows), `similar_edistance` (4,720); 0 negative, min 0.11; matches pure-Python hand check and scipy to 1e-14 | Done | `1e7937c` |
| 2.5 | Deleted `legacy/`, rebuilt from Phase 1 files, ran again: all 8 tables identical across runs | Done | uncommitted (docs only) |

Answer key (`data/processed/norman/legacy/`):

| Table | Rows |
|---|---|
| `perturbations` | 236 |
| `signatures` | 487,576 |
| `top_genes` | 11,800 |
| `euclidean` | 27,730 |
| `similar_euclidean` | 4,720 |
| `sampled_cells` | 23,290 |
| `edistance` | 27,730 |
| `similar_edistance` | 4,720 |

Single-machine baseline (step 2.5, clean run, Apple M4):

| Stage | Seconds |
|---|---|
| Load Parquet | 0.3 |
| Gene averages | 0.8 |
| Signatures + ranking | 0.2 |
| Euclidean (all pairs) | 0.1 |
| Sampling | 0.1 |
| E-distance (all pairs) | 11.7 |
| Write tables | 0.1 |
| Script total | 13.3 |
| Process wall time (incl. ~2 s imports) | 15.5 |

Peak memory 2.4 GB. Imports include scanpy because the script reuses
`log`/`PROCESSED_DIR` from `convert.py`; time inside `run()` for benchmarks.

## Phase 3: PySpark job + parity (done)

Run: `uv run --env-file .env python -m pipeline.spark_signatures norman`
(`--hold` keeps the Spark UI at `localhost:4040` open until Enter).
Output: `data/processed/norman/spark/<table>/` (folder of part files).
Each build step runs a throwaway comparison against `legacy/`.

| Step | What | Status | Commit |
|---|---|---|---|
| 3.1 | Spark session, read Parquet, cells per perturbation; writes `perturbations` (236 rows; names, counts, target genes match legacy) | Done | `9f93a2a` |
| 3.2 | Broadcast join cells → sum per (perturbation, gene) → full grid (cross join + left join, fill 0) ÷ cell count → cached → minus broadcast control; writes `signatures` (487,576 rows, 11 part files). Matches legacy bit-for-bit (max gap 0.0), no missing/duplicate rows. ~8 s for this table vs ~1 s in pandas (Spark overhead at this size) | Done | `3cdbea7` |
| 3.3 | Window `row_number` per perturbation by abs(change) desc, gene asc; keep ≤50; writes `top_genes` (11,800 rows). Identical genes at every rank vs legacy, max gap 0.0. Plan: reads cached grid; `WindowGroupLimit` trims to top 50 per worker before the shuffle | Done | `3d80ef3` |
| 3.4 | Self-join signatures on gene (a < b) → sum squared gaps → sqrt; cached; union both directions → window rank ≤20; writes `euclidean` (27,730 rows), `similar_euclidean` (4,720). Max gap vs legacy 2.7e-15; neighbor rankings identical. SortMergeJoin output 57,290,180 rows, run once (cache). Full job ~29 s (euclidean ~10 s vs 0.1 s numpy) | Done | `b0f7789` |
| 3.5 | `tests/test_parity.py`: 5 tests (perturbations counts + target genes, signatures ≤1e-9, top-10 genes identical, euclidean ≤1e-9, similar lists identical); skips if outputs missing. Run: `uv run pytest tests/test_parity.py -v` → 5 passed in 0.5 s. Tamper check: +1e-6 on one signature and one dropped pair → 2 failed, restored → 5 passed | Done | `b4530fd` |
| 3.6 | `tests/fixtures/make_tiny.py` → `tests/fixtures/tiny/` (committed, 108 KB): 6 perturbations + control, 240 cells, 40 genes (5 targets + first 35 A–Z seen in kept cells), 1,723 expression rows, 110 zero-only (perturbation, gene) pairs. Both pipelines' `run(src, out, control)` take folders; CLIs unchanged. Test runs both pipelines on the fixture (session fixture, temp folder) and checks Norman if present: 10 passed (~20 s, needs Java: `uv run --env-file .env pytest`); without Norman outputs 5 passed, 5 skipped | Done | `70bb9bc` |
| 3.7 | Deliberate bug (÷ rows present) caught by parity, reverted; write-up in `docs/notes/` | Skipped (user's call; PLAN "done when" bug demo not done) | — |

## Phase 4: E-distance two ways (done)

Run: `uv run --env-file .env python -m pipeline.spark_signatures norman
--edistance udf|pandas` (default `udf`).

Benchmarks dropped (user's call, 2026-10-22): no benchmark scripts, charts, or
Replogle dataset. Scala way (4.4) skipped for now (user's call: "go with
PySpark"); docs say "two ways, Scala deferred".

| Step | What | Status | Commit |
|---|---|---|---|
| 4.1 | `sample_cells`: `F.md5(cell_id)` fingerprint, `row_number` per perturbation by (fingerprint, cell_id), keep ≤100; writes `sampled_cells` (23,290 rows); `perturbation_table` joins `sampled_cell_count`. Throwaway check vs legacy: same 23,290 (perturbation, cell_id) rows, fingerprints identical, no duplicates; `sampled_cell_count` equal for all 236, 12 below 100 (min 54). Parity suite: 10 passed (30 s). Full Norman job 77 s this run vs ~29 s in step 3.4; untouched stages were slower too (likely machine load, not checked) | Done | `89def88` |
| 4.2 | `cell_groups` (sampled cells' 50 PCs as float64, `collect_list` per perturbation, 236 rows) → `cell_pairs` (a < b, small side repartitioned to 40 chunks then broadcast-joined, 27,730 rows carrying both cell lists) → `edistance(groups, fn)` = 2 × between − spread a − spread b, `fn` = `mean_distance_udf` (plain `udf`, `useArrow=False`, numpy inside; same expression as legacy `mean_distance`); `nearest` reused. Writes `edistance` (27,730), `similar_edistance` (4,720). Throwaway check vs legacy: no one-sided/duplicate rows, max gap 1.4e-14, 0 negative (min 0.1105), neighbor lists identical (max gap 8.9e-15). E-distance stage ~42 s (legacy 11.7 s); full job 125 s. Parity suite: 10 passed (35 s) | Done | `beef5a1` |
| 4.3 | `mean_distance` (shared numpy math) used by `mean_distance_udf` and new `mean_distance_pandas` (`pandas_udf`, Series → Series, `np.stack` per row); `EDISTANCE_FNS` + `--edistance udf\|pandas` (default `udf`); `run(..., way=)`; `spark.sql.execution.arrow.maxRecordsPerBatch` = 500 (~40 MB per batch). Norman `--edistance pandas` vs legacy: max gap 1.4e-14, neighbor lists identical (same as udf). E-distance stage ~31 s vs ~42 s for udf (single runs, not a benchmark). Fixture throwaway with pandas way: 15 pairs, max gap 3.6e-15, but the stage took ~22 s for 15 rows (40 pair chunks → Python worker startup per task). Parity suite (udf default): 10 passed (41 s). pandas ≥ 3.0 warning printed, no failure | Done | `2be5139` |
| 4.4 | Way 3: Scala `scala/edistance/` → jar → PySpark | Skipped for now (user's call: "go with PySpark") | — |
| 4.5 | `tests/test_parity.py`: `test_perturbations` also checks `sampled_cell_count`; new `test_sampled_cells` (same rows, identical fingerprints), `test_edistance` (≤1e-9), `test_similar_edistance` (identical neighbors, ≤1e-9), each on fixture + Norman; `test_edistance_pandas_way` runs the pandas way on the fixture into a temp folder and checks against the fixture's legacy output (main fixture run uses udf, so both ways covered). Run: `uv run --env-file .env pytest tests/test_parity.py` → 17 passed in 107 s (was 10 in ~35 s; pandas-way fixture run adds most). Tamper check on Norman: +1e-6 on one E-distance and one sampled cell dropped → 2 failed; restored → 8 Norman tests passed. Docs: "three ways" → two, Scala deferred, Scala cut-order and post-MVP jar mentions removed (PLAN, ARCHITECTURE, README, CONCEPTS) | Done | `7b43c48` |

AI-assistant translation mistakes get logged in `docs/notes/` as they happen
(PLAN.md).

## Phase 5: MongoDB + FastAPI + CI (done)

Data source: Spark output only (`data/processed/norman/spark/`).
Load: `uv run --env-file .env python -m pipeline.load_mongo norman` (~6 s
per run, mostly imports; load itself < 1 s). Database `minixell`, collection
`perturbations`.
API: `uv run --env-file .env uvicorn api.main:app` → `http://127.0.0.1:8000`,
docs page at `/docs`. Env: `MONGODB_URI` (required), `MONGODB_DB` (default
`minixell`).

| Step | What | Status | Commit |
|---|---|---|---|
| 5.1 | `pipeline/load_mongo.py`: `load_tables` (pandas reads `perturbations`, `top_genes`, `similar_euclidean`, `similar_edistance`) → `build_documents` (236 docs per ARCHITECTURE.md schema, lists in rank order, `dataset` = `NormanWeissman2019`) → `ensure_indexes` (unique `{dataset, name}`, multikey `{top_genes.gene}`) → `write_documents` (delete dataset's docs, `insert_many`). Ran twice: 0 then 236 replaced, 236 total (no duplicates). Throwaway checks: every doc 50 top genes + 20 + 20 similar; 0 docs list themselves as similar; KLF1 matches Parquet exactly (targets, counts, all 90 list entries); doc size 3.9–4.2 KB; `explain()`: by name → IXSCAN `dataset_1_name_1` (1 examined, 1 returned), by gene HBZ → IXSCAN `top_genes.gene_1` (206 examined, 206 returned) | Done | `2e31555` |
| 5.2 | `api/main.py`: FastAPI app; `lifespan` opens one `AsyncMongoClient` (2 s server timeout) and stores a `PerturbationRepository` on `app.state`; `get_repository` dependency hands it to routes. `api/repository.py`: `PerturbationRepository(db, dataset)` with `ping()` and `get(name)` (find by `{dataset, name}`, `_id` dropped, returns dict). `api/models.py`: Pydantic `Health`, `TopGene`, `Neighbor`, `Similar`, `Perturbation`. Endpoints: `GET /health` (200 `{"status":"ok"}`; 503 when MongoDB unreachable), `GET /perturbations/{name}` (404 if unknown). Smoke run: `/health` 200; KLF1 → 50 top genes (HBZ first) + 20 + 20 similar (KLF1_BAK1 first); KLF1_BAK1 200; NOPE 404; `/docs` 200, lists both paths; server pointed at a dead port → `/health` 503 in 2.0 s | Done | `b7794c8` |
| 5.3 | `api/repository.py`: `search(gene, limit)` (find by dataset [+ `top_genes.gene`], sort name, limit; positional projection `top_genes.$` returns only the matched gene → `gene_change`) and `similar(name, metric)` (projects only `similar.<metric>`; None if unknown). `api/models.py`: `Metric` (`Literal["euclidean", "edistance"]`), `PerturbationSummary`, `SimilarResponse`. `api/main.py`: `GET /perturbations?gene=&limit=` (default 50, 1–236 via `MAX_LIMIT`), `GET /perturbations/{name}/similar?metric=` (default `edistance`). Choices: list sorted by name; exact gene match (`hbz` → 0 results). Smoke run: no gene → 50, sorted; limit=236 → 236; gene=HBZ → 206, KLF1 change 1.416903; limit 0 / 237 and metric=foo → 422; NOPE similar → 404; KLF1 similar → 20, KLF1_BAK1 first (edistance 0.131292, euclidean 0.794458); `/openapi.json` lists 4 paths. `explain()`: list all → IXSCAN `dataset_1_name_1`, covered (0 docs examined); similar → IXSCAN `dataset_1_name_1` (1 examined). Gene search: planner picks per gene; across all 388 top genes, 359 use `top_genes.gene_1` (AHR: 1 examined, 1 returned), 29 very common genes (in > 50 docs, e.g. HBZ in 206) use `dataset_1_name_1` to skip the sort (236 examined). Never a full collection scan; no index change | Done | `bb240d4` |
| 5.4 | Per the [step 5.4 contract](PLAN.md#step-54-contract-api-integration-tests). `tests/conftest.py` (**new**): `tiny` session fixture moved from `test_parity.py` (one Spark run shared by parity and API tests) + `require_java()` (runs `java -version`; clear setup failure). `tests/test_api.py` (**new**): `mongo` (ping; clear failure if `MONGODB_URI` unset or server down), `api_db` (unique `minixell_test_<12 hex>`, loads fixture Spark output via `load_mongo.run` under `NormanWeissman2019` + decoy records under `DecoyDataset`: same names with shifted numbers, plus `DECOY_ONLY` and gene `DECOYGENE`; dropped in `finally`), function-scoped `client` (`TestClient`, real lifespan, `MONGODB_DB` set per test); expected values read straight from Spark Parquet, tolerance 1e-9. 38 tests: health 200 / 503 (dead port, shared MongoDB untouched); get for all 6 perturbations (single + combination; metadata, ranked genes, both neighbor lists, no `_id`); unknown + decoy-only → 404; list exact + sorted, `gene_change` null, limit prefix; every fixture gene's search exact with changes; unknown / wrong-case / decoy gene → []; limit 1 and 236 accepted, 0 / -1 / 237 / abc / 1.5 → 422; similar for 6 × 2 metrics (order, distances, no self), default edistance, unknown/decoy 404, bad metric 422. `test_parity.py`: fixture + `legacy_signatures` import removed; tests unchanged. Dev dependency `httpx` 0.28.1. Results: `pytest tests/test_api.py -v` twice → 38 passed (41 s, 41 s); full `pytest -v` → 55 passed (17 parity + 38 API), 0 skipped (Norman outputs present), 67 s; re-run after conftest fix → 55 passed, 76 s. Tamper (throwaway pytest plugin, no app edits): dataset-blind search + reversed similar lists → 18 failed, 20 passed. Setup failures: dead `MONGODB_URI` → "MongoDB unreachable at …" error in 2.5 s; `JAVA_HOME=/nonexistent` → "Java 17 not found (tried /nonexistent/bin/java)" (first run raised a raw `FileNotFoundError`; fixed with `except OSError`). Live smoke: throwaway `/tmp/minixell_smoke/prepare.py` ran Spark on the fixture and loaded `minixell_smoke_b2779bf2c431` (6 docs); `MONGODB_DB=minixell_smoke_b2779bf2c431 uv run --env-file .env uvicorn api.main:app --port 8010`; curl: `/health` 200; list 200 (6, sorted, null changes); `gene=KLF1&limit=3` 200 (BAK1 0.1225, CEBPE −0.1493, CEBPE_KLF1 0.8828); `gene=klf1` → []; `limit=0` 422; KLF1_BAK1 200; NOPE 404; KLF1 similar 200 edistance (KLF1_BAK1 0.3937 first), euclidean 200 (KLF1_BAK1 0.7175 first); `metric=cosine` 422; NOPE similar 404. Cleanup: server stopped, smoke DB dropped, `/tmp/minixell_smoke` removed; databases after every run: admin, config, local, minixell only; `minixell` 236 docs, content hash `b698d3fc71f2cff2` same before and after. Note: Starlette warns "Using `httpx` with `starlette.testclient` is deprecated; install `httpx2`"; contract names `httpx`, so not switched | Done (accepted 2026-10-26) | `8f2739b` |
| 5.5 | Per the [step 5.5 contract](PLAN.md#step-55-contract-github-ci). `.github/workflows/ci.yml` (**new**): `push` + `pull_request`, no filters; one `ubuntu-24.04` job, `contents: read`, 30-min timeout; `mongo:8` service on 27017 with health check `mongosh … quit(db.runCommand({ping: 1}).ok ? 0 : 1)` (steps wait for healthy); env `MONGODB_URI=mongodb://127.0.0.1:27017`, `SPARK_LOCAL_IP=127.0.0.1`; `actions/checkout@v7`, `actions/setup-python@v7` (`python-version-file: .python-version`), `actions/setup-java@v6` (temurin 17, sets `JAVA_HOME`), `astral-sh/setup-uv@v10.3.2` (exact pin: no floating `v10` tag exists); `uv sync --locked` → `uv run --no-sync ruff check .` → `uv run --no-sync pytest -v -ra`. `pyproject.toml`: dev dependency `ruff` 0.17.3; `[tool.ruff.lint] select = ["E9", "F63", "F7", "F82"]`. Local checks (2026-10-27): `uv sync --locked` → resolved 77, checked 74, no changes; `uv run --no-sync ruff check .` → All checks passed; `uv run --no-sync --env-file .env pytest -v -ra` → 55 passed, 0 skipped, 35.7 s (17 parity incl. `test_edistance_pandas_way`, 38 API); CI-style run without `.env` (only `MONGODB_URI`, `SPARK_LOCAL_IP`, `JAVA_HOME` set) → 55 passed, 35.1 s. Databases after: admin, config, local, minixell (236 docs). Workflow checks: YAML parses (triggers push/pull_request, 1 job, 7 steps); health command exits 0 against the local MongoDB 8 container, 1 against a dead port; action inputs used exist in each pinned `action.yml` (all node24). Lead review: cleared to publish, no blocking findings. Publication: `gh repo create QuanDev2/miniXell --public --source . --remote origin`; commit `d1d16a0` (the 5 step files only); `git push -u origin main` (no force). Hosted run https://github.com/QuanDev2/miniXell/actions/runs/40625486917 on `d1d16a02b7a468665a779bf219ae72faaf5b9930` (push): success, 2 min 42 s; every step success (containers incl. MongoDB health, checkout, Python, Java, uv, locked install, Lint "All checks passed", Tests); Python 3.12.15, PyMongo 4.19.0; pytest → 47 passed, 8 skipped (all 8 `[norman]` parity tests: "Norman outputs missing"), 76 s: 38 API + 9 tiny parity (8 `[tiny]` + `test_edistance_pandas_way`). Evidence commit `5217b57` (pushed) → https://github.com/QuanDev2/miniXell/actions/runs/40625798578: success, 47 passed, 8 skipped | Done (accepted 2026-10-29) | `d1d16a0`, `5217b57` |

Docstring review (in `2e31555`): `pipeline/load_mongo.py` now uses Google-style
docstrings describing record contents, argument meaning, rank ordering, and
the non-atomic replacement risk. Syntax compilation passed; executable syntax
and the CLI description match the pre-edit version. No loader execution or
database writes during this review. `api/` uses Google style too (step 5.2).
Older files (`pipeline/convert.py`, `download.py`, `legacy_signatures.py`,
`spark_signatures.py`, `tests/`) still use `In:`/`Out:`/`State:`; not
restyled.

CI fix after acceptance (user: "Fix A"): GitHub's ubuntu-24.04 image moved
20261012 → 20261025 (kernel 6.19+); `mongo:8` (8.3.13) refused to start
("Linux kernel versions 6.19 and newer has a known incompatibility", MongoDB
SERVER-121912; SERVER-136272: 8.3/9.0 fail, 8.2 boots). Run
https://github.com/QuanDev2/miniXell/actions/runs/40979222561 on `17f8b23`
failed at "Initialize containers". Pinned service to `mongo:8.2` in `effbef4`;
run https://github.com/QuanDev2/miniXell/actions/runs/40979723800 on image
20261025.353.1, MongoDB 8.2.12: success, 47 passed, 8 skipped. Local Docker
stays on 8.3.13.

## Phase 6: Claude explain endpoint + demo page (in progress)

Claude access: Anthropic API key (user's call, 2026-10-29), not Bedrock.
Default model `claude-haiku-5-5` at effort `high` (user's call, changed from
`max`); the explain endpoint reads optional `CLAUDE_MODEL` / `CLAUDE_EFFORT`
overrides (6.3). Haiku's thinking counts toward `max_tokens`
(Anthropic effort docs).
Tests and CI use a fake Claude; no key in CI.

| Step | What | Status | Commit |
|---|---|---|---|
| 6.1 | `uv add anthropic` (2.3.0); key in `.env` (user). Throwaway smoke call `/tmp/minixell_claude_smoke.py` (deleted after): KLF1's top 10 genes from Spark Parquet → `claude-haiku-5-5`, effort `high`, `max_tokens` 16,000. Result: 4.3 s, 175 input / 874 output tokens (incl. thinking), `end_turn`; 3-sentence answer naming 9 genes (HBZ, HBG2, HBG1, HBA1, BLVRB, TMSB10, EMP3, PNMT, GAL), all in the input list; reads KLF1 as driving the erythroid/fetal globin program, flags direct vs downstream as undecidable. `.env.example` created, then deleted by the user (key had been pasted into it); not committed | Done | uncommitted |
| 6.2 | `pipeline/fetch_genes.py` (**new**): `top_gene_symbols` (distinct `top_genes.gene`, 388) → `query_mygene` (POST `mygene.info/v3/query`, human, fields symbol/name/summary; exact-symbol match wins, else top score) by `symbol`, then unfound genes by `alias,ensembl.gene,accession` → `build_documents` (`symbol` = dataset spelling, `current_symbol`, `full_name`, `summary`, `source`, `fetched_at`; nulls when missing) → `bulk_write` `ReplaceOne` upsert by symbol (not the briefed delete-then-insert: no empty window, other datasets' genes kept) + unique `{symbol: 1}`. Run: `uv run --env-file .env python -m pipeline.fetch_genes norman` (~2.4 s). Result: 360 by symbol, 16 by former name (e.g. C10orf54 → VSIR, HIST1H4C → H4C3), 12 not found (unnamed `RP11-…`/`AC…` IDs), 372 with a description (4 found without one, e.g. IER5L); HBD's two hits → exact match. Re-run: 388 written, 0 new. `explain()` by symbol → EXPRESS_IXSCAN `symbol_1`, 1 doc examined. `perturbations` untouched (236). Ruff passes. ARCHITECTURE.md `genes` schema: field table, `current_symbol`, nullable `summary` | Done | uncommitted |
| 6.3 | `api/explain.py` (**new**): `SYSTEM` prompt (explain only the given data, name only listed genes, no new numbers, no guessing for undescribed genes, flag what the data can't answer, one 4–6 sentence paragraph), `build_prompt` (perturbation, targets, cell count, then rank. gene (change): description or "No description available."), `explain` (one `messages.create`, `output_config.effort`, `max_tokens` 16,000, text blocks only; empty → `ValueError`). `api/repository.py`: `genes` collection + `descriptions(symbols)`. `api/models.py`: `Explanation` (name, model, explanation). `api/main.py`: `lifespan` makes one `AsyncAnthropic` (120 s timeout) only when `ANTHROPIC_API_KEY` is set; `POST /perturbations/{name}/explain` (404 unknown; 503 no key or Claude error); `CLAUDE_MODEL` / `CLAUDE_EFFORT` env overrides (defaults `claude-haiku-5-5`, `high`). Smoke run (uvicorn, real Claude): KLF1 200 in 7.6 s (166 words, 14 genes named), CEBPE_KLF1 200 in 9.0 s (153 words, 14), JUN 200 in 11.2 s (151 words, 17); throwaway check: every named gene is in that perturbation's top genes or targets; NOPE → 404. No key (TestClient) → 503 "Claude not configured". `/openapi.json` lists the route. Ruff passes; full suite 55 passed (138 s). No tests added (fake-Claude tests are 6.4) | Done | uncommitted |
| 6.4 | Guardrail (reject genes absent from signature/descriptions) + tests with a fake Claude, incl. planted made-up gene | Pending | — |
| 6.5 | Demo page `api/static/index.html` served by FastAPI; checked in a real browser | Pending | — |

## Environment (this machine)

- Apple M4, 24 GB RAM, 10 cores, macOS.
- Homebrew tools: uv 0.13.1, sbt 2.0.11 (runner), openjdk@17 17.0.20.1.
  openjdk 27 also installed as sbt's Homebrew dependency; unused.
- Python 3.12.15 via uv (`.python-version`); system Python 3.14 untouched.
- pytest 9.1.1 as a uv dev dependency (`uv add --dev pytest`, step 3.5).
- pymongo 4.19.0 (`uv add pymongo`, step 5.1); the API uses its async
  client (Motor is deprecated).
- fastapi 0.162.0, uvicorn 0.54.0 (`uv add fastapi uvicorn`, step 5.2).
- httpx 0.28.1 as a dev dependency (`uv add --dev httpx`, step 5.4) for
  FastAPI's `TestClient`.
- Tests: `uv run --env-file .env pytest` needs Java and MongoDB running; API
  tests use a throwaway `minixell_test_<random>` database, dropped after.
- Java is scoped to the project: run project commands as
  `uv run --env-file .env <command>`. Plain `uv run` is fine for pure Python
  that doesn't start Spark or sbt.
- `.env` is git-ignored; no committed template. Keys:
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`
  - `MONGODB_URI=mongodb://localhost:27017`
  - `SPARK_LOCAL_IP=127.0.0.1`
  - `ANTHROPIC_API_KEY` (step 6.1; user adds it)
- anthropic 2.3.0 (`uv add anthropic`, step 6.1).
- MongoDB: `docker compose up -d`; container `minixell-mongo`, MongoDB
  8.3.13, `127.0.0.1:27017`, volume `minixell_mongo-data`.
  Database `minixell` (step 5.1).
- Spark: PySpark 4.2.0 bundles the engine (277 jars, built for Scala 2.13);
  `local[*]` = 10 workers.
- Data: `data/raw/NormanWeissman2019_filtered.h5ad` (git-ignored). Re-fetch
  with `uv run python -m pipeline.download norman`.
- Processed data: `data/processed/norman/` (git-ignored), rebuilt with
  `uv run python -m pipeline.convert norman` (~50 s, peak 7.6 GB):
  - `cells.parquet`: 111,391 rows (cell_id, perturbation, is_control, gemgroup), 1.3 MB;
  - `expression.parquet`: 20,142,590 rows (cell_id, gene, value), 2,066 genes, 89.8 MB;
  - `cell_pcs.parquet`: 111,391 rows (cell_id, pc_1…pc_50), 34.7 MB.

## Decisions not in PLAN/ARCHITECTURE

- Homebrew `openjdk@17` instead of the Temurin installer (no admin password
  needed).
- `JAVA_HOME` set per project in `.env`, not globally (user's choice).
- `SPARK_LOCAL_IP=127.0.0.1` keeps Spark's driver off the Wi-Fi interface.
- Zenodo throttles (0.1–7 MB/s observed). `download.py` resumes partial
  downloads; don't run downloads under short timeouts.
- Learning scripts aren't saved to the repo unless the user asks.
- Step 1.4 applies DataXight's quality filter: drop cells with
  `percent_mito` ≥ 20% (54 of 111,445 cells). User approved.
- Schema: `name` = published label (e.g. `KLF1_BAK1`), `target_genes` =
  `name.split("_")`; no alphabetical renaming. Applied to ARCHITECTURE.md.
- Converter choices: `gemgroup` kept in `cells.parquet`; no per-gene
  standardizing before PCA; PCA seed 0; one file per table; expression
  `cell_id`/`gene` stored dictionary-encoded, `value` as float32.
- Gene list = 2,000 most variable genes + all targeted genes (2,066 total),
  so each perturbation's own target appears in its signature. User approved.
- Step 2.1 parity contract for Spark: sums in float64; output long tables
  (one row per perturbation × gene); top-gene rank = largest absolute change,
  ties by gene name A→Z; `rank` stored as a column (row order isn't kept).
- `legacy/` = outputs of the legacy script; Spark writes its own copy in
  phase 3 and parity compares them.
- Step 2.2 parity contract: `euclidean` stores each pair once (`a` < `b`
  alphabetically); similar lists rank by distance, ties by neighbor name A→Z,
  `rank` stored. Distances computed with plain numpy (no scipy; it's only a
  transitive dependency); matches scipy's exact function to 1e-14.
- Phase 7 added to the MVP: research assistant agent (`POST /ask`), design in
  ARCHITECTURE.md. Single agent, hand-written tool loop, five read-only tools,
  ledger-based guardrail, run records in `agent_runs`. User approved
  2026-10-22. Post-MVP phases renumbered 8–10; cut order now starts with
  phase 7.
- Demo page ("Option B"): one static HTML page served by FastAPI, built in
  phase 6 (search, top genes, similar, Explain), extended in phase 7 (Ask box).
  Phase 6 estimate now 1–1.5 days. User approved 2026-10-22.
- `/ask` and the explain endpoint both stay (user's call, 2026-10-22).

## Open items

- Claude access: decided 2026-10-29, Anthropic API (see Phase 6).
- PySpark 4.2.0 warns it doesn't fully support pandas ≥ 3.0 (installed via
  anndata). Worked so far: `toPandas` (step 2.3), `pandas_udf` with nested
  arrays (step 4.3). Only the warning is printed.

## Accepted limitations

- 3 targets labeled with old gene names aren't matched in the gene list:
  `C19orf26` (`CBARP`), `C3orf72` (`FOXL2NB`), `KIAA1804` (`RP5-862P8.2`,
  inferred). Their perturbations still get signatures and distances; they're
  only excluded from the "target moves in its own signature" sanity check.
  User accepted 102/105 (MVP over perfection).

## Notes for Phase 2 (legacy reference)

Goal (PLAN.md phase 2): `pipeline/legacy_signatures.py`, single-machine
pandas, all in memory, producing the answer key Spark must match in phase 3.
Details that matter for correctness:

- Inputs: `data/processed/norman/{cells,expression,cell_pcs}.parquet`.
- Averages: `expression` stores only non-zero values. A gene's average in a
  perturbation = sum of its values ÷ **that perturbation's total cell count**
  (from `cells`), not ÷ rows present. Same for the control average.
- Signature = perturbation average − control average, per gene (2,066 genes).
  Top genes = 50 largest by absolute change.
- Euclidean distance between two perturbations = straight-line distance
  between their full 2,066-gene average vectors (control cancels; see
  CONCEPTS.md §5).
- E-distance (CONCEPTS.md §6, pertpy's current formula):
  `2 × mean(between) − mean(within A) − mean(within B)`, cell-to-cell
  distances = plain Euclidean on the 50 PCs, within-group means include each
  cell paired with itself (divide by n²).
- Sampling for E-distance: up to 100 cells per perturbation, chosen by a
  pinned hash of `cell_id` (sort by hash, take first 100). Don't use Python's
  built-in `hash()` (randomized per process); pick an explicit algorithm Spark
  can reproduce. 12 perturbations have fewer than 100 cells; they use all.
- Similar lists: per perturbation, 20 closest others per metric; never itself;
  controls excluded (236 perturbations).
- Sanity check result (step 2.1): of 102 checkable targets, 21 rank #1, 51
  top 10, 77 top 50; 100 changed upward. Median target goes from expressed in
  11% of control cells to 52% of its perturbed cells. Ranks are modest because
  genes a target switches on can move more (KLF1 ranks #4 behind hemoglobin
  genes). ~7 targets barely move (e.g. ATL1, ZBTB25, PLK4: weak activation);
  CKS1B and CELF2 go slightly down. Hand check of HBG1 in KLF1 matched exactly.
- Output (answer key) goes under `data/processed/norman/` (git-ignored),
  e.g. a `legacy/` folder in Parquet.

## Working with this user

- Read [AGENTS.md](../AGENTS.md) first: teaching loop, one step then stop,
  MVP first, update this log after every step.
- The user's global rules also apply: numbered `##` sections, bold-led claims
  with short sub-bullets, plain terms by default, end by asking for direction,
  no changes without explicit approval.
- The user is a .NET/Angular developer learning this stack for a DataXight
  interview; .NET analogies land well. Expect conceptual questions before each
  step; answer briefly and at the level asked.
- Pre-implementation briefs: high level only (function names and what they
  do), with .NET analogies. No detailed code unless the user asks.
- Docstrings: Google style (`Args:` / `Returns:` / `Yields:` / `Raises:` /
  `Warning:`) for all new or edited code; `In:`/`Out:`/`State:` is retired
  (user's call, 2026-10-25). The global AGENTS.md no longer covers
  docstrings; this repo keeps Google style (user's call, 2026-10-29).
  Inline `#` comments: one 80-col line, max 2 (global AGENTS.md).
- Tone: terse, senior-engineer style; no chit-chat (user's call, 2026-10-29).
