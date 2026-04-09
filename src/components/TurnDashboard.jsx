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

// ── Situation Report Cards ──────────────────────────────

function SituationCards({ cards, onApplyCard }) {
  if (!cards || cards.length === 0) return null;
  return (
    <div style={{
      padding: '10px 14px', borderBottom: '1px solid #2a1f14',
      background: '#0c0906',
    }}>
      <div style={{
        fontSize: 10, color: '#b8923a', letterSpacing: '2px',
        textTransform: 'uppercase', fontWeight: 600, marginBottom: 8,
      }}>
        Situation
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {cards.map(card => (
          <div key={card.id} style={{
            padding: '8px 10px', borderRadius: 3,
            background: '#110d07',
            border: '1px solid #3a2a14',
          }}>
            <div style={{
              fontSize: 9, color: '#d4b896', fontWeight: 700,
              letterSpacing: '0.5px', marginBottom: 5,
            }}>
              {card.icon}  {card.title}
            </div>
            <div style={{
              fontSize: 8, color: '#a8906a', lineHeight: 1.55, marginBottom: 7,
            }}>
              {card.body}
            </div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {card.actions.map((act, i) => (
                <button
                  key={i}
                  onClick={() => onApplyCard?.(card.id, act.action)}
                  style={{
                    padding: '2px 8px', fontSize: 7, fontFamily: 'inherit',
                    cursor: 'pointer', fontWeight: 600, letterSpacing: '1px',
                    background: act.action ? '#1a1408' : '#0e0a06',
                    border: `1px solid ${act.action ? '#4a3a20' : '#2a1f14'}`,
                    color: act.action ? '#c8a878' : '#6a5a3a',
                    borderRadius: 2, textTransform: 'uppercase',
                  }}
                >
                  {act.label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
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
  // Interaction mechanics
  embargoTargets, onToggleEmbargo,
  rivalCores, onToggleRival,
  partnerCores, onTogglePartner,
  culturePolicyCI, culturePolicyIO, onSetCulturePolicy,
  sovFocusTargets, onToggleSovFocus,
  scoutActive, onToggleScout,
  // Situation cards
  pendingCards, onApplyCard,
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
            {ps.piety !== undefined && (() => {
              const piety = ps.piety;
              const piLabel = piety >= 0.75 ? 'fervent' : piety >= 0.50 ? 'devout' : piety >= 0.30 ? 'moderate' : 'secular';
              const piColor = piety >= 0.75 ? '#b8923a' : piety >= 0.50 ? '#9a8a5a' : '#6a5a3a';
              return (<>
                <span style={S.statLabel}>Piety</span>
                <span style={{ ...S.statValue, color: piColor }}>{piLabel} {(piety * 100).toFixed(0)}%</span>
              </>);
            })()}
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

      {/* Situation Report Cards */}
      <SituationCards cards={pendingCards} onApplyCard={onApplyCard} />

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

      {/* Diplomacy — rivals, partners, embargoes */}
      {(snapshot?.contactedCores?.length > 0) && (
        <div style={S.section}>
          <div style={S.sectionTitle}>Diplomacy</div>
          <div style={{ maxHeight: 140, overflowY: 'auto' }}>
            {snapshot.contactedCores.map(cc => {
              const isRival = rivalCores?.has(cc);
              const isPartner = partnerCores?.has(cc);
              const isEmbargo = embargoTargets?.has(cc);
              return (
                <div key={cc} style={{
                  padding: '4px 8px', marginBottom: 2, borderRadius: 3,
                  background: isRival ? '#1a0808' : isPartner ? '#0a1408' : '#0e0a06',
                  border: `1px solid ${isRival ? '#4a2020' : isPartner ? '#2a4a20' : '#1a1408'}`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <span style={{ fontSize: 8, color: '#c8a878' }}>{names[cc] || `Nation ${cc}`}</span>
                  <div style={{ display: 'flex', gap: 2 }}>
                    <button onClick={() => onToggleRival?.(cc)} title="Rival — prioritize attacking"
                      style={{
                        padding: '1px 5px', fontSize: 7, fontFamily: 'inherit', cursor: 'pointer',
                        background: isRival ? '#3a1010' : '#0a0804', border: `1px solid ${isRival ? '#6a3030' : '#2a1f14'}`,
                        color: isRival ? '#c06040' : '#6a5a3a', borderRadius: 2,
                      }}>⚔</button>
                    <button onClick={() => onTogglePartner?.(cc)} title="Partner — trade bonus, avoid attacking"
                      style={{
                        padding: '1px 5px', fontSize: 7, fontFamily: 'inherit', cursor: 'pointer',
                        background: isPartner ? '#0a1a08' : '#0a0804', border: `1px solid ${isPartner ? '#3a6a30' : '#2a1f14'}`,
                        color: isPartner ? '#80c060' : '#6a5a3a', borderRadius: 2,
                      }}>◆</button>
                    <button onClick={() => onToggleEmbargo?.(cc)} title="Embargo — block trade"
                      style={{
                        padding: '1px 5px', fontSize: 7, fontFamily: 'inherit', cursor: 'pointer',
                        background: isEmbargo ? '#1a1000' : '#0a0804', border: `1px solid ${isEmbargo ? '#6a5020' : '#2a1f14'}`,
                        color: isEmbargo ? '#c0a040' : '#6a5a3a', borderRadius: 2,
                      }}>✕</button>
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: 7, color: '#4a3a2a', marginTop: 4 }}>
            ⚔ rival · ◆ partner · ✕ embargo
          </div>
        </div>
      )}

      {/* Cultural Policy */}
      <div style={S.section}>
        <div style={S.sectionTitle}>
          Cultural Policy
          <span style={{ fontSize: 7, color: '#6a5a3a', fontWeight: 400, marginLeft: 8 }}>
            {ps?.cultureLabel || '—'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 7, color: '#6a5a3a', width: 50 }}>Collect.</span>
            <input type="range" min={-100} max={100} value={Math.round((culturePolicyCI || 0) * 100)}
              onChange={e => onSetCulturePolicy?.('ci', Number(e.target.value) / 100)}
              style={{ flex: 1, accentColor: '#8a7a5a' }} />
            <span style={{ fontSize: 7, color: '#6a5a3a', width: 50, textAlign: 'right' }}>Indiv.</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 7, color: '#6a5a3a', width: 50 }}>Inward</span>
            <input type="range" min={-100} max={100} value={Math.round((culturePolicyIO || 0) * 100)}
              onChange={e => onSetCulturePolicy?.('io', Number(e.target.value) / 100)}
              style={{ flex: 1, accentColor: '#8a7a5a' }} />
            <span style={{ fontSize: 7, color: '#6a5a3a', width: 50, textAlign: 'right' }}>Outward</span>
          </div>
        </div>
      </div>

      {/* Scout & Sovereignty Focus */}
      <div style={S.section}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={S.sectionTitle}>Operations</div>
          <button onClick={() => onToggleScout?.()}
            style={{
              padding: '2px 8px', fontSize: 7, fontFamily: 'inherit', cursor: 'pointer',
              background: scoutActive ? '#1a1408' : '#0a0804',
              border: `1px solid ${scoutActive ? '#6a5430' : '#2a1f14'}`,
              color: scoutActive ? '#d4b896' : '#6a5a3a', borderRadius: 2,
              fontWeight: scoutActive ? 600 : 400,
            }}>
            {scoutActive ? '◉ SCOUTING' : '○ Scout'}
          </button>
        </div>
        {ownedArchs.length > 1 && (
          <>
            <div style={{ fontSize: 7, color: '#6a5a3a', marginBottom: 4, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Sovereignty Focus
            </div>
            <div style={{ maxHeight: 100, overflowY: 'auto' }}>
              {ownedArchs.filter(i => i !== playerCore).map(i => {
                const focused = sovFocusTargets?.has(i);
                const sov = snapshot?.sovereignty?.[i];
                return (
                  <div key={i} onClick={() => onToggleSovFocus?.(i)} style={{
                    padding: '3px 6px', marginBottom: 1, cursor: 'pointer', borderRadius: 2,
                    background: focused ? '#14100a' : '#0e0a06',
                    border: `1px solid ${focused ? '#4a3a20' : '#1a1408'}`,
                    display: 'flex', justifyContent: 'space-between', fontSize: 8,
                  }}>
                    <span style={{ color: focused ? '#d4b896' : '#8a7a5a' }}>
                      {focused ? '▣ ' : '□ '}{names[i]}
                    </span>
                    {sov !== undefined && (
                      <span style={{ color: sov > 0.6 ? '#7a8a5a' : sov > 0.3 ? '#8a7a3a' : '#a05030', fontSize: 7 }}>
                        {Math.round(sov * 100)}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Dispatches log */}
      <div style={{ ...S.section, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 100 }}>
        <div style={S.sectionTitle}>Dispatches</div>
        <div style={S.eventLog}>
          {eventLog.length === 0 && (
            <div style={{ color: '#6a5a3a', fontStyle: 'italic' }}>No dispatches yet</div>
          )}
          {eventLog.slice(-40).reverse().map((ev, i) => {
            // Parse source tag from text (format: "SOURCE — body")
            const sep = ev.text?.indexOf(' — ');
            const hasSource = sep > 0 && sep < 32;
            const source = hasSource ? ev.text.slice(0, sep) : null;
            const body = hasSource ? ev.text.slice(sep + 3) : ev.text;
            const sourceColor = {
              'ADMIRALTY INTELLIGENCE': '#a04030',
              'MERCHANT GUILD': '#b8923a',
              'INTERNAL AFFAIRS': '#7a8a5a',
              'CULTURAL OBSERVER': '#9a6a9a',
              'CARTOGRAPHIC SURVEY': '#4a8aaa',
              'GEOLOGICAL SURVEY': '#8a6a4a',
              'DIPLOMATIC CORPS': '#6a9a7a',
              'MERCHANT GUILD REPORT': '#b8923a',
            }[source] || (ev.color || '#2a1f14');
            return (
              <div key={i} style={{
                marginBottom: 6, paddingLeft: 7,
                borderLeft: `2px solid ${sourceColor}`,
              }}>
                <div style={{ display: 'flex', gap: 4, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  {source && (
                    <span style={{ color: sourceColor, fontSize: 7, fontWeight: 700, letterSpacing: '0.5px', flexShrink: 0 }}>
                      {source}
                    </span>
                  )}
                  <span style={{ color: '#6a5a3a', fontSize: 7, flexShrink: 0 }}>{ev.yearStr}</span>
                </div>
                <div style={{ color: '#a8906a', fontSize: 8, lineHeight: 1.5, marginTop: 1 }}>
                  {body}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export { FOCUSES };
