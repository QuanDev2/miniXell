# miniXell Progress

Handoff log: where the build stands, what's done, what's next. Updated after
every step. Phases are defined in [PLAN.md](PLAN.md); steps within a phase are
defined here.

Last updated: 2026-10-18.

## Current position

- **Done:** Phase 0 and Phase 1. Last commit for Phase 1: `cbc9338`.
- **Uncommitted:** nothing.
- **Next:** Phase 2 (legacy reference). Define its steps (see "Notes for
  Phase 2" below), brief the user, wait for an explicit go per step.

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

## Environment (this machine)

- Apple M4, 24 GB RAM, 10 cores, macOS.
- Homebrew tools: uv 0.13.1, sbt 2.0.11 (runner), openjdk@17 17.0.20.1.
  openjdk 27 also installed as sbt's Homebrew dependency; unused.
- Python 3.12.15 via uv (`.python-version`); system Python 3.14 untouched.
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

## Open items

- Claude access (Anthropic API vs Bedrock): decide in phase 6.

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
- Sanity check: each single-gene perturbation's own target ranks high in its
  signature (102 targets available; see Accepted limitations).
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
