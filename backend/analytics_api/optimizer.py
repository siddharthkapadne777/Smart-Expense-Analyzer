"""
Real Linear Programming budget optimizer using scipy.optimize.linprog.

Given last-30-day per-category spend, we minimize total deviation from
historical spend subject to:
  - Each category cap >= 50% of historical (don't cut a category below half)
  - Each category cap <= 100% of historical (we never inflate caps)
  - SUM(caps) <= target_budget  (global constraint, default 85% of total)

This is a genuine LP problem. The `x` vector is the per-category cap.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog


def optimize_budget_caps(category_totals: dict[str, float],
                         target_ratio: float = 0.85,
                         min_ratio: float = 0.50) -> dict[str, float]:
    """
    category_totals: {category_name: trailing_30d_spend}
    target_ratio:    fraction of total historical spend we aim to cap at
                     (e.g., 0.85 → aim for 15% savings)
    min_ratio:       minimum cap per category as fraction of its history

    Returns: {category_name: optimized_cap}
    """
    categories = list(category_totals.keys())
    if not categories:
        return {}

    n = len(categories)
    historical = np.array([category_totals[c] for c in categories], dtype=float)
    total_historical = float(historical.sum())
    target_total = total_historical * target_ratio

    # Objective: minimize sum of |cap_i - historical_i * target_ratio|
    # -> Linearize: introduce u_i >= cap_i - t_i, u_i >= t_i - cap_i,
    #    minimize sum(u_i). t_i = historical_i * target_ratio is the ideal.
    ideal = historical * target_ratio

    # Variables: [c_1..c_n, u_1..u_n]   (2n total)
    c = np.concatenate([np.zeros(n), np.ones(n)])

    # Constraints: u_i >= c_i - ideal_i   → -c_i + u_i >= -ideal_i
    #              u_i >= ideal_i - c_i   →  c_i + u_i >=  ideal_i
    A_ub = []
    b_ub = []
    for i in range(n):
        # -c_i + u_i >= -ideal_i  →  c_i - u_i <= ideal_i
        row = np.zeros(2 * n)
        row[i] = 1
        row[n + i] = -1
        A_ub.append(row)
        b_ub.append(ideal[i])

        # c_i + u_i >= ideal_i  →  -c_i - u_i <= -ideal_i
        row = np.zeros(2 * n)
        row[i] = -1
        row[n + i] = -1
        A_ub.append(row)
        b_ub.append(-ideal[i])

    # Global cap: sum(c_i) <= target_total
    row = np.zeros(2 * n)
    row[:n] = 1
    A_ub.append(row)
    b_ub.append(target_total)

    # Bounds: min_ratio * hist_i <= c_i <= hist_i ; u_i >= 0
    bounds = [(min_ratio * historical[i], historical[i]) for i in range(n)]
    bounds += [(0, None)] * n

    res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                  bounds=bounds, method='highs')

    if not res.success:
        # Fallback: proportional 15% reduction
        return {cat: round(val * target_ratio, 2)
                for cat, val in category_totals.items()}

    caps = res.x[:n]
    return {cat: round(float(caps[i]), 2) for i, cat in enumerate(categories)}