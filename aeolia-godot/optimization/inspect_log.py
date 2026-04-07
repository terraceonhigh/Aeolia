import json

d = json.load(open('/Users/terrace/Labs/Aeolia/aeolia-godot/optimization/worlds/seed_17.json'))
log = d['log']
print('log type:', type(log).__name__)
if isinstance(log, list):
    print('log len:', len(log))
    if len(log) > 0:
        print('log[0]:', json.dumps(log[0], indent=2)[:500])
elif isinstance(log, dict):
    print('log keys:', list(log.keys()))
    for k, v in list(log.items())[:3]:
        print(f'  log[{k!r}]:', json.dumps(v, indent=2)[:300])

# Also check plateau_edges
pe = d['plateau_edges']
print('\nplateau_edges type:', type(pe).__name__, 'len:', len(pe) if hasattr(pe, '__len__') else 'N/A')
if isinstance(pe, list) and len(pe) > 0:
    print('plateau_edges[0]:', pe[0])
