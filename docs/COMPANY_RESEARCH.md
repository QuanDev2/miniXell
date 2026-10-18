# DataXight Research Notes

Everything gathered about DataXight, protoXell, their engineering, and their
problems. Researched 2026-10-16 to 2026-10-17 from public sources (listed at
the end) and the recruiter conversation.

Labels used below:

- **[Recruiter]**: what the recruiter told me.
- **[INFERENCE]**: my reasoning, not stated by any source.
- Everything else is stated in a cited public source.

---

## 1. Company

| Item | Detail |
|---|---|
| Name | DataXight |
| Tagline | "Accelerating Innovation, from Data to Insight" |
| Founded | February 2023, by Tuan Nguyen |
| Headquarters | Mountain View, California |
| Delivery hubs | Saigon / Ho Chi Minh City (167 Tran Nao, An Khanh), Bangkok, Prague |
| Size | 11–50 (Crunchbase); 1–50 (ITviec) |
| Funding | Private; no funding announcements found |
| Industry | Life sciences and healthcare data: software, data engineering, bioinformatics, AI/ML |
| Business model | Services (consulting, staff augmentation, dedicated teams, outsourcing, managed services) plus own products (protoXell, PROTOplast) |

### Milestones (About Us page)

| Date | Milestone |
|---|---|
| Feb 2023 | DataXight founded |
| Jul 2023 | First U.S. client |
| Sep 2023 | First European client |
| Jan 2024 | DataXight 84 (Vietnam entity) launched |
| May 2024 | First Asian client |
| Nov 2024 | First annual team outing |
| Apr 2025 | Bioinformatics & AI development operations established in Thailand |
| Jun 2025 | Collaboration with HCM University of Technology |
| Oct 2025 | PROTOplast product page published |
| May 19, 2026 | protoXell launched at Bio-IT World Conference & Expo |

### Leadership

| Person | Role | Background |
|---|---|---|
| Tuan Nguyen | Founder, CEO | Builds data platforms; integrates complex datasets |
| Tri Le | Chief Product Officer | Ex-DNAnexus, BioTuring; helped build BBrowser (large-scale single-cell analysis); co-author of two protoXell science blog posts |
| Tan Phan | CTO | Ex-DNAnexus, BioTuring; genome assembly, single-cell analytics, high-performance research computing |
| Michael Pan | Chief Data Scientist | Ex-Head of Data & Analytics for Diagnostics at Danaher; earlier Roche, DNAnexus, 23andMe; wrote the Parquet scaling blog post; publishes PROTOplast and protoform on PyPI |
| Anne Hunt, PhD | VP Strategy & Growth | Ex-Microsoft, AWS; PhD in logic, semantics, knowledge systems |
| Eric Talevich, PhD | VP Bioinformatics | Ex-Form Bio, DNAnexus (UK Biobank research platform), UCSF, Caris Life Sciences; created open-source tool CNVkit |

Leadership experience they cite: Roche, Danaher, Microsoft, AWS, DNAnexus,
Form Bio, QIAGEN, BioTuring.

### Values and culture

- Core values: Employees First, Client Centricity, Return on Innovation,
  Unwavering Quality.
- Employees are "Xighters." "Curiosity and common sense guide our thinking.
  Courage and respect ground our values. Commitment fuels everything we do."
- "Ø Drama": transparency, lean teams, focus on outcomes.
- Company lunches, "happy Wednesday" snacks, video games, badminton, spot
  bonuses nominated by peers.
- ITviec: Monday–Friday, "No OT" policy, 12 days annual leave + 2 floating
  holidays, MacBook provided.
- Job posts value: inquisitive mindset, clarity, "depth of perception"
  (seeing the need behind a request), implementation insight, articulate
  communication; occasional US/EU time-zone overlap.
- No employee reviews exist on ITviec; Glassdoor shows one rating, no text.

### Clients and partners

- Named on site ("Spotlight"): Champions Oncology, Crown Bioscience,
  Danaher, DNAnexus, Form Bio, UPenn.
- In site metadata only: Indivumed, JSR.
- Danaher testimonial (Dmitrii Calzago, Senior Manager, Data & Analytics):
  DataXight built a data platform integrated with Snowflake, cloud-native
  infrastructure components, and custom applications with API and UI for
  multi-omics and clinical data.

---

## 2. Services

| Service | What they sell |
|---|---|
| AI Quickstart | "Deploy foundation-model inference in six weeks—on your infrastructure, with validated notebooks and results your team can own and extend." |
| Data Services & Solutions | Data curation, quality, governance, engineering, data products, managed services. Mentions a managed service "ProtoXight." Standard vocabularies (MeSH, SNOMED), FAIR-compliant data, version control, audit-ready lineage. |
| Software & AI/ML | Custom scientific applications and UI/UX; data and workflow orchestration (ingestion, transformation, QC, scheduling); ML enablement (training, deployment, monitoring; "reproducible, secure, and cloud-agnostic architectures"). |
| Science Services | Genomics, bioinformatics, translational research. |

Claims across service pages:

- Platform-agnostic: AWS, Azure, GCP, DNAnexus, on-prem, hybrid.
- Compliance: HIPAA, GxP; auditability, traceability, data security.
- Reproducibility: standardized, version-controlled software, documentation.

---

## 3. protoXell (flagship product)

### What it is

"Cell response discovery software": explore, compare, and interpret
perturbation data across experiments, "without pipelines, infrastructure,
complexity, or specialized expertise." Launched May 19, 2026.

### Core capabilities

| Capability | Detail |
|---|---|
| Curated Perturbation Catalog | 150M+ cells; cell lines, tissues, compounds, CRISPRi perturbations; public sources include Tahoe-100M and Xaira X-Atlas/Orion; harmonized for cross-study analysis; new data "as often as 3 days after a dataset is requested"; enterprise customers add proprietary data |
| Comparative Analysis | Compare perturbation effects across experiments at gene and pathway level |
| inXighter (AI interpretation) | LLM connects results to mechanisms and literature. FAQ: "The LLM does not generate or alter results; it only interprets deterministic outputs." |
| Enterprise Integration & Deployment | SaaS, private cloud, on-prem, hybrid; "modular components" that can run in separate environments |

Other stated features:

- Genetic and chemical perturbations; cell lines and in vivo models.
- Cross-species analysis via homolog mapping (human, mouse).
- Point-and-click interface, no coding.
- "Support virtual cell modeling" and "Power LLM-driven agents."
- Customer data never used to train shared AI models without agreement.
- Free access option, flexible licensing; DNAnexus availability planned for
  June 2026.

### Use cases and showcase examples

| Use case | Example on product page |
|---|---|
| Side-effect / toxicity detection | Saquinavir (HIV protease inhibitor) shares disruptions in electron transfer and ion channels with norepinephrine → possible mitochondrial dysfunction or cardiotoxicity |
| Mechanism of action | AZD2858 (GSK-3 inhibitor) suppresses RREB1, rewiring "stemness" in PANC-1 and LoVo cells → anti-invasive effect beyond the known Wnt pathway |
| Novel drug target | Berbamine in HEC1A endometrial cancer cells raises cholesterol homeostasis; protoXell pinpoints PCSK9 and LDLR |
| Drug repositioning | Trifluridine (nucleoside analog) signature resembles Everolimus (mTOR inhibitor) → possible use in growth-signaling disorders |

### Customer pain points they target (product page)

1. Data fragmented across experiments, modalities, teams.
2. Infrastructure complexity: compute-intensive pipelines hard to scale across
   cloud and HPC.
3. Interpretation needs coding, statistics, algorithm expertise.
4. Linking results to mechanisms and literature is slow manual curation.
5. "Answering even simple biological questions can take weeks or months."

---

## 4. PROTOplast and open source

### PROTOplast

- Open-source Python library (Apache 2.0) on PyPI: "Scalable machine learning
  for molecular data analysis"; "single-cell data loader for distributed ML."
- Streams h5ad files directly from cloud storage (patches `anndata` to use
  `fsspec`).
- Distributed training with Ray + PyTorch Lightning; "14.5 minutes on an A100
  instance with 4 GPUs"; "scale to multi-node clusters with zero code changes."
- Also reads VCF (genomic variant) files via Daft.
- Benchmarks against Tahoe-100M, Virtual Cell Challenge (VCC), and Xaira data;
  an example notebook prepares a VCC submission.
- Engineering signals: `uv`, GitHub Actions (TestPyPI on prerelease, PyPI on
  release from main), mkdocs, pre-commit, Docker; Jira project key `PROTO`.
- Fixes in its history show distributed-correctness work:
  - PR #24: imbalanced batches across GPUs;
  - PR #48: "Dropping too many data";
  - PR #46: verify every worker can reach storage before training;
  - PR #55: keep data order consistent across workers per epoch.
- Open items: issue #63 (multi-layer / multi-modal h5ad request), PRs #18/#20
  (GDS-backed storage proof of concept), PR #15 (perturbation training data
  module, scverse 2025).

### Other public code

- `protoform` on PyPI ("shaping data"), released Feb 2026, by Michael Pan.
- GitHub org `dataxight`: 14 repos. Own: `protoplast`, `protoplast-examples`,
  `toy-data-web-app` and `protein-atlas` (Taipy data web app examples). Forks:
  `anndata`, `pqdata` (AnnData ↔ Parquet), `SIMS`, `tabnet`, `alphatims`,
  `alphaviz`, `structuremap`, `gcp-variant-transforms`, `pipelines-tools`,
  `variant-annotation`.

---

## 5. Blog findings

### "Democratizing Scalable Single-Cell RNA Analyses" (Michael Pan, Jun 23, 2025)

- Datasets: CellxGene, Arc Institute, Tahoe-100M, Xaira X-Atlas/Orion.
- Tahoe-100M: 300 GB across 14 h5ad files of 12–35 GB; matrices typically
  >95% zeros; "could easily require upwards of 1TB of memory when fully
  loaded" (estimate).
- Limits of existing tools: memory constraints (little out-of-core support),
  single-machine assumptions, file-backed limitations.
- Alternatives noted: Dask, rapids-singlecell.
- Their approach: convert AnnData to DataFrames stored as Parquet; analyze
  with Daft (lazy evaluation) + Ray (scaling).
- Conversion problems: `pqdata` broke on newer `anndata` sparse objects (they
  fixed it); then ran out of memory on the smallest Tahoe plate.
- Conversion time: 2.5–7.5 hours per Tahoe plate on an 8 GB MacBook M1.
- Benchmark, plate 7 (15.4 GB): `anndata` crashed on count, max, mean.
  Daft: count 11.03 s (5,692,117 rows), max 11.14 s, mean 10.93 s.
- Two plates (28 GB): ~20–21 s per operation, 10,397,519 rows.
- Promised to open-source the conversion code.

### "Perturbation effect is not an on-off switch" (Loc Tran, Tri Le, Apr 16, 2026)

- Data: Nadig et al. 2025, CRISPRi study of 2,000+ genes in hepatocellular
  carcinoma cells.
- Of 2,160 knockdowns, 60.2% (1,300) significantly reduced the target gene;
  39.8% (860) did not (Wilcoxon rank-sum, Bonferroni-corrected).
- Three metrics compared: target gene expression, gene rank, fold change.
  Expression correlates with rank and with fold change; rank and fold change
  don't correlate.
- On 140,497 cells, clusters 3 (21,107 cells) and 5 (10,265 cells) look
  distinct in expression space but merge in fold-change space; 88.7% of
  their perturbations are shared.
- Conclusion: analytical conclusions are metric-dependent.
- Preprocessing used: quality control (mitochondrial % < 20, UMI > 1,000),
  normalize to 10,000 counts per cell, log1p, at least 5 cells per
  perturbation; anndata, scanpy, scikit-learn, matplotlib. miniXell's
  normalization matches this.

### "Comparing Perturbations: E-distance and Euclidean distance are Your Best Allies" (Loc Tran, Nhan Tran, Tri Le, May 14, 2026)

- Test case: Saquinavir's hidden adrenergic signal (from a Tahoe blog post).
- Data: Tahoe plate 6, 3,000 cells per drug, 62,710 genes, 9 treatments:
  targets (Saquinavir, Terfenadine), positive controls (Vilanterol,
  Norepinephrine), background (Furosemide, Clonidine, Verapamil, Lidocaine,
  DMSO).
- Tool: pertpy. Metrics: Euclidean, E-distance, Mean Pairwise, Wasserstein,
  MMD.
- All metrics recovered the adrenergic core; Lidocaine unexpectedly close to
  Saquinavir (possible off-target effect).
- Top-5 rankings: Euclidean, E-distance, MMD identical; Wasserstein and Mean
  Pairwise diverge.
- Signal strength ratio: Mean Pairwise / Wasserstein 1.04–1.10×; Euclidean
  2.93×; MMD / E-distance 8.61–11.19×.
- Discrimination (CV% across top-5 pairs): Euclidean and E-distance
  12.7–33.5%; Wasserstein and Mean Pairwise near zero.
- Runtime on 27,000 cells, 96 cores, 125 GB RAM: Euclidean 0.11 s,
  E-distance 1.7 s, MMD 3.6 s, Mean Pairwise 174.7 s, Wasserstein 557.9 s.
- Conclusion: E-distance and Euclidean are the pragmatic choice for
  high-throughput pipelines.

### "Looking at batch effect through scRNA-seq data" (Sep 17, 2024)

- Simulation (splatter): 2,300 cells, 5,000 genes, 3 patients, tumor vs
  adjacent tissue; 117 truly changed genes (54 up, 63 down).
- With batch effects, standard Seurat analysis found 112 genes: missed 9
  (7.7% false negatives), 4 wrong (3.6% false positives).
- "Its effect grows even bigger when you combine datasets from multiple
  studies."

---

## 6. Hiring signals

### Open roles (careers page, Oct 2026)

Senior Quality Engineer (Automation, Backend); Senior Quality Engineer
(Automation, Full Stack); Senior Bioinformatics Engineer – Scientific
Computing; Senior Bioinformatics Engineer – Computational Genomics;
Bioinformatics Engineer; Senior Software Engineer (NodeJS, Python); Staff
Software Engineer (NodeJS, Python); Senior Software Engineer (Distributed
Computing); Senior AI Software Transformation Engineer (Distributed
Computing); Lead Software Engineer (Distributed Computing). Also linked: Cloud
Platform Engineer (Bangkok), Cloud Support Engineer, Senior Data Engineer,
Senior Full Stack Engineer. Most roles exist in both Ho Chi Minh City and
Bangkok.

### Key quotes

**Senior Software Engineer (Python, Cloud, Distributed Computing)**
- "Many high-value analytical applications were originally designed for
  single-node or limited-scale execution and struggle to efficiently process
  today's increasingly large and complex datasets. This role focuses on
  transforming those applications into scalable, distributed solutions
  running on a Spark-based cloud platform."
- Must: Python, AWS preferred, relational + NoSQL, CI/CD pipelines,
  unit/integration testing, 5+ years.
- Nice: Spark/PySpark; "NodeJS or Go is highly preferred… for building APIs";
  OAuth2/SAML; MLOps.

**Senior Software AI Transformation Engineer (Distributed Computing)**
- "Help build an AI-powered framework for transforming complex analytical
  software into scalable cloud-native platforms."
- "Use AI agents, LLMs, and emerging AI engineering techniques to automate
  software analysis, code transformation, validation, and optimization."
- "Establish validation strategies and quality frameworks to ensure
  transformed systems maintain functional correctness and reproducibility."
- Must: 5+ years distributed computing (Spark/PySpark), "Python or Scala,"
  legacy modernization, performance measurement, workflow orchestration.
- Nice: scientific computing/bioinformatics, HPC/GPU, AI agents, compiler
  technology, static analysis, source-to-source translation, Airflow /
  Nextflow.

**Staff Software Engineer (NodeJS, Python)**: describes the legacy stack
- 5+ years Node.js, 3+ years Python; RESTful/microservices architectures.
- AWS: S3, EC2, Auto Scaling Groups, SQS, VPC, security groups; Redis /
  ElastiCache; MongoDB performance and query optimization.
- Jest, Mocha, Chai; TDD; Linux.
- Nice: AI-assisted tools (GitHub Copilot, Claude).

**Senior Data Engineer**
- "Lead the gradual transition from an ad-hoc, 'analytics-first' workflow to
  one with rigorous data engineering standards, including version control,
  CI/CD, automated testing, and data governance."
- Tools: Python, advanced SQL, Spark, ClickHouse, Trino, Airflow, Nextflow.

**Senior Full Stack Engineer** (closed posting): Python, React/Next.js, AWS;
charting libraries (ECharts, D3, Deck.GL); Spark nice-to-have.

No job post names a backend web framework (searched for FastAPI, Django,
Flask, Express, NestJS). "Scala" appears only in the AI Transformation post.

---

## 7. Recruiter conversation

- **[Recruiter]** Legacy: Node.js, AWS, lots of data, distributed, clunky,
  50+ microservices.
- **[Recruiter]** New platform: AI integration, PySpark, distributed
  computing; backend Python, Scala; cloud AWS.
- **[Recruiter]** Assessment: AWS, MongoDB, backend.
- **[Recruiter]** Rounds: (1) technical with lead: questions, algorithms,
  LeetCode; (2) and (3) culture fit with CEO; (4) online with US team.

---

## 8. Architecture picture

### Legacy (evidence)

- Node.js microservices (50+, per recruiter) on AWS: EC2, Auto Scaling, S3,
  SQS, VPC; Redis / ElastiCache; MongoDB.
- Single-node analytical applications that "struggle" with today's data
  sizes (job posts).

### Target (evidence)

- Python backend; Spark-based cloud platform (PySpark, Scala); AWS.
- AI integration: inXighter in the product; AI agents to automate code
  migration and validation.
- Data layer: Parquet-based single-cell data (blog), Daft + Ray in
  PROTOplast; orchestration with Airflow / Nextflow (job posts).
- Deployable to SaaS, customer cloud, on-prem, DNAnexus.

### [INFERENCE]

- The rebuild likely powers protoXell and similar client platforms.
- Node.js probably stays in the API layer during migration; Python takes data,
  Spark, AI.
- Scala likely used for speed-critical Spark functions, platform plumbing
  (e.g. custom readers for scientific formats), and possibly as a target
  language for converted tools.
- The 3-day dataset turnaround requires automated ingestion and
  harmonization pipelines.

---

## 9. Problems

### Technical, from their own sources

1. Single-machine tools crash or crawl on modern single-cell datasets
   (memory, single-machine assumptions, file-backed limits).
2. Conversion to scalable formats is slow (hours per file) and fragile.
3. Perturbation effects are a spectrum, and conclusions depend on the chosen
   metric.
4. Rigorous comparison metrics hit a scalability wall (Wasserstein ~5,000×
   slower than Euclidean).
5. Batch effects distort results, more so when combining studies.
6. Legacy Node.js microservices need replacing with a Python/Spark platform.
7. Migrated code must be proven functionally correct and reproducible.
8. Data engineering is "ad-hoc, analytics-first," lacking CI/CD, tests,
   governance.
9. Distributed data loading has needed correctness fixes (dropped data,
   uneven batches, inconsistent order).

### Business, from their customer-facing pages

1. Customers wait weeks to months for answers and need programmers.
2. Promise of new datasets within 3 days requires full automation.
3. Customers need audit trails, lineage, compliance (HIPAA, GxP).
4. Must run anywhere: multiple clouds, DNAnexus, on-prem.
5. AI must never invent results.

### Not found

No public evidence on finances, churn, outages, customer complaints, or
internal friction.

### [INFERENCE] Future risks

1. All-pairs comparison cost grows with the square of the catalog size.
2. Old and new systems will disagree during the migration without automated
   parity checks.
3. AI explanations aren't reproducible across model versions without run
   records.
4. Private customer data in a shared catalog raises isolation risk.
5. A small team split between consulting and product.
6. Data producers (Tahoe, Xaira, Arc) could ship competing tools; free
   open-source kits exist. The moat is curation speed plus trustworthy AI.

---

## 10. How miniXell maps to this

| Their problem | miniXell answer |
|---|---|
| Single-node tools struggle with data size | Legacy reference vs PySpark; scale benchmark (time and memory) |
| Migrated code must stay correct and reproducible | Parity test in CI; deterministic cell sampling |
| Metric choice and comparison cost | Euclidean + E-distance (their winners); precomputed top-20 matches |
| Python vs Scala inside Spark | Three-way E-distance benchmark: plain Python, grouped pandas, Scala |
| Ad-hoc data workflows | CI with lint, tests, parity as a merge gate |
| AI must not invent results | Claude explanations grounded in signature + gene descriptions; guardrail |

---

## 11. Open questions for the interviews

1. Which posting is my role: Senior Software Engineer (Python, Cloud,
   Distributed Computing) or Senior Software AI Transformation Engineer?
2. In the apps being migrated, what breaks first: memory, runtime, or cloud
   cost?
3. What framework do new Python services use, and which APIs stay on Node?
4. Where does Scala sit: custom Spark functions, platform libraries, or the
   converted apps themselves?
5. Does the 50-microservice platform power protoXell, client platforms, or
   both?

---

## Sources

- https://dataxight.com/
- https://dataxight.com/about-us
- https://dataxight.com/products/protoxell
- https://dataxight.com/products/protoplast
- https://dataxight.com/services/data
- https://dataxight.com/services/software-ai-ml
- https://dataxight.com/careers
- https://dataxight.com/careers/senior-software-engineer-python-cloud-distributed-computing-901611546
- https://dataxight.com/careers/senior-software-ai-transformation-engineer-distributed-computing-909083534
- https://dataxight.com/careers/staff-software-engineer-node-js-python-cloud-887226369
- https://dataxight.com/careers/senior-data-engineer-1004601349
- https://www.foundit.id/job/senior-full-stack-engineer-dataxight-ho-chi-minh-65598539
- https://dataxight.com/blogs/democratizing-scalable-single-cell-rna-analyses
- https://dataxight.com/blogs/perturbation-effect-is-not-an-on-off-switch
- https://dataxight.com/blogs/comparing-perturbations-e-distance-and-euclidean-distance-are-your-best-allies
- https://dataxight.com/blogs/looking-at-batch-effect-through-scrna-seq-data
- https://www.prnewswire.com/news-releases/dataxight-launches-protoxell-to-unlock-mechanistic-insight-from-large-scale-perturbation-data-302770979.html
- https://github.com/dataxight
- https://github.com/dataxight/protoplast
- https://pypi.org/user/michael-dataxight/
- https://www.crunchbase.com/organization/dataxight
- https://itviec.com/companies/dataxight
