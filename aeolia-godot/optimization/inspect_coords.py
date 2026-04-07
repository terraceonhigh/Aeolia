import json

d = json.load(open('/Users/terrace/Labs/Aeolia/aeolia-godot/optimization/worlds/seed_17.json'))

print('=== archs[0] keys:', list(d['archs'][0].keys()))
print('=== substrate[0] keys:', list(d['substrate'][0].keys()))
print('=== states[0] keys:', list(d['states'][0].keys()))

# Check all archs for lon field
arch_keys = set()
for a in d['archs']:
    arch_keys.update(a.keys())
print('\n=== all arch keys across all archs:', sorted(arch_keys))

sub_keys = set()
for s in d['substrate']:
    sub_keys.update(s.keys())
print('=== all substrate keys across all archs:', sorted(sub_keys))

state_keys = set()
for s in d['states']:
    state_keys.update(s.keys())
print('=== all state keys across all archs:', sorted(state_keys))

# Count factions
factions = {}
for s in d['states']:
    f = s.get('faction', 'unknown')
    factions[f] = factions.get(f, 0) + 1
print('\n=== faction counts:', factions)

# Check reach_arch / lattice_arch meaning
print('\n=== reach_arch value:', d['reach_arch'])
print('=== lattice_arch value:', d['lattice_arch'])
print('=== state at reach_arch index:', d['states'][d['reach_arch']])
print('=== state at lattice_arch index:', d['states'][d['lattice_arch']])

# Check names
print('\n=== names type:', type(d['names']).__name__)
if isinstance(d['names'], list):
    print('=== names[0]:', d['names'][0])
elif isinstance(d['names'], dict):
    print('=== names keys (first 3):', list(d['names'].keys())[:3])
