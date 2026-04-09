// ═══════════════════════════════════════════════════════════
// PolitySelect.jsx — Starting archipelago picker
// Shows a list of archipelagos with substrate info.
// Player clicks one to begin the game.
// ═══════════════════════════════════════════════════════════

import { useState } from 'react';

const STYLES = {
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(10,8,4,0.88)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 10,
  },
  panel: {
    width: 520, maxHeight: '80vh', background: '#0e0a06',
    border: '1px solid #2a1f14', borderRadius: 6,
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
    fontFamily: "'JetBrains Mono','Fira Code',monospace",
    boxShadow: '0 8px 48px rgba(0,0,0,0.8)',
  },
  header: {
    padding: '16px 20px 12px', borderBottom: '1px solid #2a1f14', flexShrink: 0,
  },
  title: {
    fontSize: 14, color: '#d4b896', fontWeight: 700, letterSpacing: '2px',
    textTransform: 'uppercase', marginBottom: 4,
  },
  subtitle: {
    fontSize: 9, color: '#8a7a5a', lineHeight: 1.5,
  },
  list: {
    flex: 1, overflowY: 'auto', padding: '8px 12px',
  },
  item: (selected, hovered) => ({
    padding: '8px 12px', marginBottom: 4, borderRadius: 4, cursor: 'pointer',
    border: `1px solid ${selected ? '#6a5430' : hovered ? '#3a2a1a' : '#1a1408'}`,
    background: selected ? '#1a1408' : hovered ? '#14100a' : '#0e0a06',
    transition: 'all 0.15s',
  }),
  archName: (selected) => ({
    fontSize: 11, fontWeight: 600, color: selected ? '#d4b896' : '#c8a878',
    letterSpacing: '1px',
  }),
  archDetail: {
    fontSize: 8, color: '#8a7a5a', marginTop: 3, lineHeight: 1.6,
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px 12px',
  },
  footer: {
    padding: '12px 20px', borderTop: '1px solid #2a1f14', flexShrink: 0,
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  },
  button: (enabled) => ({
    padding: '8px 20px', fontSize: 10, fontFamily: 'inherit', cursor: enabled ? 'pointer' : 'default',
    background: enabled ? '#1a1408' : '#0a0804', border: `1px solid ${enabled ? '#6a5430' : '#2a1f14'}`,
    color: enabled ? '#d4b896' : '#6a5a3a', letterSpacing: '1.5px', fontWeight: 600,
    borderRadius: 3, textTransform: 'uppercase',
  }),
};

export default function PolitySelect({ archs, substrate, names, onSelect, onHighlight }) {
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);

  const archList = archs.map((arch, i) => {
    const sub = substrate[i];
    const crop = sub?.crops?.primary_crop || 'foraging';
    const yield_ = sub?.crops?.primary_yield?.toFixed(1) || '?';
    const minerals = sub?.minerals || {};
    const mineralStr = [
      minerals.Cu && 'Cu', minerals.Au && 'Au',
      minerals.C > 0 && 'C', minerals.Pu && 'Pu'
    ].filter(Boolean).join(' ') || 'Fe';
    const fishR = (sub?.climate?.fisheries_richness * 100)?.toFixed(0) || '0';
    const peaks = arch.peaks?.length || 0;

    return { i, crop, yield_, mineralStr, fishR, peaks, name: names[i] };
  });

  // Sort by yield descending (good starting positions first)
  archList.sort((a, b) => parseFloat(b.yield_) - parseFloat(a.yield_));

  return (
    <div style={STYLES.overlay}>
      <div style={STYLES.panel}>
        <div style={STYLES.header}>
          <div style={STYLES.title}>Choose Your Archipelago</div>
          <div style={STYLES.subtitle}>
            Select a starting position. Higher crop yield and more peaks mean a stronger start.
            Mineral access unlocks at higher tech levels.
          </div>
        </div>

        <div style={STYLES.list}>
          {archList.map(({ i, crop, yield_, mineralStr, fishR, peaks, name }) => (
            <div key={i}
              style={STYLES.item(selected === i, hovered === i)}
              onClick={() => { setSelected(i); onHighlight?.(i); }}
              onMouseEnter={() => { setHovered(i); onHighlight?.(i); }}
              onMouseLeave={() => setHovered(hovered === i ? null : hovered)}
            >
              <div style={STYLES.archName(selected === i)}>{name}</div>
              <div style={STYLES.archDetail}>
                <span>crop: {crop} (yield {yield_})</span>
                <span>minerals: {mineralStr}</span>
                <span>peaks: {peaks}</span>
                <span>fisheries: {fishR}%</span>
              </div>
            </div>
          ))}
        </div>

        <div style={STYLES.footer}>
          <div style={{ fontSize: 8, color: '#6a5a3a' }}>
            {selected !== null ? `Selected: ${names[selected]}` : 'Click an archipelago to select'}
          </div>
          <button
            style={STYLES.button(selected !== null)}
            disabled={selected === null}
            onClick={() => selected !== null && onSelect(selected)}
          >
            Begin Game
          </button>
        </div>
      </div>
    </div>
  );
}
