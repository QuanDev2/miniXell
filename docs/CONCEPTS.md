# miniXell Concepts

Plain-terms reference for the science and math behind miniXell. Example
numbers are made up for illustration unless a source is named.

## 1. The experiment

**How the lab does it (pooled Perturb-seq).**

1. Grow millions of identical cells in one flask. The Norman dataset uses
   K562, a human leukemia cell line.
2. Add a pool of gene-editing instructions. Each instruction targets one gene
   and carries a readable barcode. The dose is low, so most cells randomly
   receive exactly one instruction, like drawing one card in a lottery.
3. Some instructions are dummies that target nothing. Cells receiving them are
   the **controls**: the untouched baseline.
4. Days later, cells are captured one per droplet. For each cell the machine
   reads which instruction it received and counts its gene messages.

**Vocabulary.**

| Term | Meaning |
|---|---|
| Perturbation | One instruction ("turn up gene KLF1", or in drug studies "add drug X"), plus the group of cells that received it |
| Experiment | The whole flask: many perturbations plus controls |
| Control | Cells with a dummy instruction; the baseline, not a perturbation |
| Pair | Two perturbations being compared, e.g. KLF1 vs GATA1 |

Example flask of 1,000 cells:

| Group | Instruction | Cells | Perturbation? |
|---|---|---|---|
| KLF1 | Turn up KLF1 | 300 | Yes |
| GATA1 | Turn up GATA1 | 250 | Yes |
| MYC | Turn up MYC | 250 | Yes |
| Control | Dummy | 200 | No, baseline |

Edge cases:

- Norman gave some cells two instructions on purpose ("turn up KLF1 and
  CEBPA"). The combination counts as its own perturbation.
- In drug studies (Tahoe-100M), each drug, sometimes each drug at each dose,
  is one perturbation.

## 2. Activity values

A gene is a recipe in the cell's DNA. To use it, the cell makes short-lived
copies of the recipe ("messages"). More copies means the gene is working
harder. The lab counts message copies per gene per cell: whole numbers, the
raw data in the h5ad file.

Each count is scaled in two steps:

1. **Rate**: copies ÷ total messages captured from that cell × 10,000. Fixes
   the machine capturing more from some cells than others. Like reporting
   crimes per 10,000 residents.
2. **Log**: value = ln(1 + rate). Zero stays zero; "times more" becomes equal
   steps, so a few very busy genes don't drown out the rest.

| Cell | Gene X copies | Total captured | Rate per 10,000 | Value ln(1 + rate) |
|---|---|---|---|---|
| #1 | 2 | 8,000 | 2.5 | 1.25 |
| #2 | 0 | 15,000 | 0 | 0 |
| #3 | 1 | 20,000 | 0.5 | 0.41 |

A single value has no everyday unit. Only comparisons between values mean
something. DataXight's April 2026 blog uses the same scaling (10,000 counts
per cell, then log1p).

## 3. Signature

**What it is.** One perturbation's summary report: how much each gene moved
compared with untouched cells.

**How it's computed.**

1. For each gene, average its value across the perturbation's cells.
2. Do the same across control cells.
3. Subtract: perturbation average − control average.
4. The 50 biggest moves, up or down, are the signature's top genes.

Because values are logs, the gap reads as a ratio: +0.69 ≈ 2× more active,
−0.69 ≈ half as active.

**Why it's needed.** Single cells are noisy and the raw data is millions of
rows. The signature condenses each perturbation into one comparable row of
2,000 numbers. Comparing, ranking, and explaining all run on signatures.

**Averages across machines.** In Spark, one perturbation's cells are spread
over many workers. Each worker reports a (sum, count) subtotal; subtotals are
added, then divided. Averaging the workers' averages is wrong, because each
worker saw a different number of cells:

| Worker | Sum of gene X | Cells | Its own average |
|---|---|---|---|
| 1 | 20 | 40 | 0.50 |
| 2 | 3 | 30 | 0.10 |
| 3 | 13 | 50 | 0.26 |
| Combined | 36 | 120 | **0.30** correct |

Average of averages = (0.50 + 0.10 + 0.26) ÷ 3 = 0.29, wrong. The parity test
exists to catch bugs like this.

## 4. Comparing a pair of perturbations

The output is always **one number per pair**: how alike two perturbations'
effects are. Small number = similar effect, which hints at a shared mechanism,
a new use for an existing drug, or a side-effect warning. A lead, not proof.

Pairs grow fast: n perturbations give n × (n − 1) ÷ 2 pairs. 3 → 3 pairs;
200 → 19,900 pairs.

Two ways to compute the number: Euclidean distance and E-distance.

## 5. Euclidean distance, step by step

Compares the two perturbations' **averages**.

1. Take each perturbation's average value per gene.
2. Line the two rows up, gene by gene; take each gap.
3. Square each gap, add them up, take the square root.

| Gene | KLF1 average | GATA1 average | Gap |
|---|---|---|---|
| Gene 1 | 0.9 | 0.8 | 0.1 |
| Gene 2 | 0.2 | 0.3 | −0.1 |
| Gene 3 | 0.5 | 0.5 | 0.0 |

Distance = √(0.01 + 0.01 + 0) ≈ 0.14.

Subtracting control first doesn't change the result: both perturbations
subtract the same control values, so control cancels in each gap.

## 6. E-distance, step by step

Compares the **cells themselves**. No averaging of cells first: it averages
distances, not cells.

1. Take each perturbation's sampled cells (up to 100 each).
2. **Between**: distance from every A cell to every B cell (100 × 100 =
   10,000 distances). Average them.
3. **Within A**: distance from every A cell to every A cell, each cell paired
   with itself included. Average them.
4. **Within B**: same for B.
5. E-distance = 2 × between − within A − within B.

The distance between two cells is the straight-line (Euclidean) distance
across their 50 summary numbers (section 7). So "Euclidean" appears at two
levels: the Euclidean metric measures between two averages; E-distance
measures between individual cells, then summarizes.

This matches pertpy's current implementation
(`2 * between - within_X - within_Y`, cell-wise metric `"euclidean"`), the
library DataXight's benchmark used.

**Why it differs from comparing averages.** One number per cell, two cells per
group:

| | Cells | Average |
|---|---|---|
| Group A | 0 and 4 | 2 |
| Group B | 2 and 2 | 2 |

- Euclidean: averages are both 2 → distance 0 → "identical".
- E-distance: between = mean(2, 2, 2, 2) = 2; within A = mean(0, 4, 4, 0) = 2;
  within B = 0 → 2 × 2 − 2 − 0 = **2** → "different".

A is scattered, B is tight, same center. Picture each perturbation's cells as
a crowd in a park: Euclidean measures between crowd centers; E-distance also
sees how spread out each crowd is. In biology, a drug pushing all cells the
same way and one scattering them randomly can share an average and still
behave differently.

**Cost.** About 30,000 cell distances per pair, times ~20,000 pairs. That's
why it's the expensive calculation, the one ported to Spark two ways.

| | Euclidean | E-distance |
|---|---|---|
| Compares | Two averages | All cells in both groups |
| Sees spread inside groups | No | Yes |
| Cost | Very cheap | Heavy |
| DataXight benchmark: signal strength | 2.93× | 8.61–11.19× (E-distance and MMD) |
| DataXight benchmark: runtime, 27,000 cells | 0.11 s | 1.7 s |

## 7. Making E-distance affordable

**50 summary numbers instead of 2,000 genes.** Genes move in teams, like
height, arm length, and shoe size rising together in people. A standard
technique (principal components) finds 50 summary scores per cell that keep
most of the differences between cells. Cell-to-cell distances on 50 numbers
are 40× less work than on 2,000. Small details carried by few genes can blur;
this is standard practice for cell-to-cell comparisons. Signatures and
Euclidean distance still use all 2,000 genes.

**100 cells per perturbation instead of all.** Some perturbations have over
1,000 cells; 100 gives a reliable picture at a fraction of the cost.

**A fixed sampling rule.** If the legacy script and Spark picked different
random cells, both would be correct yet disagree, and parity would fail with
no real bug. Like two auditors each auditing 100 random case files and
reporting different error rates. The rule: turn each cell ID into a fixed
fingerprint number (hash), sort by it, take the first 100. Same IDs → same
picks, every run, any machine, any language.

Trap: Python's built-in `hash()` changes every time a program starts, and
Spark's built-in hash uses a different recipe. Both sides must use one
explicit, pinned recipe. Bonus: reruns give identical answers.

**The pinned recipe** (legacy and Spark must both follow it exactly):

1. Skip control cells; group the rest by perturbation.
2. Fingerprint = MD5 of the `cell_id` text (UTF-8), written as 32 lowercase
   hex characters. Python: `hashlib.md5(cell_id.encode()).hexdigest()`; Spark:
   `F.md5("cell_id")`.
3. Within each perturbation, sort by fingerprint, then `cell_id` (tie-break),
   and keep the first 100. Fewer than 100 cells → keep all.

Norman: 23,290 sampled cells; 12 perturbations keep all (smallest 54). Spark
run on the same rule picked the identical set.

## 8. Similar lists

For each perturbation, Spark ranks every other perturbation by distance and
keeps the 20 closest, separately for Euclidean and E-distance. The lists are
stored in order inside the perturbation's MongoDB document, so the API reads
them without sorting.
