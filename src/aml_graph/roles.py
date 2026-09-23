from __future__ import annotations

import pandas as pd


def _evidence(row, role: str) -> str:
    if role == "coordinator":
        return f"Seed with the highest observed connectivity among seed accounts: {row.counterparty_count} counterparties."
    if role == "consolidator":
        return f"Receives from {row.n_senders} senders; observed incoming flow exceeds outgoing flow."
    if role == "distributor":
        return f"Sends to {row.n_receivers} receivers; observed outgoing flow exceeds incoming flow."
    if role == "transit":
        return f"Observed pass-through ratio is {row.pass_through_ratio:.2f}; has incoming and outgoing flow."
    if role == "terminal":
        return f"No observed outgoing edge; receives {row.in_amount:,.0f} KZT."
    if row.is_depth4_boundary:
        return "No outgoing edge, but depth 4 is the graph boundary; terminal status is unknown."
    return "No required role rule matched from the observed graph structure."


def assign_roles(metrics: pd.DataFrame) -> pd.DataFrame:
    """Assign roles using only direct graph facts and documented case rules."""
    out = metrics.copy()
    seed_rows = out[out["is_seed"]]
    max_seed_connectivity = seed_rows["counterparty_count"].max() if not seed_rows.empty else -1
    roles: list[str] = []
    scores: list[float] = []
    evidence: list[str] = []
    for row in out.itertuples():
        if row.is_seed and row.counterparty_count == max_seed_connectivity and row.counterparty_count > 0:
            role = "coordinator"
        elif row.n_senders >= 2 and row.in_amount > row.out_amount:
            role = "consolidator"
        elif row.n_receivers >= 3 and row.out_amount > row.in_amount:
            role = "distributor"
        elif row.in_amount > 0 and row.out_amount > 0 and 0.8 <= row.pass_through_ratio <= 1.2:
            role = "transit"
        elif row.out_degree == 0 and not row.is_depth4_boundary:
            role = "terminal"
        else:
            role = "peripheral"
        roles.append(role)
        scores.append(1.0 if role != "peripheral" else 0.0)
        evidence.append(_evidence(row, role)[:200])

    out["role"] = roles
    out["role_score"] = scores
    out["evidence"] = evidence
    out["priority_score"] = out["total_flow"].rank(method="min", pct=True).round(6)
    return out
