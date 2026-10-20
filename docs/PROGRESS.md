# miniXell Progress

Handoff log: where the build stands, what's done, what's next. Updated after
every step. Phases are defined in [PLAN.md](PLAN.md); steps within a phase are
defined here.

Last updated: 2026-10-18.

## Current position

- **Done:** Phase 0, Phase 1, Phase 2, steps 3.1–3.5. Last commit: `b0f7789`
  (step 3.4).
- **Uncommitted:** step 3.5 (`tests/test_parity.py`, `pyproject.toml`,
  `uv.lock`, this file).
- **Next:** step 3.6 (tiny fixture; scripts take input/output folders; parity
  on fixture). Brief the user (commented code snippets; see "Working with
  this user"), wait for an explicit go.

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

## Phase 3: PySpark job + parity (in progress)

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
| 3.5 | `tests/test_parity.py`: 5 tests (perturbations counts + target genes, signatures ≤1e-9, top-10 genes identical, euclidean ≤1e-9, similar lists identical); skips if outputs missing. Run: `uv run pytest tests/test_parity.py -v` → 5 passed in 0.5 s. Tamper check: +1e-6 on one signature and one dropped pair → 2 failed, restored → 5 passed | Done | uncommitted |
| 3.6 | Tiny fixture in `tests/fixtures/`; scripts take input/output folders; parity on fixture | Next | |
| 3.7 | Deliberate bug (÷ rows present) caught by parity, reverted; write-up in `docs/notes/` | | |

`sampled_cell_count` and E-distance in Spark come in Phase 4. AI-assistant
translation mistakes get logged in `docs/notes/` as they happen (PLAN.md).

## Environment (this machine)

- Apple M4, 24 GB RAM, 10 cores, macOS.
- Homebrew tools: uv 0.13.1, sbt 2.0.11 (runner), openjdk@17 17.0.20.1.
  openjdk 27 also installed as sbt's Homebrew dependency; unused.
- Python 3.12.15 via uv (`.python-version`); system Python 3.14 untouched.
- pytest 9.1.1 as a uv dev dependency (`uv add --dev pytest`, step 3.5).
- Java is scoped to the project: run project commands as
  `uv run --env-file .env <command>`. Plain `uv run` is fine for pure Python
  that doesn't start Spark or sbt.
- `.env` is git-ignored. Keys:
  - `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`
  - `MONGODB_URI=mongodb://localhost:27017`
  - `SPARK_LOCAL_IP=127.0.0.1`
- MongoDB: `docker compose up -d`; container `minixell-mongo`, MongoDB
  8.3.13, `127.0.0.1:27017`, volume `minixell_mongo-data`.
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

## Open items

- Claude access (Anthropic API vs Bedrock): decide in phase 6.
- PySpark 4.2.0 warns it doesn't fully support pandas ≥ 3.0 (installed via
  anndata). Spark → pandas conversion worked in step 2.3's check; watch for
  issues in phase 3 (`toPandas`, `applyInPandas`).

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
- Pre-implementation briefs: show the code to be written as snippets with
  comments explaining each block or non-obvious line, plus a .NET analogy
  where it helps. The user asked for this format explicitly.
