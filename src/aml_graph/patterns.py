"""Observed behavioural signals; these never modify the baseline role/priority scores."""
from collections import Counter, defaultdict, deque
import networkx as nx
import pandas as pd

WINDOW = pd.Timedelta(days=2)

def analyze_patterns(graph, transactions, metrics):
    tx = transactions.dropna(subset=['date']).sort_values('date').copy()
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for r in tx.itertuples():
        item = (r.date, int(r.src), int(r.dst), float(r.sum_kzt))
        incoming[int(r.dst)].append(item)
        outgoing[int(r.src)].append(item)
    by_node = {}
    routes = Counter()
    # Pairings represent temporal compatibility, not proven tracing of the same money.
    for r in metrics.itertuples():
        gid = int(r.gid)
        arrivals, departures = incoming[gid], outgoing[gid]
        queue, cursor, matched = deque(), 0, 0.0
        for date, src, dst, amount in departures:
            observed_routes = set()
            while cursor < len(arrivals) and arrivals[cursor][0] <= date:
                a = arrivals[cursor]
                queue.append([a[0], a[1], a[3]])
                cursor += 1
            while queue and date - queue[0][0] > WINDOW:
                queue.popleft()
            remaining = amount
            while queue and remaining > 0:
                a = queue[0]
                portion = min(a[2], remaining)
                if portion > 0:
                    matched += portion
                    if a[1] != dst:
                        observed_routes.add((a[1], gid, dst))
                a[2] -= portion
                remaining -= portion
                if a[2] <= 0:
                    queue.popleft()
            # Count distinct outgoing events, not multiple FIFO fragments of one event.
            routes.update(observed_routes)
        daily = Counter(a[0].date().isoformat() for a in arrivals + departures)
        median = float(pd.Series(list(daily.values()), dtype=float).median()) if daily else 0
        peak = max(daily.values(), default=0)
        senders = defaultdict(set)
        for date, src, _, _ in arrivals:
            senders[date.date().isoformat()].add(src)
        sync = [{'date': day, 'n_senders': len(ids)} for day, ids in sorted(senders.items()) if len(ids) >= 3]
        repeats = Counter((date.date().isoformat(), dst, amount) for date, _, dst, amount in departures)
        split = [{'date': day, 'dst': str(dst), 'amount_kzt': amount, 'count': count}
                 for (day, dst, amount), count in repeats.items() if count >= 3]
        by_node[str(gid)] = {
            'matched_48h_kzt': round(matched, 2), 'active_days': len(daily),
            'peak_day_count': peak, 'median_active_day_count': median,
            'burst_days': [day for day, count in sorted(daily.items()) if len(daily) >= 3 and count >= 3 * median and count > median],
            'synchronous_days': sync[:10], 'repeated_amount_groups': split[:10],
            'signals': [], 'requests': ['external_flows', 'below_threshold', 'balances', 'customer_context'],
        }
        item = by_node[str(gid)]
        if matched > 0: item['signals'].append('temporal_overlap')
        if item['burst_days']: item['signals'].append('activity_burst')
        if sync: item['signals'].append('synchronous_incoming')
        if split: item['signals'].append('repeated_amounts')
        if r.is_depth4_boundary: item['requests'].append('extend_boundary')
        if r.is_seed: item['requests'].append('seed_inflows')
    # Comparison only within observed depth peers. Small/constant groups are not flagged.
    for _, peers in metrics.groupby('depth'):
        q1, q3 = peers.total_flow.quantile([.25, .75])
        threshold = float(q3 + 1.5 * (q3 - q1))
        for r in peers.itertuples():
            item = by_node[str(r.gid)]
            item['depth_peer_count'] = len(peers)
            item['depth_volume_threshold_kzt'] = threshold if len(peers) >= 8 and q3 > q1 else None
            if len(peers) >= 8 and q3 > q1 and r.total_flow > threshold:
                item['signals'].append('depth_volume_outlier')
    route_rows = [{'gids': list(map(str, route)), 'matching_events': count}
                  for route, count in sorted(routes.items(), key=lambda p: (-p[1], p[0])) if count >= 2]
    cycles = set()
    for a, b in graph.edges():
        if graph.has_edge(b, a): cycles.add(tuple(sorted((a, b))))
        for c in graph.successors(b):
            if c != a and c != b and graph.has_edge(c, a):
                seq = (a, b, c)
                cycles.add(min(seq[i:] + seq[:i] for i in range(3)))
    cycle_rows = [{'gids': list(map(str, cycle)), 'min_edge_transactions': min(graph[u][v]['n_tx'] for u, v in zip(cycle, cycle[1:] + cycle[:1]))}
                  for cycle in sorted(cycles)]
    for item in route_rows:
        for gid in set(item['gids']): by_node[gid].setdefault('routes', []).append(item)
    for item in cycle_rows:
        for gid in item['gids']:
            by_node[gid].setdefault('cycles', []).append(item)
            if 'return_cycle' not in by_node[gid]['signals']: by_node[gid]['signals'].append('return_cycle')
    for item in by_node.values():
        item['routes'] = item.get('routes', [])[:10]
        item['cycles'] = item.get('cycles', [])[:10]
    return {'nodes': by_node, 'routes': route_rows[:100], 'cycles': cycle_rows[:100],
            'summary': {'n_repeated_routes': len(route_rows), 'n_cycles_2_3': len(cycle_rows),
                        'n_nodes_with_signals': sum(bool(n['signals']) for n in by_node.values()),
                        'invalid_dates_excluded': int(transactions.date.isna().sum())}}

def resilience(graph, metrics, n):
    ranked = metrics.sort_values(['priority_score', 'role_score', 'gid'], ascending=[False, False, True])
    removed = ranked.head(min(n, len(ranked))).gid.tolist()
    after = graph.copy()
    after.remove_nodes_from(removed)
    def stats(g):
        sizes = [len(c) for c in nx.weakly_connected_components(g)]
        return {'nodes': g.number_of_nodes(), 'edges': g.number_of_edges(), 'components': len(sizes),
                'largest_component': max(sizes, default=0), 'isolated': len(list(nx.isolates(g)))}
    return {'removed_gids': list(map(str, removed)), 'before': stats(graph), 'after': stats(after),
            'interpretation': 'Static observed topology only; no causal or behavioural prediction.'}
