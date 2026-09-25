import argparse
import math
import os
import re
import time

from google.cloud import storage


LINK_PATTERN = re.compile(r'HREF="(\d+)\.html"')


# ============================================================
# HTML PARSING
# ============================================================

def extract_links(content):
    """
    Extract numeric page IDs from hyperlinks of the form:

        HREF="123.html"

    Duplicate links and self-links are intentionally preserved.
    """
    return [int(x) for x in LINK_PATTERN.findall(content)]


def page_id_from_name(name):
    """
    Convert a name such as:

        graph_data/123.html
        123.html

    into:

        123
    """

    filename = os.path.basename(name)

    if not filename.endswith(".html"):
        return None

    stem = filename[:-5]

    if not stem.isdigit():
        return None

    return int(stem)


# ============================================================
# BUILD GRAPH
# ============================================================

def build_reverse_adjacency(adjacency):

    n = len(adjacency)

    reverse_adjacency = [[] for _ in range(n)]

    for source in range(n):

        for target in adjacency[source]:

            if target < 0 or target >= n:
                raise ValueError(
                    f"Invalid link from page {source} "
                    f"to page {target}"
                )

            reverse_adjacency[target].append(source)

    return reverse_adjacency


# ============================================================
# LOCAL LOADING
# ============================================================

def load_graph_local(directory):
    """
    Read graph files already stored on the local filesystem.

    This is useful for development and performance testing after
    the GCS objects have already been downloaded/generated.
    """

    print(
        f"Reading local graph directory: {directory}",
        flush=True
    )

    files = []

    for filename in os.listdir(directory):

        page_id = page_id_from_name(filename)

        if page_id is not None:
            files.append((page_id, filename))

    if not files:
        raise RuntimeError(
            f"No HTML files found in {directory}"
        )

    files.sort()

    page_ids = [page_id for page_id, _ in files]

    expected = list(range(len(page_ids)))

    if page_ids != expected:
        raise RuntimeError(
            "Expected files numbered consecutively "
            "from 0.html through N-1.html"
        )

    n = len(files)

    print(f"Found {n} pages.", flush=True)

    adjacency = [[] for _ in range(n)]

    for count, (page_id, filename) in enumerate(
        files,
        start=1
    ):

        path = os.path.join(directory, filename)

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:
            content = f.read()

        links = extract_links(content)

        adjacency[page_id] = links

        if count % 500 == 0:
            print(
                f"Read {count}/{n} local pages",
                flush=True
            )

    reverse_adjacency = build_reverse_adjacency(
        adjacency
    )

    return adjacency, reverse_adjacency


# ============================================================
# GCS LOADING
# ============================================================

def load_graph(bucket_name, prefix="graph_data/"):
    """
    Read every HTML page directly from a public Google Cloud
    Storage bucket.

    This is the assignment-compliant GCS execution path.

    The bucket is accessed anonymously because the assignment
    requires it to be world-readable.
    """

    print(
        f"Opening bucket: {bucket_name}",
        flush=True
    )

    print(
        f"Prefix: {prefix}",
        flush=True
    )

    client = storage.Client.create_anonymous_client()

    bucket = client.bucket(bucket_name)

    print(
        "Listing objects in bucket...",
        flush=True
    )

    blobs = []

    for blob in client.list_blobs(
        bucket,
        prefix=prefix
    ):

        page_id = page_id_from_name(blob.name)

        if page_id is not None:
            blobs.append(
                (page_id, blob)
            )

    if not blobs:
        raise RuntimeError(
            f"No HTML files found under "
            f"gs://{bucket_name}/{prefix}"
        )

    blobs.sort(
        key=lambda item: item[0]
    )

    page_ids = [
        page_id
        for page_id, _ in blobs
    ]

    expected = list(
        range(len(page_ids))
    )

    if page_ids != expected:
        raise RuntimeError(
            "Expected bucket files numbered "
            "0.html through N-1.html"
        )

    n = len(blobs)

    print(
        f"Found {n} pages.",
        flush=True
    )

    adjacency = [
        [] for _ in range(n)
    ]

    for count, (page_id, blob) in enumerate(
        blobs,
        start=1
    ):

        try:

            content = blob.download_as_text(
                timeout=30
            )

        except Exception as exc:

            print(
                f"\nERROR downloading "
                f"{blob.name}: {exc}",
                flush=True
            )

            raise

        links = extract_links(content)

        adjacency[page_id] = links

        if count % 500 == 0:

            print(
                f"Downloaded "
                f"{count}/{n} pages",
                flush=True
            )

    reverse_adjacency = build_reverse_adjacency(
        adjacency
    )

    return adjacency, reverse_adjacency


# ============================================================
# STATISTICS
# ============================================================

def median(sorted_values):

    n = len(sorted_values)

    if n == 0:
        raise ValueError(
            "Median of empty list"
        )

    middle = n // 2

    if n % 2 == 1:
        return float(
            sorted_values[middle]
        )

    return (
        sorted_values[middle - 1]
        +
        sorted_values[middle]
    ) / 2.0


def nearest_rank_percentile(
    sorted_values,
    fraction
):
    """
    Nearest-rank percentile.

    rank = ceil(p * N)
    """

    n = len(sorted_values)

    if n == 0:
        raise ValueError(
            "Percentile of empty list"
        )

    rank = math.ceil(
        fraction * n
    )

    index = max(
        0,
        rank - 1
    )

    return sorted_values[index]


def calculate_statistics(values):

    if not values:
        raise ValueError(
            "Statistics of empty list"
        )

    ordered = sorted(values)

    return {
        "average":
            sum(ordered) / len(ordered),

        "median":
            median(ordered),

        "minimum":
            ordered[0],

        "maximum":
            ordered[-1],

        "q20":
            nearest_rank_percentile(
                ordered,
                0.20
            ),

        "q40":
            nearest_rank_percentile(
                ordered,
                0.40
            ),

        "q60":
            nearest_rank_percentile(
                ordered,
                0.60
            ),

        "q80":
            nearest_rank_percentile(
                ordered,
                0.80
            ),
    }


def print_statistics(
    title,
    statistics
):

    print()
    print(title)
    print("=" * len(title))

    print(
        f"Average : "
        f"{statistics['average']:.6f}"
    )

    print(
        f"Median  : "
        f"{statistics['median']:.6f}"
    )

    print(
        f"Minimum : "
        f"{statistics['minimum']}"
    )

    print(
        f"Maximum : "
        f"{statistics['maximum']}"
    )

    print(
        f"Q20     : "
        f"{statistics['q20']}"
    )

    print(
        f"Q40     : "
        f"{statistics['q40']}"
    )

    print(
        f"Q60     : "
        f"{statistics['q60']}"
    )

    print(
        f"Q80     : "
        f"{statistics['q80']}"
    )


# ============================================================
# PAGERANK
# ============================================================

def pagerank(
    adjacency,
    damping=0.85,
    tolerance=0.005,
    max_iterations=1000
):
    """
    Iterative PageRank.

    PR(A) =
        0.15/N
        +
        0.85 *
        SUM(PR(T) / C(T))

    Dangling page rank is distributed uniformly across all
    nodes.

    Convergence is reached when total absolute PageRank
    movement is <= 0.5% of the previous total PageRank.
    """

    n = len(adjacency)

    if n == 0:
        return [], 0

    rank = [
        1.0 / n
        for _ in range(n)
    ]

    teleport = (
        1.0 - damping
    ) / n

    for iteration in range(
        1,
        max_iterations + 1
    ):

        new_rank = [
            teleport
            for _ in range(n)
        ]

        # ----------------------------------------
        # Dangling nodes
        # ----------------------------------------

        dangling_mass = 0.0

        for node in range(n):

            if len(adjacency[node]) == 0:
                dangling_mass += rank[node]

        if dangling_mass:

            dangling_share = (
                damping
                *
                dangling_mass
                /
                n
            )

            for node in range(n):
                new_rank[node] += (
                    dangling_share
                )

        # ----------------------------------------
        # Normal edges
        # ----------------------------------------

        for source in range(n):

            outgoing = adjacency[source]

            outdegree = len(outgoing)

            if outdegree == 0:
                continue

            contribution = (
                damping
                *
                rank[source]
                /
                outdegree
            )

            for target in outgoing:

                new_rank[target] += (
                    contribution
                )

        previous_total = sum(rank)

        total_change = sum(
            abs(
                new_rank[i]
                -
                rank[i]
            )
            for i in range(n)
        )

        relative_change = (
            total_change
            /
            previous_total
        )

        print(
            f"PageRank iteration "
            f"{iteration}: "
            f"change="
            f"{relative_change:.8f}",
            flush=True
        )

        rank = new_rank

        if relative_change <= tolerance:

            return (
                rank,
                iteration
            )

    return (
        rank,
        max_iterations
    )


# ============================================================
# CLOSENESS CENTRALITY
# ============================================================

def build_bit_graph(adjacency):
    """
    Build integer bit-set adjacency representations.

    This remains a custom graph implementation and uses no
    graph library.

    Duplicate links do not affect shortest-path distances.
    """

    n = len(adjacency)

    forward = [
        0 for _ in range(n)
    ]

    reverse = [
        0 for _ in range(n)
    ]

    for source in range(n):

        bits = 0

        for target in adjacency[source]:

            bits |= (
                1 << target
            )

            reverse[target] |= (
                1 << source
            )

        forward[source] = bits

    return (
        forward,
        reverse
    )


def _iter_set_bits(bits):

    while bits:

        lowest = (
            bits & -bits
        )

        index = (
            lowest.bit_length()
            -
            1
        )

        yield index

        bits ^= lowest


def closeness_for_node(
    source,
    forward_bits,
    reverse_bits,
    all_nodes_mask
):
    """
    Exact directed shortest-path closeness centrality.

    Standard connected form:

        C(u) =
          (N - 1) /
          SUM distance(u,v)

    For disconnected graphs, a reachability correction is
    applied.
    """

    n = len(
        forward_bits
    )

    if n <= 1:
        return 0.0

    visited = (
        1 << source
    )

    frontier = (
        1 << source
    )

    reachable = 0
    distance_sum = 0
    depth = 0

    while frontier:

        depth += 1

        unvisited = (
            all_nodes_mask
            &
            ~visited
        )

        if not unvisited:
            break

        frontier_count = (
            frontier.bit_count()
        )

        unvisited_count = (
            unvisited.bit_count()
        )

        next_frontier = 0

        # Expand whichever side requires less work.

        if (
            frontier_count
            <=
            unvisited_count
        ):

            candidates = 0

            for node in _iter_set_bits(
                frontier
            ):

                candidates |= (
                    forward_bits[node]
                )

            next_frontier = (
                candidates
                &
                unvisited
            )

        else:

            for target in _iter_set_bits(
                unvisited
            ):

                if (
                    reverse_bits[target]
                    &
                    frontier
                ):

                    next_frontier |= (
                        1 << target
                    )

        if not next_frontier:
            break

        count = (
            next_frontier.bit_count()
        )

        reachable += count

        distance_sum += (
            depth
            *
            count
        )

        visited |= next_frontier

        frontier = next_frontier

    if distance_sum == 0:
        return 0.0

    base = (
        reachable
        /
        distance_sum
    )

    correction = (
        reachable
        /
        (n - 1)
    )

    return (
        base
        *
        correction
    )


def best_closeness_node(
    adjacency
):

    n = len(adjacency)

    (
        forward_bits,
        reverse_bits
    ) = build_bit_graph(
        adjacency
    )

    all_nodes_mask = (
        1 << n
    ) - 1

    best_node = None

    best_score = -1.0

    for node in range(n):

        score = closeness_for_node(
            node,
            forward_bits,
            reverse_bits,
            all_nodes_mask
        )

        if score > best_score:

            best_score = score
            best_node = node

        if (
            (node + 1)
            %
            500
            ==
            0
        ):

            print(
                f"Closeness processed "
                f"{node + 1}/{n} nodes",
                flush=True
            )

    return (
        best_node,
        best_score
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Analyze the directed graph generated "
            "by the supplied HTML generator."
        )
    )

    parser.add_argument(
        "--source",
        choices=[
            "gcs",
            "local"
        ],
        default="gcs",
        help=(
            "Read directly from Google Cloud Storage "
            "or from a local directory."
        )
    )

    parser.add_argument(
        "--bucket",
        help=(
            "Google Cloud Storage bucket name. "
            "Required when --source gcs."
        )
    )

    parser.add_argument(
        "--prefix",
        default="graph_data/",
        help=(
            "GCS object prefix. "
            "Default: graph_data/"
        )
    )

    parser.add_argument(
        "--local-dir",
        default="graph_data",
        help=(
            "Local graph directory. "
            "Default: graph_data"
        )
    )

    args = parser.parse_args()

    total_start = (
        time.perf_counter()
    )

    # ========================================================
    # LOAD GRAPH
    # ========================================================

    load_start = (
        time.perf_counter()
    )

    if args.source == "local":

        adjacency, reverse_adjacency = (
            load_graph_local(
                args.local_dir
            )
        )

    else:

        if not args.bucket:

            parser.error(
                "--bucket is required "
                "when --source gcs"
            )

        adjacency, reverse_adjacency = (
            load_graph(
                args.bucket,
                args.prefix
            )
        )

    load_time = (
        time.perf_counter()
        -
        load_start
    )

    n = len(adjacency)

    total_links = sum(
        len(neighbors)
        for neighbors
        in adjacency
    )

    print()
    print(
        "=============================="
    )
    print("GRAPH")
    print(
        "=============================="
    )

    print(
        f"Pages : {n}"
    )

    print(
        f"Links : {total_links}"
    )

    # ========================================================
    # STATISTICS
    # ========================================================

    stats_start = (
        time.perf_counter()
    )

    outgoing = [
        len(adjacency[node])
        for node in range(n)
    ]

    incoming = [
        len(reverse_adjacency[node])
        for node in range(n)
    ]

    outgoing_statistics = (
        calculate_statistics(
            outgoing
        )
    )

    incoming_statistics = (
        calculate_statistics(
            incoming
        )
    )

    stats_time = (
        time.perf_counter()
        -
        stats_start
    )

    print_statistics(
        "OUTGOING LINK STATISTICS",
        outgoing_statistics
    )

    print_statistics(
        "INCOMING LINK STATISTICS",
        incoming_statistics
    )

    # ========================================================
    # PAGERANK
    # ========================================================

    pagerank_start = (
        time.perf_counter()
    )

    ranks, iterations = pagerank(
        adjacency
    )

    pagerank_time = (
        time.perf_counter()
        -
        pagerank_start
    )

    top_five = sorted(
        range(n),
        key=lambda node: ranks[node],
        reverse=True
    )[:5]

    print()
    print(
        "=============================="
    )
    print(
        "TOP 5 PAGES BY PAGERANK"
    )
    print(
        "=============================="
    )

    for position, node in enumerate(
        top_five,
        start=1
    ):

        print(
            f"{position}. "
            f"{node}.html "
            f"PR="
            f"{ranks[node]:.12f}"
        )

    print()

    print(
        f"PageRank iterations: "
        f"{iterations}"
    )

    print(
        f"PageRank sum: "
        f"{sum(ranks):.12f}"
    )

    # ========================================================
    # CLOSENESS CENTRALITY
    # ========================================================

    closeness_start = (
        time.perf_counter()
    )

    best_node, best_score = (
        best_closeness_node(
            adjacency
        )
    )

    closeness_time = (
        time.perf_counter()
        -
        closeness_start
    )

    print()
    print(
        "=============================="
    )
    print(
        "BEST CLOSENESS CENTRALITY"
    )
    print(
        "=============================="
    )

    print(
        f"Page  : "
        f"{best_node}.html"
    )

    print(
        f"Score : "
        f"{best_score:.12f}"
    )

    # ========================================================
    # TIMINGS
    # ========================================================

    total_time = (
        time.perf_counter()
        -
        total_start
    )

    print()
    print(
        "=============================="
    )
    print("TIMINGS")
    print(
        "=============================="
    )

    print(
        f"Graph loading : "
        f"{load_time:.6f} seconds"
    )

    print(
        f"Statistics    : "
        f"{stats_time:.6f} seconds"
    )

    print(
        f"PageRank      : "
        f"{pagerank_time:.6f} seconds"
    )

    print(
        f"Closeness     : "
        f"{closeness_time:.6f} seconds"
    )

    print(
        f"TOTAL         : "
        f"{total_time:.6f} seconds"
    )


if __name__ == "__main__":
    main()
