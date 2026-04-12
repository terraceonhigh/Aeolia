// ═══════════════════════════════════════════════════════════
// TurnDashboard.jsx — Strategy game chrome (three-zone layout)
//
// Exports three components consumed by GameApp.jsx:
//
//   CommandBar   — top strip (always visible): turn/stats/timer/focus
//   TurnDashboard (default) — right context panel: focus cards,
//                 expansion targets, diplomacy, culture, ops
//   FeedZone     — bottom strip: dispatches feed + situation cards
//
// The globe occupies the unobstructed center. No panel ever covers
// it during normal play; overlays (EventPopup, PolitySelect) are
// separate and intentionally full-screen.
// ═══════════════════════════════════════════════════════════

import { useState } from 'react';
import TurnTimer from './TurnTimer.jsx';

const MONO = "'JetBrains Mono','Fira Code',monospace";

// ── Shared palette helpers ───────────────────────────────────
const BORDER = '1px solid #2a1f14';
const BG_PANEL = 'linear-gradient(180deg,#100c06,#0a0804)';

// ── National Focus definitions ───────────────────────────────

const FOCUSES = [
  { key: 'expand',   icon: '⚔', label: 'Expand',   color: '#c47830', desc: 'Aggressive growth',     alloc: { expansion: 65, techShare: 20, consolidation: 15 } },
  { key: 'innovate', icon: '◈', label: 'Innovate',  color: '#a09060', desc: 'Research push',          alloc: { expansion: 15, techShare: 65, consolidation: 20 } },
  { key: 'fortify',  icon: '▣', label: 'Fortify',   color: '#7a8a5a', desc: 'Consolidate holdings',   alloc: { expansion: 10, techShare: 20, consolidation: 70 } },
  { key: 'balanced', icon: '◎', label: 'Balanced',  color: '#9a8a6a', desc: 'Steady all fronts',      alloc: { expansion: 33, techShare: 34, consolidation: 33 } },
  { key: 'exploit',  icon: '⛏', label: 'Exploit',   color: '#8a6a4a', desc: 'Extract + research',     alloc: { expansion: 40, techShare: 45, consolidation: 15 }, minTech: 5 },
];

// ── Speed buttons ────────────────────────────────────────────

const SPEEDS = [
  { key: 0,  label: '⏸' },
  { key: 1,  label: '1×' },
  { key: 5,  label: '5×' },
  { key: 10, label: '10×' },
];

function SpeedBar({ speed, onSetSpeed }) {
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {SPEEDS.map(s => {
        const active = speed === s.key;
        return (
          <button key={s.key} onClick={() => onSetSpeed(s.key)} style={{
            padding: '2px 7px', fontSize: 8, fontFamily: MONO,
            cursor: 'pointer', fontWeight: active ? 700 : 400,
            background: active ? '#1a1408' : '#0a0804',
            border: `1px solid ${active ? '#6a5430' : '#2a1f14'}`,
            color: active ? '#d4b896' : '#6a5a3a',
            borderRadius: 2, letterSpacing: '0.5px',
          }}>{s.label}</button>
        );
      })}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// ZONE A — CommandBar
// Full-width, pinned below the app header. Never scrolls.
// ═══════════════════════════════════════════════════════════

export function CommandBar({
  snapshot, playerCore, activeFocus,
  speed, onSetSpeed,
  timerKey, timerDuration, timerPaused, onAdvance,
  finished,
}) {
  const ps = snapshot?.playerStats;
  const tick = snapshot?.tick || 60;
  const year = snapshot?.year;
  const gameYear = tick - 60;
  const eraName = !year ? 'Antiquity'
    : year < -5000 ? 'Antiquity' : year < -2000 ? 'Serial Contact'
    : year < -500  ? 'Colonial'  : year < -200  ? 'Industrial' : 'Nuclear';

  const activeFocusDef = FOCUSES.find(f => f.key === activeFocus);
  const alloc = activeFocusDef?.alloc;

  // Piety label + color
  const piety = ps?.piety;
  const piLabel = piety === undefined ? null
    : piety >= 0.75 ? 'fervent' : piety >= 0.50 ? 'devout' : piety >= 0.30 ? 'moderate' : 'secular';
  const piColor = piety === undefined ? '#8a7a5a'
    : piety >= 0.75 ? '#b8923a' : piety >= 0.50 ? '#9a8a5a' : '#6a5a3a';

  const S = {
    label: { color: '#6a5a3a', fontSize: 7, letterSpacing: '0.5px' },
    value: { color: '#d4b896', fontSize: 9, fontWeight: 600 },
    pipe:  { color: '#3a2a1a', padding: '0 6px' },
  };

  return (
    <div style={{
      flexShrink: 0, borderBottom: BORDER,
      background: 'linear-gradient(180deg,#130f09,#0c0806)',
      fontFamily: MONO, display: 'flex', alignItems: 'stretch',
      height: 52,
    }}>

      {/* ── Turn / Era ── */}
      <div style={{
        padding: '0 16px', borderRight: BORDER, display: 'flex',
        flexDirection: 'column', justifyContent: 'center', flexShrink: 0, minWidth: 130,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#d4b896', letterSpacing: '1px' }}>
          TURN {gameYear}<span style={{ color: '#4a3a2a', fontWeight: 400 }}>/340</span>
        </div>
        <div style={{ fontSize: 7, color: '#7a6a4a', marginTop: 2, letterSpacing: '1.5px', textTransform: 'uppercase' }}>
          {eraName} Era
        </div>
      </div>

      {/* ── Stat strip ── */}
      {ps && (
        <div style={{
          flex: 1, padding: '0 14px', display: 'flex', alignItems: 'center',
          gap: 0, overflow: 'hidden',
        }}>
          {(() => {
            // Derive food security label from fishery + crop health
            const fH = ps.fisheryHealth ?? 1, cH = ps.cropHealth ?? 1;
            const foodAvg = (fH + cH) / 2;
            const foodLabel = foodAvg >= 0.85 ? 'Secure' : foodAvg >= 0.6 ? 'Stressed'
              : foodAvg >= 0.35 ? 'Scarce' : 'Famine';
            const foodColor = foodAvg >= 0.85 ? S.value.color : foodAvg >= 0.6 ? '#8a7a2a'
              : foodAvg >= 0.35 ? '#c47830' : '#a04030';
            return [
              ['POP',      ps.pop?.toLocaleString()],
              ['TECH',     ps.tech],
              ['TERR',     `${ps.territory} archs`],
              ['FOOD',     foodLabel],
              ['NAPH',     ps.naphtha > 0 ? ps.naphtha.toFixed(1) : '—'],
              ['CONTACTS', ps.contacts],
              ['CULTURE',  ps.cultureLabel],
              ...(piLabel ? [['PIETY', piLabel]] : []),
              ...(snapshot?.pu_scramble_onset_tick && ps?.hasPu
                ? [['PYRA', ps.tech >= 9.0 ? 'WEAPONS' : 'DEPOSITS']] : []),
            ].map(([lbl, val], i, arr) => (
              <div key={lbl} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', padding: '0 10px' }}>
                  <div style={S.label}>{lbl}</div>
                  <div style={lbl === 'PIETY' ? { ...S.value, color: piColor }
                    : lbl === 'PYRA' ? { ...S.value, color: ps.tech >= 9.0 ? '#a04030' : '#7a6a2a' }
                    : lbl === 'TERR' ? { ...S.value, color: ps.territory <= 1 ? '#a04030' : ps.territory <= 3 ? '#c47830' : S.value.color }
                    : lbl === 'FOOD' ? { ...S.value, color: foodColor }
                    : S.value}>{val}</div>
                  {lbl === 'PIETY' && piety !== undefined && (
                    <div style={{ width: 40, height: 2, borderRadius: 1, background: '#1a120a', marginTop: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.min(piety, 1) * 100}%`, background: piColor, transition: 'width 0.3s' }} />
                    </div>
                  )}
                  {lbl === 'FOOD' && (
                    <div style={{ width: 40, height: 2, borderRadius: 1, background: '#1a120a', marginTop: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${foodAvg * 100}%`, background: foodColor, transition: 'width 0.3s' }} />
                    </div>
                  )}
                </div>
                {i < arr.length - 1 && <div style={S.pipe}>·</div>}
              </div>
            ));
          })()}
        </div>
      )}

      {/* ── Focus badge ── */}
      {activeFocusDef && (
        <div style={{
          padding: '0 14px', borderLeft: BORDER, borderRight: BORDER,
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          alignItems: 'center', flexShrink: 0, minWidth: 90,
        }}>
          <div style={{ fontSize: 13, color: activeFocusDef.color, lineHeight: 1 }}>
            {activeFocusDef.icon}
          </div>
          <div style={{ fontSize: 7, fontWeight: 700, color: activeFocusDef.color, letterSpacing: '1px', marginTop: 2 }}>
            {activeFocusDef.label.toUpperCase()}
          </div>
          {alloc && (
            <div style={{ fontSize: 6, color: '#6a5a3a', marginTop: 1, letterSpacing: '0.5px' }}>
              {alloc.expansion}/{alloc.techShare}/{alloc.consolidation}
            </div>
          )}
        </div>
      )}

      {/* ── Speed + Timer ── */}
      <div style={{
        padding: '0 14px', display: 'flex', alignItems: 'center',
        gap: 10, flexShrink: 0,
      }}>
        <SpeedBar speed={speed} onSetSpeed={onSetSpeed} />
        <TurnTimer
          key={timerKey}
          size={44}
          duration={timerDuration}
          onComplete={onAdvance}
          paused={timerPaused || speed === 0}
          finished={finished}
        />
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// ZONE C — FeedZone
// Full-width, pinned to bottom. Dispatches left, cards right.
// ═══════════════════════════════════════════════════════════

const DISPATCH_FILTERS = [
  { key: 'all',       label: 'ALL' },
  { key: 'admiralty',  label: 'ADM',  match: 'ADMIRALTY' },
  { key: 'merchant',   label: 'MER',  match: 'MERCHANT' },
  { key: 'internal',   label: 'INT',  match: 'INTERNAL' },
  { key: 'other',      label: 'OTH' },
];

export function FeedZone({ eventLog, pendingCards, cardHistory, onApplyCard }) {
  const [dispatchFilter, setDispatchFilter] = useState('all');
  const [cardTab, setCardTab] = useState('active'); // 'active' | 'history'

  const filteredLog = dispatchFilter === 'all' ? eventLog
    : eventLog.filter(ev => {
        const sep = ev.text?.indexOf(' — ');
        const source = (sep > 0 && sep < 32) ? ev.text.slice(0, sep) : '';
        const filterDef = DISPATCH_FILTERS.find(f => f.key === dispatchFilter);
        if (!filterDef?.match) {
          // "other" — everything not matching admiralty/merchant/internal
          return !source.includes('ADMIRALTY') && !source.includes('MERCHANT') && !source.includes('INTERNAL');
        }
        return source.includes(filterDef.match);
      });

  return (
    <div style={{
      flexShrink: 0, borderTop: BORDER,
      background: 'linear-gradient(0deg,#0c0806,#100c06)',
      fontFamily: MONO, display: 'flex',
      height: 190,
    }}>

      {/* ── Dispatches ── */}
      <div style={{
        flex: '0 0 55%', borderRight: BORDER,
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{
          flexShrink: 0, padding: '5px 14px 4px', borderBottom: '1px solid #1a1408',
          fontSize: 8, color: '#7a6a3a', letterSpacing: '2px', textTransform: 'uppercase',
          fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>Dispatches</span>
          <div style={{ display: 'flex', gap: 2 }}>
            {DISPATCH_FILTERS.map(f => {
              const active = dispatchFilter === f.key;
              return (
                <button key={f.key} onClick={() => setDispatchFilter(f.key)} style={{
                  padding: '1px 4px', fontSize: 6, fontFamily: MONO,
                  cursor: 'pointer', fontWeight: active ? 700 : 400,
                  background: active ? '#1a1408' : 'transparent',
                  border: `1px solid ${active ? '#4a3a20' : '#1a1408'}`,
                  color: active ? '#c8a878' : '#4a3a2a',
                  borderRadius: 2, letterSpacing: '0.3px',
                  textTransform: 'uppercase',
                }}>
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>
        <div style={{
          flex: 1, overflowY: 'auto', padding: '6px 14px',
          display: 'flex', flexDirection: 'column', gap: 5,
        }}>
          {filteredLog.length === 0 && (
            <div style={{ color: '#4a3a2a', fontStyle: 'italic', fontSize: 8 }}>
              {dispatchFilter === 'all' ? 'No dispatches yet' : 'No matching dispatches'}
            </div>
          )}
          {filteredLog.slice(-50).reverse().map((ev, i) => {
            const sep = ev.text?.indexOf(' — ');
            const hasSource = sep > 0 && sep < 32;
            const source = hasSource ? ev.text.slice(0, sep) : null;
            const body   = hasSource ? ev.text.slice(sep + 3) : ev.text;
            const sourceColor = {
              'ADMIRALTY INTELLIGENCE': '#a04030',
              'MERCHANT GUILD':         '#b8923a',
              'INTERNAL AFFAIRS':       '#7a8a5a',
              'CULTURAL OBSERVER':      '#9a6a9a',
              'CARTOGRAPHIC SURVEY':    '#4a8aaa',
              'GEOLOGICAL SURVEY':      '#8a6a4a',
              'DIPLOMATIC CORPS':       '#6a9a7a',
              'MERCHANT GUILD REPORT':  '#b8923a',
              'YOUR ORDERS':            '#6a8a6a',
            }[source] || ev.color || '#3a2a1a';
            return (
              <div key={i} style={{ paddingLeft: 7, borderLeft: `2px solid ${sourceColor}`, flexShrink: 0 }}>
                <div style={{ display: 'flex', gap: 5, alignItems: 'baseline' }}>
                  {source && (
                    <span style={{ color: sourceColor, fontSize: 7, fontWeight: 700, letterSpacing: '0.3px' }}>
                      {source}
                    </span>
                  )}
                  <span style={{ color: '#5a4a3a', fontSize: 7 }}>{ev.yearStr}</span>
                </div>
                <div style={{ color: '#a8906a', fontSize: 7.5, lineHeight: 1.45, marginTop: 1 }}>
                  {body}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Situation Cards (active + history tabs) ── */}
      <div style={{
        flex: '0 0 45%',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{
          flexShrink: 0, padding: '5px 14px 4px', borderBottom: '1px solid #1a1408',
          fontSize: 8, color: '#7a6a3a', letterSpacing: '2px', textTransform: 'uppercase',
          fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>
            Situation
            {cardTab === 'active' && pendingCards?.length > 0 && (
              <span style={{ color: '#6a5a3a', fontWeight: 400, marginLeft: 6, fontSize: 7 }}>
                {pendingCards.length}
              </span>
            )}
          </span>
          <div style={{ display: 'flex', gap: 2 }}>
            {[
              { key: 'active', label: 'Active' },
              { key: 'history', label: 'History' },
            ].map(t => {
              const active = cardTab === t.key;
              return (
                <button key={t.key} onClick={() => setCardTab(t.key)} style={{
                  padding: '1px 5px', fontSize: 6, fontFamily: MONO,
                  cursor: 'pointer', fontWeight: active ? 700 : 400,
                  background: active ? '#1a1408' : 'transparent',
                  border: `1px solid ${active ? '#4a3a20' : '#1a1408'}`,
                  color: active ? '#c8a878' : '#4a3a2a',
                  borderRadius: 2, letterSpacing: '0.3px', textTransform: 'uppercase',
                }}>
                  {t.label}
                </button>
              );
            })}
          </div>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 10px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {cardTab === 'active' && (
            <>
              {(!pendingCards || pendingCards.length === 0) && (
                <div style={{ color: '#4a3a2a', fontStyle: 'italic', fontSize: 8, padding: '4px 0' }}>
                  No active situations
                </div>
              )}
              {pendingCards?.map(card => (
                <div key={card.id} style={{
                  padding: '7px 9px', borderRadius: 3, flexShrink: 0,
                  background: '#110d07', border: '1px solid #3a2a14',
                }}>
                  <div style={{
                    fontSize: 8, color: '#d4b896', fontWeight: 700,
                    letterSpacing: '0.5px', marginBottom: 4,
                  }}>
                    {card.icon} {card.title}
                  </div>
                  <div style={{
                    fontSize: 7.5, color: '#907858', lineHeight: 1.5, marginBottom: 6,
                  }}>
                    {card.body}
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {card.actions.map((act, i) => (
                      <button key={i}
                        onClick={() => onApplyCard?.(card.id, act.action, act.label)}
                        style={{
                          padding: '2px 7px', fontSize: 7, fontFamily: MONO,
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
            </>
          )}
          {cardTab === 'history' && (
            <>
              {(!cardHistory || cardHistory.length === 0) && (
                <div style={{ color: '#4a3a2a', fontStyle: 'italic', fontSize: 8, padding: '4px 0' }}>
                  No card history yet
                </div>
              )}
              {cardHistory?.slice().reverse().map((h, i) => (
                <div key={i} style={{
                  padding: '5px 8px', borderRadius: 2, flexShrink: 0,
                  background: '#0c0906', border: '1px solid #1e1608',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: 7.5, color: '#a8906a', fontWeight: 600 }}>
                      {h.icon} {h.title}
                    </span>
                    <span style={{ fontSize: 6, color: '#4a3a2a' }}>{h.yearStr}</span>
                  </div>
                  <div style={{ fontSize: 6.5, color: '#6a5a3a', marginTop: 2 }}>
                    → {h.action}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// ZONE B — TurnDashboard (Context Panel, right edge)
// Narrower than before (240px). No stats, no timer, no cards.
// Focus cards + expansion targets + intel + diplomacy + culture + ops.
// ═══════════════════════════════════════════════════════════

const S = {
  panel: {
    width: 240, flexShrink: 0, borderLeft: BORDER,
    background: BG_PANEL,
    fontFamily: MONO,
    fontSize: 9, color: '#c8a878',
    display: 'flex', flexDirection: 'column',
    overflowY: 'auto',
  },
  section: {
    padding: '9px 12px', borderBottom: BORDER,
  },
  sectionTitle: {
    fontSize: 9, color: '#b8923a', letterSpacing: '2px',
    textTransform: 'uppercase', fontWeight: 600, marginBottom: 6,
  },
  statGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 10px',
    fontSize: 8, lineHeight: 1.5,
  },
  statLabel: { color: '#8a7a5a' },
  statValue: { color: '#d4b896', fontWeight: 600, textAlign: 'right' },
  targetItem: (selected) => ({
    padding: '5px 8px', marginBottom: 3, borderRadius: 3, cursor: 'pointer',
    border: `1px solid ${selected ? '#6a5430' : '#2a1f14'}`,
    background: selected ? '#1a1408' : '#0e0a06',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  }),
};

function FocusCard({ focus, active, locked, onSelect }) {
  const alloc = focus.alloc;

  // Active: inverted — bright parchment text on prominently lit background
  // Inactive: heavily dimmed so active state reads clearly at a glance
  const bg     = active ? `${focus.color}38` : '#0c0906';
  const border = active ? focus.color : '#1e1608';
  const iconC  = active ? '#f0ddb8' : locked ? '#2a1a0a' : '#4a3a2a';
  const labelC = active ? '#e8d0a8' : locked ? '#2a1a0a' : '#5a4a32';

  return (
    <div onClick={locked ? undefined : onSelect} style={{
      flex: 1, padding: '6px 3px 5px', textAlign: 'center', borderRadius: 3,
      cursor: locked ? 'not-allowed' : 'pointer',
      border: `1px solid ${border}`, background: bg,
      opacity: locked ? 0.35 : 1,
      transition: 'background 0.2s, border-color 0.2s',
      boxShadow: active ? `inset 0 0 8px ${focus.color}18` : 'none',
    }}>
      <div style={{ fontSize: active ? 17 : 14, color: iconC, transition: 'font-size 0.15s' }}>
        {focus.icon}
      </div>
      <div style={{
        fontSize: 6, fontWeight: active ? 700 : 500, letterSpacing: '0.5px',
        color: labelC, marginTop: 2,
      }}>
        {focus.label.toUpperCase()}
      </div>
      {/* Allocation bar — three segments, bright when active, dimmed when inactive */}
      {alloc && (
        <div style={{ display: 'flex', marginTop: 5, height: active ? 4 : 2, borderRadius: 2, overflow: 'hidden', gap: 1, transition: 'height 0.15s' }}>
          <div style={{ flex: alloc.expansion,     background: active ? '#c47830' : locked ? '#1e1608' : '#3a2410' }} />
          <div style={{ flex: alloc.techShare,     background: active ? '#a09060' : locked ? '#1e1608' : '#302818' }} />
          <div style={{ flex: alloc.consolidation, background: active ? '#7a8a5a' : locked ? '#1e1608' : '#283018' }} />
        </div>
      )}
      {/* Allocation percentages — shown on all cards, not just active */}
      {alloc && !active && !locked && (
        <div style={{ fontSize: 5, color: '#4a3a2a', marginTop: 2, letterSpacing: '0.3px' }}>
          {alloc.expansion}/{alloc.techShare}/{alloc.consolidation}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Arch Detail Panel — shows when a globe arch is clicked.
// Floats at top of Zone C; provides direct action buttons.
// ═══════════════════════════════════════════════════════════

// Fe is a raw world-gen precursor converted to C (naphtha) by SimEngine — exclude from display.
const MINERAL_LABELS = { C: 'naphtha', Pu: 'pyra', Au: 'chrysos', Cu: 'aes' };
const MINERAL_DISPLAY_KEYS = new Set(['C', 'Pu', 'Au', 'Cu']);

function ArchDetailPanel({
  archIdx, names, frontier, snapshot, playerCore, substrate,
  selectedTargets, onToggleTarget,
  rivalCores, onToggleRival, partnerCores, onTogglePartner,
  onClose,
}) {
  if (archIdx === null || archIdx === undefined) return null;

  const name = names?.[archIdx] || `Island ${archIdx}`;
  const ctrl = snapshot?.controller?.[archIdx];
  const isOwned    = ctrl === playerCore;
  const fEntry     = frontier?.find(f => f.index === archIdx);
  const isOnFrontier = !!fEntry;
  const isTargeted = selectedTargets?.has(archIdx);
  const isRival    = rivalCores?.has(ctrl) && ctrl !== undefined;
  const isPartner  = partnerCores?.has(ctrl) && ctrl !== undefined;

  // Status badge
  const status = isOwned ? 'OWNED'
    : isOnFrontier ? 'FRONTIER'
    : ctrl !== undefined ? 'CONTACT'
    : 'TERRA INCOGNITA';
  const statusColor = isOwned ? '#7a8a5a'
    : isOnFrontier ? '#c47830'
    : ctrl !== undefined ? '#a09060'
    : '#5a4a3a';

  // Intelligence gate — only expose details for owned territory or formally-contacted polities.
  // Frontier islands that haven't been contacted yet are "uncharted waters."
  const contactedCores = snapshot?.contactedCores ?? [];
  const isContacted = isOwned || (ctrl !== undefined && contactedCores.includes(ctrl));

  // Minerals — from frontier entry or substrate fallback (only if contacted/owned)
  const minerals = isContacted ? (fEntry?.minerals ?? substrate?.[archIdx]?.minerals ?? {}) : {};
  const crop     = isContacted ? (fEntry?.crop ?? substrate?.[archIdx]?.crops?.primary_crop) : null;
  const mineralList = Object.entries(minerals)
    .filter(([k, v]) => MINERAL_DISPLAY_KEYS.has(k) && v > 0)
    .map(([k]) => MINERAL_LABELS[k] || k);

  return (
    <div style={{
      margin: '0 0 6px 0', padding: '8px 10px',
      background: '#100c06', border: `1px solid ${statusColor}44`,
      borderLeft: `2px solid ${statusColor}`,
      borderRadius: 2, fontFamily: MONO,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: '#d4b896', letterSpacing: '1px', textTransform: 'uppercase' }}>
          {name}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ fontSize: 7, color: statusColor, fontWeight: 700, letterSpacing: '1px' }}>
            {status}
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#5a4a3a',
            cursor: 'pointer', fontSize: 10, padding: '0 2px', fontFamily: MONO,
          }}>×</button>
        </div>
      </div>

      {/* Stats row — distance always visible; pop/tech/crop only after formal contact */}
      {(fEntry || isOwned) && (
        <div style={{ fontSize: 7, color: '#8a7a5a', display: 'flex', gap: 10, marginBottom: 4 }}>
          {fEntry?.distance !== undefined && <span>dist {fEntry.distance.toFixed(2)}</span>}
          {isContacted && fEntry?.pop !== undefined && <span>pop {(fEntry.pop / 1000).toFixed(1)}k</span>}
          {isContacted && fEntry?.tech !== undefined && <span>tech {fEntry.tech}</span>}
          {isContacted && crop && <span>{crop}</span>}
          {isContacted && (() => {
            const fs = fEntry?.fisheryStock ?? snapshot?.fisheryStock?.[archIdx];
            return fs !== undefined && fs < 0.8 ? (
              <span style={{ color: fs < 0.3 ? '#a04030' : fs < 0.6 ? '#c47830' : '#8a7a2a' }}>
                fish {Math.round(fs * 100)}%
              </span>
            ) : null;
          })()}
          {isOwned && (() => {
            const ch = snapshot?.cropHealth?.[archIdx];
            return ch !== undefined && ch < 0.95 ? (
              <span style={{ color: ch < 0.4 ? '#a04030' : ch < 0.7 ? '#c47830' : '#8a7a2a' }}>
                crop {Math.round(ch * 100)}%
              </span>
            ) : null;
          })()}
          {!isContacted && isOnFrontier && (
            <span style={{ color: '#4a3a24', fontStyle: 'italic' }}>uncharted waters</span>
          )}
        </div>
      )}

      {/* Mineral badges */}
      {mineralList.length > 0 && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
          {mineralList.map(m => (
            <div key={m} style={{
              fontSize: 6, padding: '1px 5px', borderRadius: 2,
              background: '#1a1408', border: '1px solid #3a2a14',
              color: '#c47830', letterSpacing: '0.5px', textTransform: 'uppercase',
            }}>{m}</div>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {isOnFrontier && (
          <button onClick={() => onToggleTarget(archIdx)} style={{
            padding: '2px 8px', fontSize: 7, fontFamily: MONO, cursor: 'pointer', borderRadius: 2,
            background: isTargeted ? '#1a0e04' : '#0a0804',
            border: `1px solid ${isTargeted ? '#c47830' : '#3a2a14'}`,
            color: isTargeted ? '#c47830' : '#6a5a3a',
            letterSpacing: '0.5px', fontWeight: isTargeted ? 700 : 400,
          }}>{isTargeted ? '⚔ TARGETED' : '⚔ TARGET'}</button>
        )}
        {ctrl !== undefined && ctrl !== playerCore && (
          <>
            <button onClick={() => onToggleRival(ctrl)} style={{
              padding: '2px 8px', fontSize: 7, fontFamily: MONO, cursor: 'pointer', borderRadius: 2,
              background: isRival ? '#1a0804' : '#0a0804',
              border: `1px solid ${isRival ? '#a04030' : '#3a2a14'}`,
              color: isRival ? '#c05040' : '#6a5a3a',
              letterSpacing: '0.5px',
            }}>{isRival ? '✕ RIVAL' : 'RIVAL'}</button>
            <button onClick={() => onTogglePartner(ctrl)} style={{
              padding: '2px 8px', fontSize: 7, fontFamily: MONO, cursor: 'pointer', borderRadius: 2,
              background: isPartner ? '#0a1408' : '#0a0804',
              border: `1px solid ${isPartner ? '#508040' : '#3a2a14'}`,
              color: isPartner ? '#70a060' : '#6a5a3a',
              letterSpacing: '0.5px',
            }}>{isPartner ? '✓ PARTNER' : 'PARTNER'}</button>
          </>
        )}
      </div>
    </div>
  );
}


export default function TurnDashboard({
  snapshot, frontier, names, playerCore,
  activeFocus, onSetFocus,
  selectedTargets, onToggleTarget,
  embargoTargets, onToggleEmbargo,
  rivalCores, onToggleRival,
  partnerCores, onTogglePartner,
  culturePolicyCI, culturePolicyIO, onSetCulturePolicy,
  sovFocusTargets, prevSovereignty, onToggleSovFocus,
  scoutActive, onToggleScout,
  // Selected arch from globe click (Phase 4)
  selectedArch, onSelectArch,
  substrate,
}) {
  const ps = snapshot?.playerStats;

  const ownedArchs = [];
  if (snapshot?.controller && playerCore !== undefined) {
    for (let i = 0; i < snapshot.controller.length; i++) {
      if (snapshot.controller[i] === playerCore) ownedArchs.push(i);
    }
  }

  const activeFocusDef = FOCUSES.find(f => f.key === activeFocus);
  const alloc = activeFocusDef?.alloc;

  return (
    <div style={S.panel}>

      {/* ── Arch Detail Panel (globe click) ── */}
      {selectedArch !== null && selectedArch !== undefined && (
        <div style={{ padding: '6px 8px 0', flexShrink: 0 }}>
          <ArchDetailPanel
            archIdx={selectedArch}
            names={names}
            frontier={frontier}
            snapshot={snapshot}
            playerCore={playerCore}
            substrate={substrate}
            selectedTargets={selectedTargets}
            onToggleTarget={onToggleTarget}
            rivalCores={rivalCores}
            onToggleRival={onToggleRival}
            partnerCores={partnerCores}
            onTogglePartner={onTogglePartner}
            onClose={() => onSelectArch(selectedArch)}
          />
        </div>
      )}

      {/* ── National Focus ── */}
      <div style={S.section}>
        <div style={S.sectionTitle}>National Focus</div>
        <div style={{ display: 'flex', gap: 3 }}>
          {FOCUSES.map(f => {
            const locked = f.minTech && (ps?.tech || 0) < f.minTech;
            return (
              <FocusCard
                key={f.key} focus={f}
                active={activeFocus === f.key}
                locked={locked}
                onSelect={() => onSetFocus(f.key)}
              />
            );
          })}
        </div>
        {/* Live allocation summary */}
        {alloc && (
          <div style={{
            marginTop: 7, fontSize: 7, color: '#6a5a3a',
            display: 'flex', justifyContent: 'center', gap: 8,
            letterSpacing: '0.5px',
          }}>
            <span>EXP <span style={{ color: '#c47830' }}>{alloc.expansion}%</span></span>
            <span>TEC <span style={{ color: '#a09060' }}>{alloc.techShare}%</span></span>
            <span>CON <span style={{ color: '#7a8a5a' }}>{alloc.consolidation}%</span></span>
          </div>
        )}
      </div>

      {/* ── Expansion Targets ── */}
      <div style={S.section}>
        <div style={S.sectionTitle}>
          Expansion Targets
          <span style={{ fontSize: 6, color: '#6a5a3a', fontWeight: 400, marginLeft: 6 }}>
            {selectedTargets.size} sel.
          </span>
        </div>
        <div style={{ maxHeight: 180, overflowY: 'auto' }}>
          {frontier.length === 0 && (
            <div style={{ color: '#5a4a3a', fontStyle: 'italic', fontSize: 8, padding: '4px 0' }}>
              No frontier reachable
            </div>
          )}
          {frontier.map(f => {
            const sel  = selectedTargets.has(f.index);
            const held = f.controller !== f.index;
            // Intelligence gate: only reveal pop/tech/crop/minerals for polities
            // we've formally contacted. Uncontacted frontier shows distance only.
            const known = f.contacted;
            return (
              <div key={f.index} style={S.targetItem(sel)}
                onClick={() => onToggleTarget(f.index)}>
                <div>
                  <div style={{ fontSize: 8, color: sel ? '#d4b896' : '#c8a878', fontWeight: sel ? 600 : 400 }}>
                    {sel ? '[×] ' : '[  ] '}{names[f.index]}
                    {held && <span style={{ color: '#a07030', marginLeft: 4 }}>(held)</span>}
                  </div>
                  {known ? (
                    <div style={{ fontSize: 7, color: '#6a5a3a', marginTop: 2 }}>
                      p{f.pop} · t{f.tech} · {f.crop}
                      {f.minerals.Cu && ' · Cu'}
                      {f.minerals.Au && ' · Au'}
                      {f.minerals.C > 0 && ' · C'}
                      {f.minerals.Pu && ' · Pu'}
                      {f.fisheryStock !== undefined && f.fisheryStock < 0.6 && (
                        <span style={{ color: f.fisheryStock < 0.3 ? '#a04030' : '#c47830' }}>
                          {' · fish '}{Math.round(f.fisheryStock * 100)}%
                        </span>
                      )}
                    </div>
                  ) : (
                    <div style={{ fontSize: 7, color: '#4a3a24', marginTop: 2, fontStyle: 'italic' }}>
                      uncharted waters
                    </div>
                  )}
                </div>
                <div style={{ fontSize: 7, color: '#6a5a3a', marginLeft: 6, flexShrink: 0 }}>
                  d={f.distance.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Intelligence ── */}
      <div style={S.section}>
        <div style={S.sectionTitle}>Intelligence</div>
        {(() => {
          const vis      = snapshot?.visibility;
          const contacts = snapshot?.contactedCores || [];
          const known    = vis ? vis.filter(v => v !== 'unknown').length : 0;
          const total    = vis ? vis.length : 0;
          return (
            <div style={S.statGrid}>
              <span style={S.statLabel}>Known world</span>
              <span style={S.statValue}>{known}/{total}</span>
              <span style={S.statLabel}>Contacted</span>
              <span style={S.statValue}>{contacts.length}</span>
              {contacts.slice(0, 3).map((cc, i) => {
                const cTech = snapshot?.tech?.[cc];
                const cPop  = snapshot?.polityPops?.[cc];
                return [
                  <span key={`l${i}`} style={{ ...S.statLabel, color: '#7a6a4a', fontSize: 7 }}>
                    {names[cc] || `Nation ${cc}`}
                  </span>,
                  <span key={`v${i}`} style={{ ...S.statValue, color: '#b8a080', fontSize: 7 }}>
                    t{cTech} p{cPop ? Math.round(cPop / 100) * 100 : '?'}
                  </span>,
                ];
              }).flat()}
              {contacts.length > 3 && <>
                <span style={{ ...S.statLabel, color: '#4a3a2a', fontSize: 7 }}>+{contacts.length - 3} more</span>
                <span style={S.statValue} />
              </>}
              <span style={S.statLabel}>Terra incognita</span>
              <span style={{ ...S.statValue, color: '#4a3a2a' }}>{total - known}</span>
            </div>
          );
        })()}
      </div>

      {/* ── Diplomacy ── */}
      {(snapshot?.contactedCores?.length > 0) && (
        <div style={S.section}>
          <div style={S.sectionTitle}>Diplomacy</div>
          <div style={{ maxHeight: 130, overflowY: 'auto' }}>
            {snapshot.contactedCores.map(cc => {
              const isRival   = rivalCores?.has(cc);
              const isPartner = partnerCores?.has(cc);
              const isEmbargo = embargoTargets?.has(cc);
              return (
                <div key={cc} style={{
                  padding: '3px 6px', marginBottom: 2, borderRadius: 2,
                  background: isRival ? '#1a0808' : isPartner ? '#0a1408' : '#0e0a06',
                  border: `1px solid ${isRival ? '#4a2020' : isPartner ? '#2a4a20' : '#1a1408'}`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <span style={{ fontSize: 7.5, color: '#c8a878' }}>{names[cc] || `Nation ${cc}`}</span>
                  <div style={{ display: 'flex', gap: 2 }}>
                    {[
                      { fn: onToggleRival,   active: isRival,   icon: '⚔', activeClr: '#c06040', activeBg: '#3a1010', activeBdr: '#6a3030', title: 'Rival' },
                      { fn: onTogglePartner, active: isPartner, icon: '◆', activeClr: '#80c060', activeBg: '#0a1a08', activeBdr: '#3a6a30', title: 'Partner' },
                      { fn: onToggleEmbargo, active: isEmbargo, icon: '✕', activeClr: '#c0a040', activeBg: '#1a1000', activeBdr: '#6a5020', title: 'Embargo' },
                    ].map(({ fn, active, icon, activeClr, activeBg, activeBdr, title }) => (
                      <button key={title} onClick={() => fn?.(cc)} title={title} style={{
                        padding: '1px 5px', fontSize: 7, fontFamily: MONO, cursor: 'pointer',
                        background: active ? activeBg : '#0a0804',
                        border: `1px solid ${active ? activeBdr : '#2a1f14'}`,
                        color: active ? activeClr : '#6a5a3a', borderRadius: 2,
                      }}>{icon}</button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: 6, color: '#3a2a1a', marginTop: 3 }}>
            ⚔ rival (+2.0 targeting) · ◆ partner (+30% trade, -3.0 targeting) · ✕ embargo (blocks trade)
          </div>
        </div>
      )}

      {/* ── Cultural Policy ── */}
      <div style={S.section}>
        <div style={S.sectionTitle}>
          Cultural Policy
          <span style={{ fontSize: 6, color: '#6a5a3a', fontWeight: 400, marginLeft: 6 }}>
            {ps?.cultureLabel || '—'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[
            { label: ['Collect.', 'Indiv.'],  key: 'ci', val: culturePolicyCI,
              hint: 'Collective: resist schism, hold piety. Individual: faster trade, innovation.' },
            { label: ['Inward',   'Outward'], key: 'io', val: culturePolicyIO,
              hint: 'Inward: consolidate holdings, resist conquest. Outward: stronger relay trade, wider contacts.' },
          ].map(({ label, key, val, hint }) => (
            <div key={key}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ fontSize: 6, color: '#6a5a3a', width: 42 }}>{label[0]}</span>
                <input type="range" min={-100} max={100}
                  value={Math.round((val || 0) * 100)}
                  onChange={e => onSetCulturePolicy?.(key, Number(e.target.value) / 100)}
                  style={{ flex: 1, accentColor: '#8a7a5a' }} />
                <span style={{ fontSize: 6, color: '#6a5a3a', width: 42, textAlign: 'right' }}>{label[1]}</span>
              </div>
              <div style={{ fontSize: 5.5, color: '#4a3a2a', marginTop: 2, lineHeight: 1.4, paddingLeft: 2 }}>
                {hint}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Operations ── */}
      <div style={S.section}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
          <div style={S.sectionTitle}>Operations</div>
          <button onClick={() => onToggleScout?.()} style={{
            padding: '2px 7px', fontSize: 7, fontFamily: MONO, cursor: 'pointer',
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
            <div style={{ fontSize: 6, color: '#6a5a3a', marginBottom: 3, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Sovereignty Focus
            </div>
            <div style={{ maxHeight: 90, overflowY: 'auto' }}>
              {ownedArchs.filter(i => i !== playerCore).map(i => {
                const focused = sovFocusTargets?.has(i);
                const sov     = snapshot?.sovereignty?.[i];
                const prevSov = prevSovereignty?.[i];
                const delta   = (sov !== undefined && prevSov !== undefined) ? sov - prevSov : 0;
                const arrow   = delta > 0.005 ? '↑' : delta < -0.005 ? '↓' : '';
                const arrowColor = delta > 0.005 ? '#5a8a4a' : '#a05030';
                return (
                  <div key={i} onClick={() => onToggleSovFocus?.(i)} style={{
                    padding: '2px 5px', marginBottom: 1, cursor: 'pointer', borderRadius: 2,
                    background: focused ? '#14100a' : '#0e0a06',
                    border: `1px solid ${focused ? '#4a3a20' : '#1a1408'}`,
                    display: 'flex', justifyContent: 'space-between', fontSize: 7.5,
                  }}>
                    <span style={{ color: focused ? '#d4b896' : '#8a7a5a' }}>
                      {focused ? '▣ ' : '□ '}{names[i]}
                    </span>
                    <span>
                      {arrow && <span style={{ color: arrowColor, fontSize: 7, marginRight: 2 }}>{arrow}</span>}
                      {sov !== undefined && (
                        <span style={{
                          color: sov > 0.6 ? '#7a8a5a' : sov > 0.3 ? '#8a7a3a' : '#a05030',
                          fontSize: 7,
                        }}>
                          {Math.round(sov * 100)}%
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export { FOCUSES };
