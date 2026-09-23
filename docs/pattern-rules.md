# Node patterns and evidence

These are explicit review heuristics, not labelled detection accuracy, account balances, or proof of criminal activity. They do not alter baseline roles, scores, or CSV schemas.

| Capability | Implemented rule and limit |
|---|---|
| Boundary truncation | Depth ≥4 with no outgoing edges is peripheral/unknown, excluded from terminal/consolidation inference. Missing-data request asks for deeper outgoing tracing. |
| Temporal pass-through | Sort raw transactions by date. Greedily match incoming amounts FIFO to outgoing amounts within 0–48 hours, consuming each matched amount once. Same-day timestamps may lack ordering precision. Matching measures compatibility, not identity of funds. Invalid dates are excluded and counted. |
| Activity bursts | At least three active days; daily transaction count ≥3 times median active-day count and greater than that median. Inactive days are excluded. |
| Synchronous inflows | At least three different senders to the same receiver on a date. Show dates and sender counts. |
| Repeated routes | At least two distinct outgoing events with positive FIFO matches on the same A→B→C sequence (three distinct accounts). Multiple incoming fragments matched to one outgoing transfer count once. Show compatible events, not a proven end-to-end transfer count. Up to 100 global routes and ten per node shown. |
| Return flows | Enumerate directed cycles of length 2–3, deduplicated by rotation. Show minimum edge transaction count. Longer cycles are outside this first implementation. Structural cycles do not imply temporally closed money flow. |
| Repeated amounts | At least three outgoing transactions with the same date, receiver and amount. Label a possible splitting pattern; never infer transactions below the 5,000 KZT extraction threshold. |
| Depth-peer anomaly | Compare observed total flow within each depth. Flag values above Q3 + 1.5×IQR only for groups of at least eight with nonzero IQR. Display peer count and calculated threshold. No extra weighted risk score. |
| Resilience | Copy observed directed graph; remove top N by existing priority, role score and gid tie-break, N=0–100. Compare nodes, edges, weak-component count, largest component and isolates. Original graph remains intact. This is topology, not a prediction of adaptation. |
| Node card | Automatic bottom-corner card on selection: role/evidence, incoming/outgoing amounts, sender/receiver counts, temporal signals, repeated routes/cycles, anomaly evidence and missing-data requests; downloadable text card and clickable gids. No separate Investigation panel. |
| Completeness | Explicit requests for external flows, subthreshold transactions, balances, customer context/payment purposes, complete seed inflows and deeper boundary tracing. No fabricated customer attributes. |

All thresholds above are documented implementation choices. The task screenshot lists desired capabilities, not universal detection thresholds. Results depend on the observed July 2026 in-bank sample.
