from __future__ import annotations

import pandas as pd


def _evidence(row, role: str) -> str:
    if role == "coordinator":
        return f"Coordination hypothesis: seed with maximal seed connectivity ({row.counterparty_count} counterparties); incoming flow is incomplete."
    if role == "consolidator":
        return f"Receives from {row.n_senders} senders; observed incoming flow exceeds outgoing flow."
    if role == "distributor":
        return f"Distribution hypothesis: sends to {row.n_receivers} receivers; outgoing flow {row.out_amount:,.0f} KZT."
    if role == "transit":
        return f"Observed pass-through ratio is {row.pass_through_ratio:.2f}; has incoming and outgoing flow."
    if role == "terminal":
        return f"Terminal hypothesis: received {row.in_amount:,.0f} KZT with no observed outgoing edge; external flows and balances unknown."
    if row.is_depth4_boundary:
        return "No outgoing edge, but depth 4 is the graph boundary; terminal status is unknown."
    if row.counterparty_count == 0:
        return "No observed connections; account retained in the graph. No evidence of funds being retained."
    if row.is_seed:
        return "Seed account with incomplete incoming flow; no balance or pass-through role inferred."
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
        if row.is_depth4_boundary or row.counterparty_count == 0:
            role = "peripheral"
        elif row.is_seed and row.counterparty_count == max_seed_connectivity and row.counterparty_count > 0:
            role = "coordinator"
        elif not row.is_seed and row.n_senders >= 2 and row.in_amount > row.out_amount:
            role = "consolidator"
        elif row.n_receivers >= 3 and (row.is_seed or row.out_amount > row.in_amount):
            role = "distributor"
        elif not row.is_seed and row.in_amount > 0 and row.out_amount > 0 and 0.8 <= row.pass_through_ratio <= 1.2:
            role = "transit"
        elif not row.is_seed and row.in_amount > 0 and row.out_degree == 0:
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
