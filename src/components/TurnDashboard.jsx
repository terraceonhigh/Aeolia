// ═══════════════════════════════════════════════════════════
// TurnDashboard.jsx — Per-turn game controls
// National Focus selector, expansion targets, timer + speed.
// ═══════════════════════════════════════════════════════════

import { useState } from 'react';
import TurnTimer from './TurnTimer.jsx';

const S = {
  panel: {
    width: 280, flexShrink: 0, borderLeft: '1px solid #2a1f14',
    background: 'linear-gradient(180deg,#100c06,#0a0804)',
    fontFamily: "'JetBrains Mono','Fira Code',monospace",
    fontSize: 9, color: '#c8a878', display: 'flex', flexDirection: 'column',
    overflowY: 'auto',
  },
  section: {
    padding: '10px 14px', borderBottom: '1px solid #2a1f14',
  },
  sectionTitle: {
    fontSize: 10, color: '#b8923a', letterSpacing: '2px', textTransform: 'uppercase',
    fontWeight: 600, marginBottom: 6,
  },
  statGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px',
    fontSize: 8, lineHeight: 1.6,
  },
  statLabel: { color: '#8a7a5a' },
  statValue: { color: '#d4b896', fontWeight: 600, textAlign: 'right' },
  targetItem: (selected) => ({
    padding: '6px 10px', marginBottom: 3, borderRadius: 3, cursor: 'pointer',
    border: `1px solid ${selected ? '#6a5430' : '#2a1f14'}`,
    background: selected ? '#1a1408' : '#0e0a06',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  }),
  eventLog: {
    flex: 1, overflowY: 'auto', padding: '8px 14px',
    fontSize: 8, lineHeight: 1.6, color: '#8a7a5a',
  },
};

// ── National Focus definitions ──────────────────────────

const FOCUSES = [
  { key: 'expand',    icon: '⚔', label: 'Expand',    color: '#c47830', desc: 'Aggressive growth',       alloc: { expansion: 65, techShare: 20, consolidation: 15 } },
  { key: 'innovate',  icon: '◈', label: 'Innovate',   color: '#a09060', desc: 'Research push',           alloc: { expansion: 15, techShare: 65, consolidation: 20 } },
  { key: 'fortify',   icon: '▣', label: 'Fortify',    color: '#7a8a5a', desc: 'Consolidate holdings',    alloc: { expansion: 10, techShare: 20, consolidation: 70 } },
  { key: 'balanced',  icon: '◎', label: 'Balanced',   color: '#9a8a6a', desc: 'Steady all fronts',       alloc: { expansion: 33, techShare: 34, consolidation: 33 } },
  { key: 'exploit',   icon: '⛏', label: 'Exploit',    color: '#8a6a4a', desc: 'Extract + research',      alloc: { expansion: 40, techShare: 45, consolidation: 15 }, minTech: 5 },
];

function FocusCard({ focus, active, locked, onSelect }) {
  const bg = active ? `${focus.color}20` : locked ? '#0a0804' : '#120e08';
  const border = active ? focus.color : locked ? '#1a1408' : '#2a1f14';
  return (
    <div
      onClick={locked ? undefined : onSelect}
      style={{
        flex: 1, padding: '8px 4px', textAlign: 'center', borderRadius: 4,
        cursor: locked ? 'not-allowed' : 'pointer',
        border: `1px solid ${border}`,
        background: bg,
        opacity: locked ? 0.4 : 1,
        transition: 'all 0.15s',
      }}
    >
      <div style={{ fontSize: 16, color: active ? focus.color : locked ? '#3a2a1a' : '#6a5a3a' }}>
        {focus.icon}
      </div>
      <div style={{
        fontSize: 7, fontWeight: 600, letterSpacing: '0.5px',
        color: active ? focus.color : locked ? '#3a2a1a' : '#8a7a5a',
        marginTop: 2,
      }}>
        {focus.label}
      </div>
    </div>
  );
}

function NationalFocus({ activeFocus, playerTech, onSetFocus }) {
  return (
    <div style={{ display: 'flex', gap: 4 }}>
      {FOCUSES.map(f => {
        const locked = f.minTech && playerTech < f.minTech;
        return (
          <FocusCard
            key={f.key}
            focus={f}
            active={activeFocus === f.key}
            locked={locked}
            onSelect={() => onSetFocus(f.key)}
          />
        );
      })}
    </div>
  );
}

// ── Speed control bar ───────────────────────────────────

const SPEEDS = [
  { key: 0,  label: '⏸' },
  { key: 1,  label: '1×' },
  { key: 5,  label: '5×' },
  { key: 10, label: '10×' },
];

function SpeedBar({ speed, onSetSpeed }) {
  return (
    <div style={{ display: 'flex', gap: 2, justifyContent: 'center', marginTop: 8 }}>
      {SPEEDS.map(s => {
        const active = speed === s.key;
        return (
          <button
            key={s.key}
            onClick={() => onSetSpeed(s.key)}
            style={{
              padding: '3px 10px', fontSize: 9, fontFamily: 'inherit',
              cursor: 'pointer', fontWeight: active ? 700 : 400,
              background: active ? '#1a1408' : '#0e0a06',
              border: `1px solid ${active ? '#6a5430' : '#2a1f14'}`,
              color: active ? '#d4b896' : '#6a5a3a',
              borderRadius: 2, letterSpacing: '0.5px',
            }}
          >
            {s.label}
          </button>
        );
      })}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════

export default function TurnDashboard({
  snapshot, frontier, names, playerCore,
  activeFocus, onSetFocus,
  selectedTargets, onToggleTarget,
  onAdvance, eventLog,
  speed, onSetSpeed,
  timerDuration, timerPaused, timerKey,
}) {
  const [showTerritory, setShowTerritory] = useState(false);
  const ps = snapshot?.playerStats;
  const year = snapshot?.year;
  const tick = snapshot?.tick;
  const finished = !!snapshot?.finished;

  // Compute owned archipelagos list
  const ownedArchs = [];
  if (snapshot?.controller && playerCore !== undefined) {
    for (let i = 0; i < snapshot.controller.length; i++) {
      if (snapshot.controller[i] === playerCore) {
        ownedArchs.push(i);
      }
    }
  }

  const eraName = year < -5000 ? 'Antiquity' : year < -2000 ? 'Serial Contact'
    : year < -500 ? 'Colonial' : year < -200 ? 'Industrial' : 'Nuclear';

  // Display game year starting from 0 (tick 60 = Year 0)
  const gameYear = (tick || 60) - 60;
  const yearStr = `Year ${gameYear}`;

  return (
    <div style={S.panel}>
      {/* Header stats */}
      <div style={S.section}>
        <div style={{ ...S.sectionTitle, display: 'flex', justifyContent: 'space-between' }}>
          <span>Turn {gameYear}/340</span>
          <span style={{ color: '#d4b896', fontSize: 9 }}>{yearStr}</span>
        </div>
        <div style={{ fontSize: 8, color: '#6a5a3a', marginBottom: 8 }}>{eraName} Era</div>

        {ps && (
          <div style={S.statGrid}>
            <span style={S.statLabel}>Population</span>
            <span style={S.statValue}>{ps.pop?.toLocaleString()}</span>
            <span style={S.statLabel}>Technology</span>
            <span style={S.statValue}>{ps.tech}</span>
            <span style={S.statLabel}>Territory</span>
            <span
              style={{ ...S.statValue, cursor: 'pointer', textDecoration: 'underline', textDecorationColor: '#3a2a1a' }}
              onClick={() => setShowTerritory(!showTerritory)}
              title="Click to list owned archipelagos"
            >{ps.territory} archs {showTerritory ? '▾' : '▸'}</span>
            <span style={S.statLabel}>Naphtha</span>
            <span style={S.statValue}>{ps.naphtha > 0 ? ps.naphtha.toFixed(1) : '---'}</span>
            <span style={S.statLabel}>Contacts</span>
            <span style={S.statValue}>{ps.contacts}</span>
            <span style={S.statLabel}>Culture</span>
            <span style={S.statValue}>{ps.cultureLabel}</span>
            {ps.hasPu && <>
              <span style={{ ...S.statLabel, color: '#a04030' }}>Plutonium</span>
              <span style={{ ...S.statValue, color: '#a04030' }}>ACTIVE</span>
            </>}
          </div>
        )}

        {/* Expandable territory list */}
        {showTerritory && ownedArchs.length > 0 && (
          <div style={{
            marginTop: 8, padding: '6px 8px', borderRadius: 3,
            background: '#0e0a06', border: '1px solid #2a1f14',
            maxHeight: 120, overflowY: 'auto',
          }}>
            <div style={{ fontSize: 7, color: '#6a5a3a', marginBottom: 4, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Controlled Archipelagos
            </div>
            {ownedArchs.map(idx => (
              <div key={idx} style={{
                fontSize: 8, padding: '2px 4px', lineHeight: 1.5,
                color: idx === playerCore ? '#d4b896' : '#b8923a',
              }}>
                {idx === playerCore ? '★ ' : '◆ '}{names[idx]}
                {idx === playerCore && <span style={{ color: '#6a5a3a', marginLeft: 4 }}>(homeland)</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Timer + Speed */}
      <div style={S.section}>
        <TurnTimer
          key={timerKey}
          duration={timerDuration}
          onComplete={onAdvance}
          paused={timerPaused || speed === 0}
          finished={finished}
        />
        <SpeedBar speed={speed} onSetSpeed={onSetSpeed} />
        {speed === 0 && !finished && (
          <div style={{ textAlign: 'center', marginTop: 6 }}>
            <button
              onClick={onAdvance}
              style={{
                padding: '6px 20px', fontSize: 9, fontFamily: 'inherit',
                cursor: 'pointer', fontWeight: 600, letterSpacing: '1.5px',
                background: '#1a1408', border: '1px solid #6a5430',
                color: '#d4b896', borderRadius: 3, textTransform: 'uppercase',
              }}
            >
              Advance
            </button>
          </div>
        )}
      </div>

      {/* National Focus */}
      <div style={S.section}>
        <div style={S.sectionTitle}>National Focus</div>
        <NationalFocus
          activeFocus={activeFocus}
          playerTech={ps?.tech || 0}
          onSetFocus={onSetFocus}
        />
        <div style={{ fontSize: 7, color: '#6a5a3a', marginTop: 6, textAlign: 'center' }}>
          {FOCUSES.find(f => f.key === activeFocus)?.desc || 'Choose a focus'}
        </div>
      </div>

      {/* Expansion targets */}
      <div style={S.section}>
        <div style={S.sectionTitle}>
          Expansion Targets
          <span style={{ fontSize: 7, color: '#6a5a3a', fontWeight: 400, marginLeft: 8 }}>
            {selectedTargets.size} selected
          </span>
        </div>
        <div style={{ maxHeight: 200, overflowY: 'auto' }}>
          {frontier.length === 0 && (
            <div style={{ color: '#6a5a3a', fontStyle: 'italic', padding: '8px 0' }}>
              No frontier — fully landlocked or tech too low
            </div>
          )}
          {frontier.map(f => {
            const sel = selectedTargets.has(f.index);
            const owned = f.controller !== f.index;
            return (
              <div key={f.index} style={S.targetItem(sel)} onClick={() => onToggleTarget(f.index)}>
                <div>
                  <div style={{ fontSize: 9, color: sel ? '#d4b896' : '#c8a878', fontWeight: sel ? 600 : 400 }}>
                    {sel ? '[ x ] ' : '[   ] '}{names[f.index]}
                    {owned && <span style={{ color: '#a07030', marginLeft: 4 }}>(held)</span>}
                  </div>
                  <div style={{ fontSize: 7, color: '#6a5a3a', marginTop: 2 }}>
                    pop {f.pop} · tech {f.tech} · {f.crop}
                    {f.minerals.Cu && ' · Cu'}
                    {f.minerals.Au && ' · Au'}
                    {f.minerals.C > 0 && ' · C'}
                    {f.minerals.Pu && ' · Pu'}
                  </div>
                </div>
                <div style={{ fontSize: 8, color: '#6a5a3a' }}>
                  d={f.distance.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Intelligence — fog of war aware */}
      <div style={S.section}>
        <div style={S.sectionTitle}>Intelligence</div>
        {(() => {
          const vis = snapshot?.visibility;
          const contacts = snapshot?.contactedCores || [];
          const knownArchs = vis ? vis.filter(v => v !== 'unknown').length : 0;
          const totalArchs = vis ? vis.length : 0;
          return (
            <div style={S.statGrid}>
              <span style={S.statLabel}>Known world</span>
              <span style={S.statValue}>{knownArchs}/{totalArchs} archs</span>
              <span style={S.statLabel}>Contacted nations</span>
              <span style={S.statValue}>{contacts.length}</span>
              {contacts.length > 0 && contacts.slice(0, 4).map((cc, i) => {
                const cTech = snapshot?.tech?.[cc];
                const cPop = snapshot?.polityPops?.[cc];
                return [
                  <span key={`l${i}`} style={{ ...S.statLabel, color: '#7a6a4a' }}>
                    {names[cc] || `Nation ${cc}`}
                  </span>,
                  <span key={`v${i}`} style={{ ...S.statValue, color: '#b8a080' }}>
                    t{cTech} · p{cPop ? Math.round(cPop / 100) * 100 : '?'}
                  </span>,
                ];
              }).flat()}
              {contacts.length > 4 && <>
                <span style={{ ...S.statLabel, color: '#4a3a2a' }}>+ {contacts.length - 4} more</span>
                <span style={S.statValue}></span>
              </>}
              <span style={S.statLabel}>Terra incognita</span>
              <span style={{ ...S.statValue, color: '#4a3a2a' }}>
                {totalArchs - knownArchs} archs
              </span>
            </div>
          );
        })()}
      </div>

      {/* Event log */}
      <div style={{ ...S.section, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 100 }}>
        <div style={S.sectionTitle}>Events</div>
        <div style={S.eventLog}>
          {eventLog.length === 0 && (
            <div style={{ color: '#6a5a3a', fontStyle: 'italic' }}>No events yet</div>
          )}
          {eventLog.slice(-30).reverse().map((ev, i) => (
            <div key={i} style={{ marginBottom: 4, paddingLeft: 6, borderLeft: `2px solid ${ev.color || '#2a1f14'}` }}>
              <span style={{ color: '#6a5a3a' }}>{ev.yearStr} </span>
              <span>{ev.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export { FOCUSES };
