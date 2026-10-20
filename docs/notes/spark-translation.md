# pandas → PySpark translation log

What the AI assistant (Claude) got wrong or missed while translating
`pipeline/legacy_signatures.py` to `pipeline/spark_signatures.py`, and what
caught it. Phase 3, PLAN.md.

| Step | Mistake | Caught by | Fix |
|---|---|---|---|
| 3.2 | Reused the averages grid (`means`) for both the control row and the experiments. In pandas a variable holds data; in Spark it holds a recipe, so each use re-ran the 20M-row join + sum. No `ReusedExchange` in the plan. | Reading the executed plan (two `partial_sum` branches) | `.cache()` on `means`; Spark UI now shows one sum stage (30.5 MB shuffle write) |
| 3.2 | Predicted ~1e-12 gaps vs legacy from different addition order. Actual: bit-identical (max gap 0.0) on this data. | Throwaway comparison | None needed; parity keeps a tolerance because a different partitioning can change the order |
| 3.2 | Log lines vanished from the terminal: Spark's console progress bar overwrote them with carriage returns. | Missing `wrote spark/signatures/` line in output | `spark.ui.showConsoleProgress=false` |
| 3.3 | Briefed that ranking shuffles the whole 487,576-row signatures table. Spark actually inserts `WindowGroupLimit (Partial)` before the shuffle: each worker keeps its local top 50 per perturbation, so at most 50 rows per perturbation per worker move. | Reading the executed plan | None needed; the brief was wrong, the code was fine |
