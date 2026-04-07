import json

d = json.load(open('/Users/terrace/Labs/Aeolia/aeolia-godot/optimization/worlds/seed_17.json'))
print('=== Top-level keys:', list(d.keys()))
print('=== reach_arch:', d['reach_arch'])
print('=== lattice_arch:', d['lattice_arch'])
print('=== df_arch:', d['df_arch'])
print('=== seed:', d['seed'])
print('=== n:', d['n'])

archs = d['archs']
print('\n=== archs type:', type(archs).__name__, 'len:', len(archs))
if isinstance(archs, list):
    print('=== archs[0]:', json.dumps(archs[0], indent=2))
elif isinstance(archs, dict):
    k = list(archs.keys())
    print('=== archs keys (first 5):', k[:5])
    print('=== archs[first]:', json.dumps(archs[k[0]], indent=2))

sub = d['substrate']
print('\n=== substrate type:', type(sub).__name__, 'len:', len(sub) if hasattr(sub, '__len__') else 'N/A')
if isinstance(sub, list) and len(sub) > 0:
    print('=== substrate[0]:', json.dumps(sub[0], indent=2))
    print('=== substrate[1]:', json.dumps(sub[1], indent=2))
elif isinstance(sub, dict):
    k = list(sub.keys())
    print('=== substrate keys (first 5):', k[:5])
    print('=== substrate[first]:', json.dumps(sub[k[0]], indent=2))

states = d['states']
print('\n=== states type:', type(states).__name__, 'len:', len(states) if hasattr(states, '__len__') else 'N/A')
if isinstance(states, list) and len(states) > 0:
    print('=== states[0]:', json.dumps(states[0], indent=2))
elif isinstance(states, dict):
    k = list(states.keys())
    print('=== states keys (first 5):', k[:5])
    print('=== states[first]:', json.dumps(states[k[0]], indent=2))
