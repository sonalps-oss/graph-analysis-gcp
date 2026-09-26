# Graph Analysis on Google Cloud Storage

Python implementation of graph parsing, descriptive link statistics, iterative PageRank, and closeness centrality for a deterministic 12,000-page synthetic web graph.

**Google Cloud project:** `directed-fabric-508221-d2`  
**Public GCS bucket:** `sonal-graph-2026-sps`  
**Object prefix:** `graph_data/`  
**Repository:** https://github.com/sonalps-oss/graph-analysis-gcp

## Assignment constraints satisfied

- Uses the supplied `generate-content.py` client.
- Generates **12,000 HTML pages**.
- Uses generator argument `-m 327`, which produces an observed maximum of **325 outgoing links** because the supplied generator samples `num_refs` from `1..326` and then writes `num_refs - 1` links.
- Stores the generated pages under `gs://sonal-graph-2026-sps/graph_data/`.
- Bucket is world-readable through `allUsers -> roles/storage.objectViewer`.
- Parses the HTML and constructs the directed graph without NetworkX, NetworkKit, iGraph, graph-tool, or any other graph library.
- Computes average, median, minimum, maximum, and quintile cut points (20%, 40%, 60%, 80%) for incoming and outgoing links.
- Implements iterative PageRank directly from the assignment formula.
- Implements closeness centrality with a custom shortest-path traversal.
- Includes independent unit tests for parsing/statistics, PageRank, and closeness centrality.
- Code is single-threaded; no graph computation is parallelized.
- Runs on a laptop, Google Cloud Shell, and an `e2-medium` VM.

## Repository layout

```text
graph-analysis-gcp/
├── generate-content.py
├── graph_analysis.py
├── requirements.txt
├── tests/
│   └── test_graph_analysis.py
└── results/
    └── cloudshell-local.txt
```

The generated `graph_data/` directory contains 12,000 HTML files and is intentionally excluded from Git because the same deterministic dataset can be regenerated with the supplied client.

## Environment setup

Python 3.11+ is recommended.

```bash
git clone https://github.com/sonalps-oss/graph-analysis-gcp.git
cd graph-analysis-gcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Dependencies are intentionally small:

```text
google-cloud-storage
pytest
```

## Generate the 12,000-page dataset

Run the supplied generator inside a dedicated directory:

```bash
mkdir -p graph_data
cd graph_data
python3 ../generate-content.py -n 12000 -m 327
cd ..
```

Verify the count:

```bash
find graph_data -maxdepth 1 -name '*.html' | wc -l
```

Expected:

```text
12000
```

The generator uses `random.seed(0)`, so the graph is deterministic when the same arguments are used.

## Google Cloud Storage setup

The assignment bucket is:

```text
gs://sonal-graph-2026-sps
```

The dataset is stored under:

```text
gs://sonal-graph-2026-sps/graph_data/
```

A typical upload command is:

```bash
gcloud storage rsync --recursive graph_data gs://sonal-graph-2026-sps/graph_data
```

Verify that the bucket contains 12,000 objects:

```bash
gcloud storage ls gs://sonal-graph-2026-sps/graph_data/ | wc -l
```

Make the objects world-readable:

```bash
gcloud storage buckets add-iam-policy-binding gs://sonal-graph-2026-sps   --member=allUsers   --role=roles/storage.objectViewer
```

Verify the IAM policy:

```bash
gcloud storage buckets get-iam-policy gs://sonal-graph-2026-sps
```

The policy should contain:

```text
- members:
  - allUsers
  role: roles/storage.objectViewer
```

## Running the analysis

`graph_analysis.py` supports two data-source modes.

### 1. Direct GCS mode - assignment/TA verification path

This mode lists the public bucket and downloads every numeric `.html` object itself:

```bash
python3 -u graph_analysis.py   --source gcs   --bucket sonal-graph-2026-sps   --prefix graph_data/
```

Parameters:

- `--source gcs|local`: chooses the input source. Default is `gcs`.
- `--bucket`: GCS bucket name; required for `--source gcs`.
- `--prefix`: object prefix; default `graph_data/`.
- `--local-dir`: local graph directory; default `graph_data`.

### 2. Local/staged mode - reproducible compute benchmark

```bash
python3 -u graph_analysis.py   --source local   --local-dir graph_data
```

This uses the exact same 12,000-file deterministic dataset, but removes per-object GCS network latency from the graph-computation benchmark.

## Tests

Run:

```bash
PYTHONPATH=. python -m pytest -v
```

Observed on Cloud Shell, the VM, and the Mac environment:

```text
test_extract_links              PASSED
test_statistics                 PASSED
test_pagerank_known_graph       PASSED
test_closeness_centrality       PASSED
```

The PageRank test uses a hand-constructed 3-node graph with analytically known PageRank values. The closeness test uses a 4-node bidirectional star where the center must have closeness 1.0. Neither test depends on the generated 12K graph.

## Algorithms

### Link statistics

For each page, outgoing degree is the number of parsed links in that page. Incoming degree is accumulated using a reverse adjacency list. Quintile cut points are calculated using the nearest-rank method at 20%, 40%, 60%, and 80%.

### PageRank

The implementation uses damping factor `0.85` and teleport probability `0.15 / N`:

```text
PR(A) = 0.15/N + 0.85 * sum(PR(T) / C(T))
```

Dangling-node mass is redistributed uniformly. Because normalized PageRank has total mass approximately 1 at every iteration, the implementation uses aggregate PageRank movement as the convergence measure:

```text
sum(abs(PR_new[i] - PR_old[i])) / sum(PR_old) <= 0.005
```

This makes the assignment's 0.5% stopping criterion meaningful rather than stopping immediately simply because the normalized total remains 1.

### Closeness centrality

Closeness is computed from exact directed shortest-path distances using custom bit-set BFS logic. No external graph package is used. A reachability correction is applied for disconnected directed graphs.

## 12K graph results

Graph size:

```text
Pages: 12000
Links: 1940788
```

| Metric | Outgoing | Incoming |
|---|---:|---:|
| Average | 161.732333 | 161.732333 |
| Median | 163 | 162 |
| Minimum | 0 | 115 |
| Maximum | 325 | 233 |
| Q20 | 63 | 151 |
| Q40 | 130 | 159 |
| Q60 | 195 | 165 |
| Q80 | 259 | 172 |

Top 5 PageRank pages:

| Rank | Page | PageRank |
|---:|---|---:|
| 1 | `9970.html` | 0.000185913197 |
| 2 | `4807.html` | 0.000185621893 |
| 3 | `1388.html` | 0.000185295351 |
| 4 | `369.html` | 0.000176459054 |
| 5 | `1685.html` | 0.000166037356 |

PageRank converged in 3 iterations with final reported movement `0.00108137`; the final rank sum was `1.000000000000`.

Best closeness centrality:

```text
Page: 7263.html
Score: 0.504795961296
```

## Execution environments and timing

All three environments use the same deterministic 12K graph and the same single-threaded implementation.

| Environment | Evidence | Graph loading | Statistics | PageRank | Closeness | Total |
|---|---|---:|---:|---:|---:|---:|
| Local MacBook Air | 12K dataset verified; 4 tests passed | **Run locally before submission and record here** | - | - | - | **Timing screenshot not supplied** |
| Google Cloud Shell | local/staged dataset | 3.295495 s | 0.006573 s | 0.376766 s | 60.730870 s | **64.416381 s** |
| GCE `e2-medium` VM | local/staged dataset | 84.260608 s | 0.005310 s | 0.327937 s | 60.665518 s | **145.264828 s** |

The Cloud Shell and VM computational phases are very similar for PageRank and closeness. The VM run is slower overall because graph loading from its local disk took about 84 seconds versus about 3.3 seconds in Cloud Shell; closeness itself took about 60.7 seconds in both environments. The direct GCS path was also tested for bucket listing and access; sequential per-object downloads can be substantially slower and one Cloud Shell attempt encountered an HTTPS read timeout.

## Billing

Google Cloud Billing showed **$0.00 actual spend** for September 1-25, 2026. The service breakdown showed Compute Engine and Cloud Storage at a $0.00 subtotal; the billing account also displayed a small Cloud Run Functions usage amount that was fully offset by savings.

## Cleanup

The assignment VM should be deleted immediately after collecting benchmark results:

```bash
gcloud compute instances delete graph-vm   --zone=us-central1-a   --quiet
```

Verify:

```bash
gcloud compute instances list
```

## AI disclosure

AI assistance was used to help structure the implementation, debug environment/setup issues, review commands, explain PageRank/closeness concepts, and prepare documentation. I reviewed the generated code, ran the program and tests myself, verified the outputs across environments, and understand the main implementation choices: HTML link extraction, adjacency/reverse-adjacency construction, nearest-rank quintiles, iterative PageRank, dangling-node handling, convergence checking, and custom shortest-path closeness computation. I can explain the code without relying on an AI assistant.
