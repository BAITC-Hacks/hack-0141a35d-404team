from __future__ import annotations

import numpy as np
import pandas as pd


def assign_roles(metrics: pd.DataFrame) -> pd.DataFrame:
    out = metrics.copy(); roles = []; scores = []; evidence = []
    central_threshold = float(out["centrality_norm"].quantile(0.90))
    for row in out.itertuples():
        role, score, reason = "peripheral", 0.15, "Limited observed connectivity; no stronger structural role signal."
        if (row.is_seed or row.centrality_norm >= central_threshold) and row.counterparty_norm >= 0.35:
            role = "coordinator"; score = 0.55 * row.centrality_norm + 0.25 * row.counterparty_norm + 0.20 * float(row.is_seed)
            reason = f"Centrality {row.centrality_norm:.2f}; {row.n_senders + row.n_receivers} counterparties"
        elif row.n_senders >= 2 and row.in_amount > row.out_amount * 1.25:
            role = "consolidator"; score = 0.55 * row.in_amount_norm + 0.30 * min(row.n_senders / 10, 1) + 0.15 * row.retention_ratio
            reason = f"Receives from {row.n_senders} senders; retains {row.retention_ratio:.0%} of observed flow"
        elif row.n_receivers >= 3 and row.out_amount > row.in_amount * 0.50:
            role = "distributor"; score = 0.55 * row.out_amount_norm + 0.30 * min(row.n_receivers / 15, 1) + 0.15 * row.counterparty_norm
            reason = f"Distributes to {row.n_receivers} receivers; outgoing flow {row.out_amount:,.0f} KZT"
        elif row.in_amount > 0 and row.out_amount > 0 and 0.70 <= row.pass_through_ratio <= 1.30:
            role = "transit"; score = 0.60 * (1 - min(abs(row.pass_through_ratio - 1.0) / 0.30, 1)) + 0.40 * row.counterparty_norm
            reason = f"Pass-through ratio {row.pass_through_ratio:.2f}; {row.n_senders} in / {row.n_receivers} out counterparties"
        elif row.out_degree == 0 and not row.is_depth4_boundary:
            role = "terminal"; score = 0.55 + 0.45 * row.in_amount_norm
            reason = f"No observed outgoing edges; receives {row.in_amount:,.0f} KZT"
        elif row.is_depth4_boundary:
            reason = "No outgoing edge, but node is at depth 4; terminal status is obscured by graph boundary."
        roles.append(role); scores.append(float(np.clip(score, 0, 1))); evidence.append(reason[:200])
    out["role"], out["role_score"], out["evidence"] = roles, scores, evidence
    role_factor = out["role"].map({"coordinator": 1.0, "consolidator": .9, "distributor": .85, "transit": .75, "terminal": .55, "peripheral": .2})
    out["priority_score"] = (0.30 * out["centrality_norm"] + 0.20 * out["total_flow_norm"] + 0.15 * out["counterparty_norm"] + 0.20 * role_factor + 0.15 * out["in_amount_norm"]).clip(0, 1)
    out["priority_score"] *= np.where(out["is_depth4_boundary"], 0.85, 1.0)
    return out

