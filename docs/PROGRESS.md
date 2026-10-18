# miniXell Progress

Handoff log: where the build stands, what's done, what's next. Updated after
every step. Phases are defined in [PLAN.md](PLAN.md); steps within a phase are
defined here.

Last updated: 2026-10-18.

## Current position

- **Done:** Phase 1, step 1.3 (inspect the h5ad file). Findings:
  [notes/norman-dataset.md](notes/norman-dataset.md).
- **Uncommitted:** step 1.3 (`docs/notes/norman-dataset.md`, removed
  `docs/notes/.gitkeep`) and this log update.
- **Next:** step 1.4 (write and run `pipeline/convert.py`). Brief the user
  first, then wait for an explicit go (see [AGENTS.md](../AGENTS.md)).

## Phase 0: Toolchain and skeleton (done)

Chat called these steps "3.1–3.5"; same steps.

| Step | What | Status | Commit |
|---|---|---|---|
| 0.1 | Install uv, sbt, Java 17; scope Java to project via `.env` | Done | `7a1960a` (AGENTS.md, `.gitignore`) |
| 0.2 | uv project with PySpark, folders, `.gitignore` | Done | `0fb1938` |
| 0.3 | MongoDB in Docker | Done | `52c6488` |
| 0.4 | Smoke test: Spark sum 1..1000 = 500500; `sbt --version` | Done | no files |
| 0.5 | Commit check | Done | nothing to commit |

## Phase 1: Data → Parquet (in progress)

| Step | What | Status | Commit |
|---|---|---|---|
| 1.1 | Add anndata, scanpy, pyarrow | Done | `482e3fb` |
| 1.2 | `pipeline/download.py`; download Norman h5ad (699 MB, MD5 verified) | Done | `482e3fb` |
| 1.3 | Inspect the file: cells, genes, `obs` columns, perturbation label column, control label, combination label format, whether `X` holds raw counts | Done | uncommitted |
| 1.4 | Write and run `pipeline/convert.py` → `cells.parquet`, `expression.parquet`, `cell_pcs.parquet` in `data/processed/norman/` | Next | |
| 1.5 | Inspect Parquet output: row counts, sizes, sample rows | Pending | |

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

## Decisions not in PLAN/ARCHITECTURE

- Homebrew `openjdk@17` instead of the Temurin installer (no admin password
  needed).
- `JAVA_HOME` set per project in `.env`, not globally (user's choice).
- `SPARK_LOCAL_IP=127.0.0.1` keeps Spark's driver off the Wi-Fi interface.
- Zenodo throttles (0.1–7 MB/s observed). `download.py` resumes partial
  downloads; don't run downloads under short timeouts.
- Learning scripts aren't saved to the repo unless the user asks.

## Open items

- Quality filter in step 1.4: apply DataXight's `percent_mito` < 20% filter?
  Affects 54 of 111,445 cells.
- Schema doc update pending user approval: drop the alphabetical-renaming
  rule (labels have no duplicate pairs; `name` = published label,
  `target_genes` = `name.split("_")`), and replace illustrative `GATA1` /
  `TAL1` (not in dataset) with real names.
- Claude access (Anthropic API vs Bedrock): decide in phase 6.
