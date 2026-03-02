"""Hypothesis tests for Phase 1 results (H1, H4).

These tests operate on already-generated Phase 1 outputs in data/processed/:
- restaurant_projection_nodes.csv  (betweenness, k_core, etc.)
- temporal_growth.csv             (monthly cumulative reviews)
- hype_events.csv                 (hype months)

They are intentionally lightweight and rely only on pandas + optional SciPy.
Run directly with:

    python -m pipeline.hypothesis_tests

or let pipeline.run call run_hypothesis_tests() after Phase 1.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import pandas as pd

from pipeline.config import DATA_PROCESSED, ensure_dirs


def _try_import_scipy() -> Any:
  """Return scipy.stats module if available, else None."""
  try:
    from scipy import stats  # type: ignore[import]

    return stats
  except Exception:
    return None


def test_h1_betweenness_hype(
  nodes: pd.DataFrame,
  growth: pd.DataFrame,
  hype: pd.DataFrame,
) -> Dict[str, Any]:
  """H1: High betweenness centrality → more likely to become hype.

  We perform a simple high-vs-low betweenness comparison on the probability
  of ever having a hype event. Where SciPy is available, we also run a
  chi-square test on the 2x2 contingency table.
  """
  df_nodes = nodes.copy()
  df_hype = hype.copy()

  # Flag restaurants that ever had at least one hype month
  hype_any = (
    df_hype.groupby("business_id")
    .size()
    .reset_index(name="n_hype_months")
  )
  hype_any["hype_any"] = 1

  merged = df_nodes.merge(
    hype_any[["business_id", "hype_any"]],
    left_on="id",
    right_on="business_id",
    how="left",
  )
  merged["hype_any"] = merged["hype_any"].fillna(0).astype(int)

  # Define high-betweenness group as top 10%
  if "betweenness" not in merged.columns:
    return {
      "ok": False,
      "reason": "betweenness column missing from restaurant_projection_nodes.csv",
    }
  q90 = merged["betweenness"].quantile(0.9)
  merged["high_betweenness"] = (merged["betweenness"] >= q90).astype(int)

  # Contingency table
  ct = pd.crosstab(merged["high_betweenness"], merged["hype_any"])
  # Ensure full 2x2 presence
  for col in [0, 1]:
    if col not in ct.columns:
      ct[col] = 0
  ct = ct[[0, 1]].sort_index()

  high_total = int(ct.loc[1].sum()) if 1 in ct.index else 0
  low_total = int(ct.loc[0].sum()) if 0 in ct.index else 0
  high_hype = int(ct.loc[1, 1]) if (1 in ct.index) else 0
  low_hype = int(ct.loc[0, 1]) if (0 in ct.index) else 0

  rate_high = high_hype / high_total if high_total > 0 else 0.0
  rate_low = low_hype / low_total if low_total > 0 else 0.0

  p_value = None
  chi2 = None
  stats = _try_import_scipy()
  if stats is not None and ct.shape == (2, 2):
    try:
      chi2_val, p, _, _ = stats.chi2_contingency(ct.values)
      chi2 = float(chi2_val)
      p_value = float(p)
    except Exception:
      chi2 = None
      p_value = None

  return {
    "ok": True,
    "high_threshold_q90": float(q90),
    "n_restaurants": int(len(merged)),
    "n_high_betweenness": int((merged["high_betweenness"] == 1).sum()),
    "n_low_betweenness": int((merged["high_betweenness"] == 0).sum()),
    "high_hype_any": high_hype,
    "low_hype_any": low_hype,
    "rate_high": rate_high,
    "rate_low": rate_low,
    "rate_ratio_high_over_low": (rate_high / rate_low) if rate_low > 0 else None,
    "chi2": chi2,
    "p_value": p_value,
    "contingency_table": {
      "rows": ["low_betweenness", "high_betweenness"],
      "cols": ["no_hype", "hype_any"],
      "values": ct.values.tolist(),
    },
  }


def test_h2_bipartite_vs_projection(
  nodes: pd.DataFrame,
  proj_edges: pd.DataFrame,
  reviews: pd.DataFrame,
) -> Dict[str, Any]:
  """H2: Bipartite network reveals more cross-cluster connections than projection.

  We compare cross-community structure in two views:
  - Restaurant projection: edges between restaurants with different community_id.
  - Bipartite: reviewers that span multiple restaurant communities and the
    resulting community–community pairs implied by their activity.
  """
  df_nodes = nodes.copy()
  df_proj = proj_edges.copy()

  if "community_id" not in df_nodes.columns:
    return {
      "ok": False,
      "reason": "community_id column missing from restaurant_projection_nodes.csv",
    }

  # Map restaurant -> community
  comm_map = df_nodes.set_index("id")["community_id"].to_dict()

  # Projection: cross-community share and community-pair coverage
  df_proj["comm_s"] = df_proj["source"].map(comm_map)
  df_proj["comm_t"] = df_proj["target"].map(comm_map)
  df_proj = df_proj.dropna(subset=["comm_s", "comm_t"])
  df_proj["comm_s"] = df_proj["comm_s"].astype(int)
  df_proj["comm_t"] = df_proj["comm_t"].astype(int)

  df_proj["is_cross"] = df_proj["comm_s"] != df_proj["comm_t"]
  n_edges_total = int(len(df_proj))
  n_edges_cross = int(df_proj["is_cross"].sum())
  share_cross_proj = n_edges_cross / n_edges_total if n_edges_total > 0 else 0.0

  proj_pairs: set[Tuple[int, int]] = set()
  for _, row in df_proj[df_proj["is_cross"]][["comm_s", "comm_t"]].iterrows():
    a, b = int(row["comm_s"]), int(row["comm_t"])
    if a == b:
      continue
    if a > b:
      a, b = b, a
    proj_pairs.add((a, b))

  # Bipartite: reviewers spanning multiple restaurant communities
  # Use full city_reviews to attach restaurant communities to reviewer activity.
  df_bi = reviews.copy()
  if not {"user_id", "business_id"}.issubset(df_bi.columns):
    return {
      "ok": False,
      "reason": "city_reviews.csv missing user_id or business_id columns",
    }
  df_bi["community_id"] = df_bi["business_id"].map(comm_map)
  df_bi = df_bi.dropna(subset=["community_id"])
  df_bi["community_id"] = df_bi["community_id"].astype(int)

  # For each reviewer, set of communities they interact with
  user_comms = (
    df_bi.groupby("user_id")["community_id"]
    .agg(lambda s: sorted(set(int(x) for x in s)))
    .reset_index(name="communities")
  )
  user_comms["n_communities"] = user_comms["communities"].apply(len)
  n_users_total = int(len(user_comms))
  n_users_multi = int((user_comms["n_communities"] >= 2).sum())

  bip_pairs: set[Tuple[int, int]] = set()
  # Generate unordered community pairs per multi-community reviewer
  for comms in user_comms[user_comms["n_communities"] >= 2]["communities"]:
    for a, b in combinations(comms, 2):
      if a == b:
        continue
      if a > b:
        a, b = b, a
      bip_pairs.add((int(a), int(b)))

  # Overlap between the two representations
  overlap_pairs = proj_pairs & bip_pairs

  return {
    "ok": True,
    "n_projection_edges": n_edges_total,
    "n_projection_cross_edges": n_edges_cross,
    "share_cross_projection": share_cross_proj,
    "n_projection_unique_comm_pairs": len(proj_pairs),
    "n_bipartite_users": n_users_total,
    "n_bipartite_users_multi_community": n_users_multi,
    "share_bipartite_users_multi_community": (n_users_multi / n_users_total) if n_users_total > 0 else 0.0,
    "n_bipartite_unique_comm_pairs": len(bip_pairs),
    "n_comm_pairs_overlap": len(overlap_pairs),
    "projection_pairs_covered_by_bipartite": (
      len(overlap_pairs) / len(proj_pairs) if proj_pairs else 0.0
    ),
    "bipartite_pairs_covered_by_projection": (
      len(overlap_pairs) / len(bip_pairs) if bip_pairs else 0.0
    ),
  }


def _compute_user_visit_sets(
  reviews: pd.DataFrame,
) -> Dict[str, set[Tuple[str, str]]]:
  """Helper: map user_id -> set of (business_id, year_month) visits."""
  df = reviews.copy()
  df["date"] = pd.to_datetime(df["date"], errors="coerce")
  df = df.dropna(subset=["date"])
  df["year_month"] = df["date"].dt.to_period("M").astype(str)

  visits: Dict[str, set[Tuple[str, str]]] = {}
  for _, row in df[["user_id", "business_id", "year_month"]].iterrows():
    uid = str(row["user_id"])
    biz = str(row["business_id"])
    ym = str(row["year_month"])
    visits.setdefault(uid, set()).add((biz, ym))
  return visits


def test_h3_homophily_vs_random(
  reviews: pd.DataFrame,
  friend_edges: pd.DataFrame,
  max_random_pairs: int = 5000,
) -> Dict[str, Any]:
  """H3 (partial): Homophily vs random similarity in time-and-place.

  This test strengthens the existing Jaccard comparison by:
  - Computing friend-pair and random-pair Jaccard distributions on
    (business_id, year_month).
  - Running a two-sample test (if SciPy is available) to quantify how
    different the distributions are.

  It does NOT by itself separate homophily from causal influence, but it is
  a valid statistical test that friends are much more similar than random
  pairs in when/where they review.
  """
  if friend_edges.empty:
    return {
      "ok": False,
      "reason": "friend_edges.csv is empty; cannot build friend pairs.",
    }

  visits = _compute_user_visit_sets(reviews)
  if not visits:
    return {
      "ok": False,
      "reason": "No valid visits after parsing city_reviews.csv.",
    }

  # Friend pairs that have at least some activity
  friend_pairs: list[Tuple[str, str]] = []
  for _, row in friend_edges[["source", "target"]].iterrows():
    u = str(row["source"])
    v = str(row["target"])
    if u in visits and v in visits:
      # Use undirected (u < v) to avoid duplicates
      if u > v:
        u, v = v, u
      friend_pairs.append((u, v))

  friend_pairs = list(dict.fromkeys(friend_pairs))  # de-dup
  if not friend_pairs:
    return {
      "ok": False,
      "reason": "No friend pairs with visits in city_reviews.csv.",
    }

  def jaccard(u: str, v: str) -> float:
    a = visits.get(u, set())
    b = visits.get(v, set())
    if not a or not b:
      return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0

  friend_jaccards = [jaccard(u, v) for u, v in friend_pairs]
  friend_series = pd.Series(friend_jaccards, dtype="float64")
  friend_mean = float(friend_series.mean()) if not friend_series.empty else 0.0

  # Random pairs from users with at least 2 visits
  user_list = [u for u, s in visits.items() if len(s) >= 2]
  import random

  random.seed(42)
  random_pairs: list[Tuple[str, str]] = []
  seen: set[Tuple[str, str]] = set()
  while len(random_pairs) < max_random_pairs and len(user_list) >= 2:
    u, v = random.sample(user_list, 2)
    if u > v:
      u, v = v, u
    if (u, v) in seen:
      continue
    seen.add((u, v))
    random_pairs.append((u, v))

  random_jaccards = [jaccard(u, v) for u, v in random_pairs]
  random_series = pd.Series(random_jaccards, dtype="float64")
  random_mean = float(random_series.mean()) if not random_series.empty else 0.0

  ratio = (friend_mean / random_mean) if random_mean > 0 else None

  stats = _try_import_scipy()
  p_value = None
  test_stat = None
  test_name = None
  if stats is not None and not friend_series.empty and not random_series.empty:
    try:
      # Welch's t-test (does not assume equal variances)
      t_stat, p = stats.ttest_ind(friend_series, random_series, equal_var=False)
      test_stat = float(t_stat)
      p_value = float(p)
      test_name = "welch_ttest"
    except Exception:
      test_stat = None
      p_value = None
      test_name = None

  return {
    "ok": True,
    "n_friend_pairs": len(friend_pairs),
    "n_random_pairs": len(random_pairs),
    "friend_mean_jaccard": friend_mean,
    "random_mean_jaccard": random_mean,
    "ratio_friend_over_random": ratio,
    "test_name": test_name,
    "test_statistic": test_stat,
    "p_value": p_value,
  }


def test_h4_kcore_growth(
  nodes: pd.DataFrame,
  growth: pd.DataFrame,
) -> Dict[str, Any]:
  """H4: High k-core restaurants experience faster review growth.

  We summarise each restaurant's growth as average monthly cumulative
  reviews and correlate it with k_core. Where SciPy is available, we
  compute a Pearson correlation and p-value.
  """
  df_nodes = nodes.copy()
  df_growth = growth.copy()

  if "k_core" not in df_nodes.columns:
    return {
      "ok": False,
      "reason": "k_core column missing from restaurant_projection_nodes.csv",
    }

  # growth: business_id, year_month, count, cumulative
  if "cumulative" not in df_growth.columns:
    return {
      "ok": False,
      "reason": "cumulative column missing from temporal_growth.csv",
    }

  df_growth = df_growth.sort_values(["business_id", "year_month"])

  def _summarise(group: pd.DataFrame) -> pd.Series:
    group = group.sort_values("year_month")
    months = len(group)
    if months <= 0:
      return pd.Series({"growth_rate": pd.NA, "months_observed": months})
    total_cum = float(group["cumulative"].iloc[-1])
    rate = total_cum / months
    return pd.Series({"growth_rate": rate, "months_observed": months})

  growth_summary = (
    df_growth.groupby("business_id")
    .apply(_summarise)
    .reset_index()
  )

  merged = df_nodes.merge(
    growth_summary[["business_id", "growth_rate", "months_observed"]],
    left_on="id",
    right_on="business_id",
    how="left",
  )
  merged = merged.dropna(subset=["growth_rate", "k_core"])

  n_used = int(len(merged))
  if n_used == 0:
    return {
      "ok": False,
      "reason": "No overlapping restaurants between metrics and temporal growth.",
    }

  stats = _try_import_scipy()
  r = None
  p_value = None
  if stats is not None:
    try:
      r_val, p = stats.pearsonr(merged["k_core"], merged["growth_rate"])
      r = float(r_val)
      p_value = float(p)
    except Exception:
      r = None
      p_value = None

  # Simple descriptive comparison: top vs bottom k_core terciles
  q33 = merged["k_core"].quantile(1 / 3)
  q67 = merged["k_core"].quantile(2 / 3)
  low = merged[merged["k_core"] <= q33]
  high = merged[merged["k_core"] >= q67]
  mean_low = float(low["growth_rate"].mean()) if not low.empty else None
  mean_high = float(high["growth_rate"].mean()) if not high.empty else None

  return {
    "ok": True,
    "n_restaurants_used": n_used,
    "pearson_r_kcore_growth": r,
    "p_value": p_value,
    "kcore_tercile_thresholds": {
      "q33": float(q33),
      "q67": float(q67),
    },
    "mean_growth_low_kcore": mean_low,
    "mean_growth_high_kcore": mean_high,
  }


def run_hypothesis_tests(out_dir: Path | None = None) -> Dict[str, Any]:
  """Run H1 and H4 tests using processed CSVs and write JSON results."""
  out_dir = out_dir or DATA_PROCESSED
  ensure_dirs()

  nodes_path = out_dir / "restaurant_projection_nodes.csv"
  growth_path = out_dir / "temporal_growth.csv"
  hype_path = out_dir / "hype_events.csv"
  proj_edges_path = out_dir / "restaurant_projection_edges.csv"
  reviews_path = out_dir / "city_reviews.csv"
  friend_edges_path = out_dir / "friend_edges.csv"

  required = [nodes_path, growth_path, hype_path]
  if not all(p.exists() for p in required):
    return {
      "ok": False,
      "reason": "Required CSVs not found; run Phase 1 pipeline first.",
      "expected_files": [str(p) for p in required],
    }

  nodes = pd.read_csv(nodes_path)
  growth = pd.read_csv(growth_path)
  hype = pd.read_csv(hype_path)

  h1 = test_h1_betweenness_hype(nodes, growth, hype)
  h4 = test_h4_kcore_growth(nodes, growth)

  # Optional tests that require additional files
  h2: Dict[str, Any] | None = None
  h3: Dict[str, Any] | None = None

  if proj_edges_path.exists() and reviews_path.exists():
    proj = pd.read_csv(proj_edges_path)
    reviews = pd.read_csv(reviews_path)
    h2 = test_h2_bipartite_vs_projection(nodes, proj, reviews)

  if reviews_path.exists() and friend_edges_path.exists():
    # Reuse reviews loaded above if available
    try:
      reviews_df = reviews  # type: ignore[name-defined]
    except NameError:
      reviews_df = pd.read_csv(reviews_path)
    friend_edges = pd.read_csv(friend_edges_path)
    h3 = test_h3_homophily_vs_random(reviews_df, friend_edges)

  results: Dict[str, Any] = {
    "ok": True,
    "h1_betweenness_hype": h1,
    "h4_kcore_growth": h4,
  }
  if h2 is not None:
    results["h2_bipartite_vs_projection"] = h2
  if h3 is not None:
    results["h3_homophily_vs_random"] = h3

  out_file = out_dir / "hypothesis_tests_results.json"
  with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

  print(f"  Wrote {out_file} with H1/H4 test summaries.")
  return results


if __name__ == "__main__":
  run_hypothesis_tests()

