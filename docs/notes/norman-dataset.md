# Norman 2019 dataset: inspection findings

File: `data/raw/NormanWeissman2019_filtered.h5ad` (699 MB, scPerturb v1.4,
CC BY 4.0). Inspected 2026-10-18 (Phase 1, step 1.3).

## Shape

| Item | Value |
|---|---|
| Cells | 111,445 |
| Genes | 33,694 |
| Non-zero values | 361,582,621 (9.63% of cells × genes) |
| Cell line | K562 only |
| Perturbation type | `CRISPR` in the file; the Norman study used CRISPR activation (genes turned up) |

## Cells (`obs`)

- **Perturbation label column:** `perturbation` (category).
- **Controls:** label `control`, `nperts == 0`. 11,855 cells.
- **Perturbations:** 236 labels besides `control`:
  - 105 single-gene (`nperts == 1`, 57,831 cells), e.g. `KLF1`, `CEBPA`;
  - 131 two-gene (`nperts == 2`, 41,759 cells), e.g. `KLF1_CEBPA`.
- **Combination format:** genes joined by `_`. Order is **not** alphabetical
  (e.g. `KLF1_BAK1`, `JUN_CEBPA`), but each pair appears under one label only
  (131 labels = 131 distinct pairs). No single-gene label contains `_`.
- **Cells per perturbation:** min 54 (`JUN_CEBPA`), median 352, max 1,960
  (`KLF1`). 12 perturbations have fewer than 100 cells; none fewer than 50.
- **Batches:** `gemgroup` 1–8 (separate capture runs), 13,083–15,033 cells
  each.
- **Quality columns:** `ncounts`, `ngenes` (min 974), `percent_mito`
  (median 6.3%, max 42.6%; 54 cells ≥ 20%), `percent_ribo`, `guide_id`.
- Other columns (`cell_line`, `disease`, `organism`, …) are constant.

## Genes (`var`)

- Index = gene symbols (e.g. `KLF1`), all unique.
- `ensemble_id` column holds database IDs (e.g. `ENSG00000243485`).
- Includes many unnamed/non-coding genes (e.g. `RP11-34P13.3`); the
  2,000-most-variable selection filters most of them out.

## Values (`X`)

- Sparse, column-compressed (`csc_matrix`), `float32`.
- **Raw counts:** all whole numbers, min 1, max 3,718.
- Total counts per cell: median 13,855, min 3,679, max 64,352.
- No precomputed extras: `obsm` empty (no principal components), no layers,
  no `uns`.

## Consequences for the converter (step 1.4)

- Read labels from `obs["perturbation"]`; `is_control = perturbation == "control"`.
- Values are raw counts → scale per 10,000 then log, as planned.
- `X` is column-compressed; convert to row-compressed before per-cell work.
- Principal components must be computed (none in the file).
- Gene identifier = symbol; keep `ensemble_id` available for gene lookups.
- Open for step 1.4: apply DataXight's quality filter (`percent_mito` < 20%)?
  Affects only 54 cells.

## Consequences for the schema

- `name` = the dataset's label as published (e.g. `KLF1_BAK1`); no
  duplicate pairs exist, so the alphabetical-renaming rule isn't needed.
- `target_genes` = `name.split("_")`.
- Illustrative examples in the docs use `GATA1` and `TAL1`; neither is in
  this dataset. Real names to use instead: e.g. `CEBPE`, `BAK1`, `CEBPA`.
- `gemgroup` gives real batch labels, so batch-aware control comparison
  (previously "not checked") is possible.

## Processed output (step 1.5)

Checked 2026-10-18 against `data/processed/norman/` from `95e0ce1`.

**Consistency: all pass.**

- `cells`: 111,391 unique `cell_id`s; `is_control` matches
  `perturbation == "control"`.
- Every `expression` `cell_id` exists in `cells`; every cell has at least one
  expression row.
- `cell_pcs` has the same `cell_id`s in the same order as `cells`.
- Per-perturbation counts equal the raw file minus the quality filter
  (237 labels; KLF1 1,959; control 11,849).

**Values.**

- 18,468,826 rows, all > 0; min 0.144, max 8.545 (log scale); exactly 2,000
  distinct genes; median 165 non-zero genes per cell.

**Parquet internals (`expression.parquet`).**

- `cell_id`, `gene`: dictionary-encoded strings (int32 indices); `value`:
  float32.
- 23 row groups of 1,048,576 rows (last 222,302); Snappy compression;
  dictionary + run-length encodings.
- Reading one column: 0.04 s; all three: 0.16 s (warm cache).

**Target genes: check failed, then fixed.**

- First run: only 36 of the 105 targeted genes were among the 2,000 most
  variable genes. 69 were missing, including `BAK1`, `CEBPB`, `SET`, `FOSB`,
  `ARID1A`.
- Cause: gene selection measures variability across all cells, and each
  target is turned up in only its own perturbation's cells (~0.3% of all
  cells), so its overall variability stays modest.
- Fix (user chose option A): `convert.py` keeps the 2,000 most variable genes
  plus every targeted gene. Re-run: 2,066 genes (2,000 + 66 targets outside
  them), 20,142,590 expression rows, 89.8 MB, peak memory 7.6 GB, 48 s.
  Consistency checks above still hold.
- Result: 102 of 105 targets kept. The other 3 are labeled with old gene
  names that the gene list stores under newer names:

  | Label name | Gene list name | Evidence |
  |---|---|---|
  | `C19orf26` | `CBARP` | mygene.info alias lookup |
  | `C3orf72` | `FOXL2NB` | mygene.info alias lookup |
  | `KIAA1804` | `RP5-862P8.2` | [INFERENCE] KIAA1804 = MAP3K21 (MLK4), Ensembl ENSG00000143674, which the gene list names `RP5-862P8.2`; mygene.info doesn't list KIAA1804 as an alias |
