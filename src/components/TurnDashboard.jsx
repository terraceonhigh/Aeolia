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

// ── Shared palette helpers (Calçada Light — Portuguese limestone + basalt) ──
// Bacalhau's calcada theme: bg #ece6dc / fg #2b2b2b / border #c0b9ad.
// Source colors (admiralty red, merchant gold, internal olive) keep register
// and read clearly against limestone — that's why the palette ports cleanly.
const BORDER = '1px solid #c0b9ad';
const BG_PANEL = 'linear-gradient(180deg,#ece6dc,#e2dbd0)';

// ── National Focus definitions ───────────────────────────────

const FOCUSES = [
  { key: 'expand',   icon: '⚔', label: 'Expand',   color: '#c47830', desc: 'Aggressive growth',     alloc: { expansion: 65, techShare: 20, consolidation: 15 } },
  { key: 'innovate', icon: '◈', label: 'Innovate',  color: '#a09060', desc: 'Research push',          alloc: { expansion: 15, techShare: 65, consolidation: 20 } },
  { key: 'fortify',  icon: '▣', label: 'Fortify',   color: '#7a8a5a', desc: 'Consolidate holdings',   alloc: { expansion: 10, techShare: 20, consolidation: 70 } },
  { key: 'balanced', icon: '◎', label: 'Balanced',  color: '#5a5a58', desc: 'Steady all fronts',      alloc: { expansion: 33, techShare: 34, consolidation: 33 } },
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
            padding: '2px 7px', fontSize: 11, fontFamily: MONO,
            cursor: 'pointer', fontWeight: active ? 700 : 400,
            background: active ? '#d6cfc3' : '#d6cfc3',
            border: `1px solid ${active ? '#8a8478' : '#c0b9ad'}`,
            color: active ? '#1a1a1a' : '#7a7a76',
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
  isMobile,
}) {
  const ps = snapshot?.playerStats;
  const tick = snapshot?.tick || 40;
  const year = snapshot?.year;
  const gameYear = tick - 40;
  const eraName = !year ? 'Antiquity'
    : year < -5000 ? 'Antiquity' : year < -2000 ? 'Serial Contact'
    : year < -500  ? 'Colonial'  : year < -200  ? 'Industrial' : 'Nuclear';

  const activeFocusDef = FOCUSES.find(f => f.key === activeFocus);
  const alloc = activeFocusDef?.alloc;

  // Piety label + color
  const piety = ps?.piety;
  const piLabel = piety === undefined ? null
    : piety >= 0.75 ? 'fervent' : piety >= 0.50 ? 'devout' : piety >= 0.30 ? 'moderate' : 'secular';
  const piColor = piety === undefined ? '#6a6a66'
    : piety >= 0.75 ? '#b8923a' : piety >= 0.50 ? '#5a5a58' : '#7a7a76';

  const S = {
    label: { color: '#7a7a76', fontSize: isMobile ? 8.5 : 10, letterSpacing: '0.5px' },
    value: { color: '#1a1a1a', fontSize: isMobile ? 10 : 12, fontWeight: 600 },
    pipe:  { color: '#b0aaa0', padding: '0 6px', display: isMobile ? 'none' : 'block' },
  };

  return (
    <div style={{
      flexShrink: 0, borderBottom: BORDER,
      background: 'linear-gradient(180deg,#ece6dc,#e2dbd0)',
      fontFamily: MONO, display: 'flex', alignItems: isMobile ? 'center' : 'stretch',
      height: isMobile ? 'auto' : 62,
      flexWrap: isMobile ? 'wrap' : 'nowrap',
      padding: isMobile ? '4px 0' : 0,
    }}>

      {/* ── Turn / Era ── */}
      <div style={{
        padding: isMobile ? '2px 10px' : '0 16px', borderRight: isMobile ? 'none' : BORDER,
        display: 'flex', flexDirection: isMobile ? 'row' : 'column',
        justifyContent: 'center', alignItems: isMobile ? 'baseline' : 'flex-start',
        flexShrink: 0, minWidth: isMobile ? 0 : 130, gap: isMobile ? 6 : 0,
      }}>
        <div style={{ fontSize: isMobile ? 12 : 14, fontWeight: 700, color: '#1a1a1a', letterSpacing: '1px' }}>
          T{gameYear}<span style={{ color: '#aaa399', fontWeight: 400 }}>/340</span>
        </div>
        <div style={{ fontSize: isMobile ? 9 : 10, color: '#7a7a76', marginTop: isMobile ? 0 : 2, letterSpacing: '1.5px', textTransform: 'uppercase' }}>
          {eraName}
        </div>
      </div>

      {/* ── Stat strip ── */}
      {ps && (
        <div style={{
          flex: 1, padding: isMobile ? '2px 6px' : '0 14px', display: 'flex', alignItems: 'center',
          gap: 0, overflow: 'hidden', flexWrap: isMobile ? 'wrap' : 'nowrap',
        }}>
          {(() => {
            // Derive food security label from fishery + crop health
            const fH = ps.fisheryHealth ?? 1, cH = ps.cropHealth ?? 1;
            const foodAvg = (fH + cH) / 2;
            const foodLabel = foodAvg >= 0.85 ? 'Secure' : foodAvg >= 0.6 ? 'Stressed'
              : foodAvg >= 0.35 ? 'Scarce' : 'Famine';
            const foodColor = foodAvg >= 0.85 ? S.value.color : foodAvg >= 0.6 ? '#8a7a2a'
              : foodAvg >= 0.35 ? '#c47830' : '#a04030';
            // Institutional stability composite (extractiveness + grievance)
            const stabScore = (ps.extractiveness ?? 0) * 0.6 + (ps.avgGrievance ?? 0) * 0.4;
            const stabLabel = stabScore < 0.10 ? 'Stable' : stabScore < 0.25 ? 'Strained'
              : stabScore < 0.45 ? 'Restive' : 'Crisis';
            const stabColor = stabScore < 0.10 ? '#7a8a5a' : stabScore < 0.25 ? '#8a7a2a'
              : stabScore < 0.45 ? '#c47830' : '#a04030';

            // CULTURE color: civic (outward+individual) reads warm gold;
            // parochial reads neutral; subject (collective+inward) reads rust.
            // Maps the 3-way label produced by _cultureLabelFromPos.
            const cultLbl = ps.cultureLabel;
            const cultColor = cultLbl === 'civic'    ? '#c8a060'
                            : cultLbl === 'subject'  ? '#9a6a4a'
                                                     : '#5a5a58';

            // Pre-DF nuclear awareness (Twilight Struggle DEFCON analog)
            const nucAw = snapshot?.nuclearAwareness;
            const showTension = nucAw !== null && nucAw !== undefined;
            const tensionPct = showTension ? Math.round(nucAw * 100) : 0;
            const tensionColor = tensionPct < 40 ? '#8a7a2a' : tensionPct < 70 ? '#c47830' : '#a04030';

            return [
              ['POP',      ps.pop?.toLocaleString()],
              ['TECH',     ps.tech],
              ['TERR',     `${ps.territory} archs`],
              ['FOOD',     foodLabel],
              ['TRADE',    ps.tradeIncome > 0 ? ps.tradeIncome.toFixed(1) : '—'],
              ['NAPH',     ps.naphtha > 0 ? ps.naphtha.toFixed(1) : '—'],
              ['STABILITY', stabLabel],
              ['CONTACTS', ps.contacts],
              ['CULTURE',  ps.cultureLabel],
              ...(piLabel ? [['PIETY', piLabel]] : []),
              ...(snapshot?.pu_scramble_onset_tick && ps?.hasPu
                ? [['PYRA', ps.tech >= 9.0 ? 'WEAPONS' : 'DEPOSITS']] : []),
              ...(showTension ? [['TENSION', `${tensionPct}%`]] : []),
            ].map(([lbl, val], i, arr) => (
              <div key={lbl} style={{ display: 'flex', alignItems: 'center' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', padding: isMobile ? '1px 4px' : '0 10px' }}>
                  <div style={S.label}>{lbl}</div>
                  <div style={lbl === 'PIETY' ? { ...S.value, color: piColor }
                    : lbl === 'PYRA' ? { ...S.value, color: ps.tech >= 9.0 ? '#a04030' : '#7a6a2a' }
                    : lbl === 'TERR' ? { ...S.value, color: ps.territory <= 1 ? '#a04030' : ps.territory <= 3 ? '#c47830' : S.value.color }
                    : lbl === 'FOOD' ? { ...S.value, color: foodColor }
                    : lbl === 'STABILITY' ? { ...S.value, color: stabColor }
                    : lbl === 'TRADE' ? { ...S.value, color: ps.tradeIncome > 0 ? '#7a8a5a' : '#9a958c' }
                    : lbl === 'CULTURE' ? { ...S.value, color: cultColor }
                    : lbl === 'TENSION' ? { ...S.value, color: tensionColor }
                    : S.value}>{val}</div>
                  {lbl === 'PIETY' && piety !== undefined && (
                    <div style={{ width: 40, height: 2, borderRadius: 1, background: '#cbc3b6', marginTop: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.min(piety, 1) * 100}%`, background: piColor, transition: 'width 0.3s' }} />
                    </div>
                  )}
                  {lbl === 'FOOD' && (
                    <div style={{ width: 40, height: 2, borderRadius: 1, background: '#cbc3b6', marginTop: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${foodAvg * 100}%`, background: foodColor, transition: 'width 0.3s' }} />
                    </div>
                  )}
                  {lbl === 'STABILITY' && (
                    <div style={{ width: 40, height: 2, borderRadius: 1, background: '#cbc3b6', marginTop: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.min(stabScore / 0.6, 1) * 100}%`, background: stabColor, transition: 'width 0.3s' }} />
                    </div>
                  )}
                  {lbl === 'TENSION' && (
                    <div style={{ width: 40, height: 2, borderRadius: 1, background: '#cbc3b6', marginTop: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${Math.min(tensionPct / 30 * 100, 100)}%`, background: tensionColor, transition: 'width 0.3s' }} />
                    </div>
                  )}
                </div>
                {i < arr.length - 1 && <div style={S.pipe}>·</div>}
              </div>
            ));
          })()}
        </div>
      )}

      {/* ── Focus badge (hidden on mobile — info is in panel) ── */}
      {activeFocusDef && !isMobile && (
        <div style={{
          padding: '0 14px', borderLeft: BORDER, borderRight: BORDER,
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          alignItems: 'center', flexShrink: 0, minWidth: 90,
        }}>
          <div style={{ fontSize: 16, color: activeFocusDef.color, lineHeight: 1 }}>
            {activeFocusDef.icon}
          </div>
          <div style={{ fontSize: 10, fontWeight: 700, color: activeFocusDef.color, letterSpacing: '1px', marginTop: 2 }}>
            {activeFocusDef.label.toUpperCase()}
          </div>
          {alloc && (
            <div style={{ fontSize: 9, color: '#7a7a76', marginTop: 1, letterSpacing: '0.5px' }}>
              {alloc.expansion}/{alloc.techShare}/{alloc.consolidation}
            </div>
          )}
        </div>
      )}

      {/* ── Speed + Timer + Next Turn ── */}
      <div style={{
        padding: '0 14px', display: 'flex', alignItems: 'center',
        gap: 10, flexShrink: 0,
      }}>
        <SpeedBar speed={speed} onSetSpeed={onSetSpeed} />
        <TurnTimer
          key={timerKey}
          size={52}
          duration={timerDuration}
          onComplete={onAdvance}
          paused={timerPaused || speed === 0}
          finished={finished}
        />
        <button
          id="next-turn-btn"
          onClick={onAdvance}
          disabled={finished || timerPaused}
          style={{
            padding: '6px 12px',
            fontSize: 10.5,
            fontFamily: "'JetBrains Mono','Fira Code',monospace",
            fontWeight: 600,
            letterSpacing: '1.2px',
            cursor: (finished || timerPaused) ? 'default' : 'pointer',
            background: (finished || timerPaused) ? '#dad3c6' : '#dad3c6',
            border: `1px solid ${(finished || timerPaused) ? '#c0b9ad' : '#b0a99d'}`,
            color: (finished || timerPaused) ? '#b0aaa0' : '#5a5a48',
            borderRadius: 2,
            transition: 'all 0.15s',
            flexShrink: 0,
            lineHeight: 1.1,
            textAlign: 'center',
          }}
          title={timerPaused ? 'Resolve the current event to continue' : 'Commit to a 50-year tick'}
        >
          ADVANCE<br/><span style={{ fontSize: 9, opacity: 0.75, letterSpacing: '1px' }}>50 YEARS</span>
        </button>
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

export function FeedZone({ eventLog, pendingCards, cardHistory, onApplyCard, isMobile }) {
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
      background: 'linear-gradient(0deg,#e2dbd0,#ece6dc)',
      fontFamily: MONO, display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      height: isMobile ? 180 : 230,
    }}>

      {/* ── Dispatches ── */}
      <div style={{
        flex: isMobile ? '1 1 50%' : '0 0 55%', borderRight: isMobile ? 'none' : BORDER,
        borderBottom: isMobile ? BORDER : 'none',
        display: 'flex', flexDirection: 'column', overflow: 'hidden',
      }}>
        <div style={{
          flexShrink: 0, padding: '5px 14px 4px', borderBottom: '1px solid #d6cfc3',
          fontSize: 11, color: '#7a7a76', letterSpacing: '2px', textTransform: 'uppercase',
          fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>Dispatches</span>
          <div style={{ display: 'flex', gap: 2 }}>
            {DISPATCH_FILTERS.map(f => {
              const active = dispatchFilter === f.key;
              return (
                <button key={f.key} onClick={() => setDispatchFilter(f.key)} style={{
                  padding: '1px 4px', fontSize: 9, fontFamily: MONO,
                  cursor: 'pointer', fontWeight: active ? 700 : 400,
                  background: active ? '#d6cfc3' : 'transparent',
                  border: `1px solid ${active ? '#a0998d' : '#d6cfc3'}`,
                  color: active ? '#2b2b2b' : '#aaa399',
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
            <div style={{ color: '#aaa399', fontStyle: 'italic', fontSize: 11 }}>
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
            }[source] || ev.color || '#b0aaa0';
            return (
              <div key={i} style={{ paddingLeft: 7, borderLeft: `2px solid ${sourceColor}`, flexShrink: 0 }}>
                <div style={{ display: 'flex', gap: 5, alignItems: 'baseline' }}>
                  {source && (
                    <span style={{ color: sourceColor, fontSize: 10, fontWeight: 700, letterSpacing: '0.3px' }}>
                      {source}
                    </span>
                  )}
                  <span style={{ color: '#9a958c', fontSize: 10 }}>{ev.yearStr}</span>
                </div>
                <div style={{ color: '#4a4a48', fontSize: 10.5, lineHeight: 1.45, marginTop: 1 }}>
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
          flexShrink: 0, padding: '5px 14px 4px', borderBottom: '1px solid #d6cfc3',
          fontSize: 11, color: '#7a7a76', letterSpacing: '2px', textTransform: 'uppercase',
          fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>
            Situation
            {cardTab === 'active' && pendingCards?.length > 0 && (
              <span style={{ color: '#7a7a76', fontWeight: 400, marginLeft: 6, fontSize: 10 }}>
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
                  padding: '1px 5px', fontSize: 9, fontFamily: MONO,
                  cursor: 'pointer', fontWeight: active ? 700 : 400,
                  background: active ? '#d6cfc3' : 'transparent',
                  border: `1px solid ${active ? '#a0998d' : '#d6cfc3'}`,
                  color: active ? '#2b2b2b' : '#aaa399',
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
                <div style={{ color: '#aaa399', fontStyle: 'italic', fontSize: 11, padding: '4px 0' }}>
                  No active situations
                </div>
              )}
              {pendingCards?.map(card => (
                <div key={card.id} style={{
                  padding: '7px 9px', borderRadius: 3, flexShrink: 0,
                  background: '#ece6dc', border: '1px solid #b0a99d',
                }}>
                  <div style={{
                    fontSize: 11, color: '#1a1a1a', fontWeight: 700,
                    letterSpacing: '0.5px', marginBottom: 4,
                  }}>
                    {card.icon} {card.title}
                  </div>
                  <div style={{
                    fontSize: 10.5, color: '#5a5a58', lineHeight: 1.5, marginBottom: card.why ? 3 : 6,
                  }}>
                    {card.body}
                  </div>
                  {card.why && (
                    <div style={{
                      fontSize: 9.5, color: '#9a958c', fontStyle: 'italic',
                      lineHeight: 1.4, marginBottom: 5, paddingLeft: 2,
                    }}>
                      {card.why}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {card.actions.map((act, i) => {
                      // Surface mechanical side-effect: SET_FOCUS overrides aren't
                      // self-evident from a label like "EXPAND FISHERIES" → Exploit focus.
                      // Annotate the button so the player sees the consequence before clicking.
                      const focusHint = act.action?.type === 'SET_FOCUS'
                        ? (FOCUSES.find(f => f.key === act.action.focus) || null)
                        : null;
                      return (
                        <button key={i}
                          onClick={() => onApplyCard?.(card.id, act.action, act.label)}
                          title={focusHint ? `Sets National Focus → ${focusHint.label}` : undefined}
                          style={{
                            padding: '2px 7px', fontSize: 10, fontFamily: MONO,
                            cursor: 'pointer', fontWeight: 600, letterSpacing: '1px',
                            background: act.action ? '#d6cfc3' : '#e2dbd0',
                            border: `1px solid ${act.action ? '#a0998d' : '#c0b9ad'}`,
                            color: act.action ? '#2b2b2b' : '#7a7a76',
                            borderRadius: 2, textTransform: 'uppercase',
                            display: 'flex', alignItems: 'center', gap: 4,
                          }}
                        >
                          <span>{act.label}</span>
                          {focusHint && (
                            <span style={{
                              fontSize: 8.5, fontWeight: 700, letterSpacing: '0.3px',
                              color: focusHint.color, opacity: 0.95,
                              borderLeft: `1px solid ${focusHint.color}55`,
                              paddingLeft: 4, marginLeft: 1,
                            }}>
                              → {focusHint.label.toUpperCase()}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </>
          )}
          {cardTab === 'history' && (
            <>
              {(!cardHistory || cardHistory.length === 0) && (
                <div style={{ color: '#aaa399', fontStyle: 'italic', fontSize: 11, padding: '4px 0' }}>
                  No card history yet
                </div>
              )}
              {cardHistory?.slice().reverse().map((h, i) => (
                <div key={i} style={{
                  padding: '5px 8px', borderRadius: 2, flexShrink: 0,
                  background: '#e2dbd0', border: '1px solid #cbc3b6',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <span style={{ fontSize: 10.5, color: '#4a4a48', fontWeight: 600 }}>
                      {h.icon} {h.title}
                    </span>
                    <span style={{ fontSize: 9, color: '#aaa399' }}>{h.yearStr}</span>
                  </div>
                  <div style={{ fontSize: 9.5, color: '#7a7a76', marginTop: 2 }}>
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
    width: '100%', flexShrink: 0, borderLeft: BORDER,
    background: BG_PANEL,
    fontFamily: MONO,
    fontSize: 12, color: '#2b2b2b',
    display: 'flex', flexDirection: 'column',
    overflowY: 'auto', height: '100%',
  },
  section: {
    padding: '9px 12px', borderBottom: BORDER,
  },
  sectionTitle: {
    fontSize: 12, color: '#b8923a', letterSpacing: '2px',
    textTransform: 'uppercase', fontWeight: 600, marginBottom: 6,
  },
  statGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3px 10px',
    fontSize: 11, lineHeight: 1.5,
  },
  statLabel: { color: '#6a6a66' },
  statValue: { color: '#1a1a1a', fontWeight: 600, textAlign: 'right' },
  targetItem: (selected) => ({
    padding: '5px 8px', marginBottom: 3, borderRadius: 3, cursor: 'pointer',
    border: `1px solid ${selected ? '#8a8478' : '#c0b9ad'}`,
    background: selected ? '#d6cfc3' : '#e2dbd0',
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
  }),
};

function FocusCard({ focus, active, locked, onSelect }) {
  const alloc = focus.alloc;

  // Active: inverted — bright parchment text on prominently lit background
  // Inactive: heavily dimmed so active state reads clearly at a glance
  const bg     = active ? `${focus.color}38` : '#e2dbd0';
  const border = active ? focus.color : '#cbc3b6';
  const iconC  = active ? '#1a1a1a' : locked ? '#cbc3b6' : '#aaa399';
  const labelC = active ? '#2b2b2b' : locked ? '#cbc3b6' : '#9a958c';

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
        fontSize: 9, fontWeight: active ? 700 : 500, letterSpacing: '0.5px',
        color: labelC, marginTop: 2,
      }}>
        {focus.label.toUpperCase()}
      </div>
      {/* Allocation bar — three segments, bright when active, dimmed when inactive */}
      {alloc && (
        <div style={{ display: 'flex', marginTop: 5, height: active ? 4 : 2, borderRadius: 2, overflow: 'hidden', gap: 1, transition: 'height 0.15s' }}>
          <div style={{ flex: alloc.expansion,     background: active ? '#c47830' : locked ? '#cbc3b6' : '#b0a99d' }} />
          <div style={{ flex: alloc.techShare,     background: active ? '#a09060' : locked ? '#cbc3b6' : '#b8a96a' }} />
          <div style={{ flex: alloc.consolidation, background: active ? '#7a8a5a' : locked ? '#cbc3b6' : '#a8b88a' }} />
        </div>
      )}
      {/* Allocation percentages — shown on all cards, not just active */}
      {alloc && !active && !locked && (
        <div style={{ fontSize: 8, color: '#aaa399', marginTop: 2, letterSpacing: '0.3px' }}>
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

// Render a delta arrow + sign for a per-tick change. Returns null when
// the change is below the noise floor so arrows don't flicker every turn.
function DeltaArrow({ delta, threshold = 0.005, invert = false }) {
  if (delta == null || Math.abs(delta) < threshold) return null;
  const rising = delta > 0;
  // For grievance/extraction, rising is bad; for sovereignty, rising is good.
  // `invert` flips the color sense.
  const goodDirection = invert ? !rising : rising;
  const color = goodDirection ? '#5a8a4a' : '#a05030';
  return (
    <span style={{ color, fontSize: 9.5, marginLeft: 3, fontWeight: 700 }}>
      {rising ? '↑' : '↓'}
    </span>
  );
}

function ArchDetailPanel({
  archIdx, names, frontier, snapshot, playerCore, substrate,
  prevSovereignty, prevGrievance, prevExtractiveness,
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
    : '#9a958c';

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
      background: '#ece6dc', border: `1px solid ${statusColor}44`,
      borderLeft: `2px solid ${statusColor}`,
      borderRadius: 2, fontFamily: MONO,
    }}>
      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', letterSpacing: '1px', textTransform: 'uppercase' }}>
          {name}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ fontSize: 10, color: statusColor, fontWeight: 700, letterSpacing: '1px' }}>
            {status}
          </div>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: '#9a958c',
            cursor: 'pointer', fontSize: 13, padding: '0 2px', fontFamily: MONO,
          }}>×</button>
        </div>
      </div>

      {/* Stats row — distance always visible; pop/tech/crop only after formal contact */}
      {(fEntry || isOwned) && (
        <div style={{ fontSize: 10, color: '#6a6a66', display: 'flex', gap: 10, marginBottom: 4 }}>
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
            <span style={{ color: '#aaa399', fontStyle: 'italic' }}>uncharted waters</span>
          )}
        </div>
      )}

      {/* Mineral badges */}
      {mineralList.length > 0 && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
          {mineralList.map(m => (
            <div key={m} style={{
              fontSize: 9, padding: '1px 5px', borderRadius: 2,
              background: '#d6cfc3', border: '1px solid #b0a99d',
              color: '#c47830', letterSpacing: '0.5px', textTransform: 'uppercase',
            }}>{m}</div>
          ))}
        </div>
      )}

      {/* Institutional indicators for owned territories */}
      {isOwned && (() => {
        const gv = snapshot?.grievance?.[archIdx] ?? 0;
        const ext = snapshot?.extractiveness?.[archIdx] ?? 0;
        const sov = snapshot?.sovereignty?.[archIdx] ?? 1;
        const isHome = archIdx === playerCore;
        // Only show for non-home islands (home island has no grievance/extraction)
        if (isHome) return null;
        const gvColor = gv > 0.6 ? '#a04030' : gv > 0.35 ? '#c47830' : gv > 0.15 ? '#8a7a2a' : '#5a6a4a';
        const extColor = ext > 0.5 ? '#a04030' : ext > 0.3 ? '#c47830' : ext > 0.15 ? '#8a7a2a' : '#5a6a4a';
        const sovPct = Math.round(sov * 100);
        const sovColor = sov > 0.65 ? '#5a6a4a' : sov > 0.35 ? '#8a7a2a' : '#c47830';
        // Per-tick deltas (null when prev snapshot absent — first turn after select)
        const dGv  = prevGrievance       != null ? gv  - (prevGrievance[archIdx]       ?? gv)  : null;
        const dExt = prevExtractiveness  != null ? ext - (prevExtractiveness[archIdx]  ?? ext) : null;
        const dSov = prevSovereignty     != null ? sov - (prevSovereignty[archIdx]     ?? sov) : null;
        return (
          <div style={{ fontSize: 10, color: '#6a6a66', marginBottom: 4 }}>
            <div style={{ display: 'flex', gap: 10, marginBottom: 2 }}>
              <span style={{ color: gvColor }}>
                grievance {gv.toFixed(2)}
                <DeltaArrow delta={dGv} threshold={0.01} />
              </span>
              <span style={{ color: extColor }}>
                extraction {ext.toFixed(2)}
                <DeltaArrow delta={dExt} threshold={0.005} />
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ color: sovColor }}>
                sovereignty {sovPct}%
                <DeltaArrow delta={dSov} threshold={0.005} invert />
              </span>
              <div style={{ flex: 1, maxWidth: 50, height: 2, borderRadius: 1, background: '#cbc3b6', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${sovPct}%`, background: sovColor, transition: 'width 0.3s' }} />
              </div>
            </div>
          </div>
        );
      })()}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {isOnFrontier && (
          <button onClick={() => onToggleTarget(archIdx)} style={{
            padding: '2px 8px', fontSize: 10, fontFamily: MONO, cursor: 'pointer', borderRadius: 2,
            background: isTargeted ? '#f0d6c0' : '#d6cfc3',
            border: `1px solid ${isTargeted ? '#c47830' : '#b0a99d'}`,
            color: isTargeted ? '#c47830' : '#7a7a76',
            letterSpacing: '0.5px', fontWeight: isTargeted ? 700 : 400,
          }}>{isTargeted ? '⚔ TARGETED' : '⚔ TARGET'}</button>
        )}
        {ctrl !== undefined && ctrl !== playerCore && (
          <>
            <button onClick={() => onToggleRival(ctrl)} style={{
              padding: '2px 8px', fontSize: 10, fontFamily: MONO, cursor: 'pointer', borderRadius: 2,
              background: isRival ? '#ecd6d0' : '#d6cfc3',
              border: `1px solid ${isRival ? '#a04030' : '#b0a99d'}`,
              color: isRival ? '#c05040' : '#7a7a76',
              letterSpacing: '0.5px',
            }}>{isRival ? '✕ RIVAL' : 'RIVAL'}</button>
            <button onClick={() => onTogglePartner(ctrl)} style={{
              padding: '2px 8px', fontSize: 10, fontFamily: MONO, cursor: 'pointer', borderRadius: 2,
              background: isPartner ? '#dde6d0' : '#d6cfc3',
              border: `1px solid ${isPartner ? '#508040' : '#b0a99d'}`,
              color: isPartner ? '#70a060' : '#7a7a76',
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
  sovFocusTargets, prevSovereignty, prevGrievance, prevExtractiveness, onToggleSovFocus,
  scoutActive, onToggleScout,
  // Selected arch from globe click (Phase 4)
  selectedArch, onSelectArch,
  substrate,
  isMobile,
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

  const panelStyle = isMobile
    ? { ...S.panel, width: '100%' }
    : { ...S.panel, width: 280 };

  return (
    <div style={panelStyle}>

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
            prevSovereignty={prevSovereignty}
            prevGrievance={prevGrievance}
            prevExtractiveness={prevExtractiveness}
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
            marginTop: 7, fontSize: 10, color: '#7a7a76',
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
          <span style={{ fontSize: 9, color: '#7a7a76', fontWeight: 400, marginLeft: 6 }}>
            {selectedTargets.size} sel.
          </span>
        </div>
        <div style={{ maxHeight: 180, overflowY: 'auto' }}>
          {frontier.length === 0 && (
            <div style={{ color: '#9a958c', fontStyle: 'italic', fontSize: 11, padding: '4px 0' }}>
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
                  <div style={{ fontSize: 11, color: sel ? '#1a1a1a' : '#2b2b2b', fontWeight: sel ? 600 : 400 }}>
                    {sel ? '[×] ' : '[  ] '}{names[f.index]}
                    {held && <span style={{ color: '#a07030', marginLeft: 4 }}>(held)</span>}
                  </div>
                  {known ? (
                    <div style={{ fontSize: 10, color: '#7a7a76', marginTop: 2 }}>
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
                    <div style={{ fontSize: 10, color: '#aaa399', marginTop: 2, fontStyle: 'italic' }}>
                      uncharted waters
                    </div>
                  )}
                </div>
                <div style={{ fontSize: 10, color: '#7a7a76', marginLeft: 6, flexShrink: 0 }}>
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
                  <span key={`l${i}`} style={{ ...S.statLabel, color: '#7a7a76', fontSize: 10 }}>
                    {names[cc] || `Nation ${cc}`}
                  </span>,
                  <span key={`v${i}`} style={{ ...S.statValue, color: '#3a3a38', fontSize: 10 }}>
                    t{cTech} p{cPop ? Math.round(cPop / 100) * 100 : '?'}
                  </span>,
                ];
              }).flat()}
              {contacts.length > 3 && <>
                <span style={{ ...S.statLabel, color: '#aaa399', fontSize: 10 }}>+{contacts.length - 3} more</span>
                <span style={S.statValue} />
              </>}
              <span style={S.statLabel}>Terra incognita</span>
              <span style={{ ...S.statValue, color: '#aaa399' }}>{total - known}</span>
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
              // Relative tech comparison
              const ccTech = snapshot?.tech?.[cc] ?? 0;
              const playerTech = snapshot?.playerStats?.tech ?? 0;
              const techDelta = ccTech - playerTech;
              const techStr = Math.abs(techDelta) < 0.1 ? '=' : (techDelta > 0 ? `+${techDelta.toFixed(1)}` : techDelta.toFixed(1));
              const techColor = techDelta > 1 ? '#a04030' : techDelta > 0 ? '#c47830' : techDelta < -1 ? '#5a6a4a' : '#7a7a76';
              // Walt alignment (post-DF only)
              const alVal = snapshot?.alignment?.[cc] ?? 0;
              const postDF = !!snapshot?.dfYear;
              return (
                <div key={cc} style={{
                  padding: '3px 6px', marginBottom: 2, borderRadius: 2,
                  background: isRival ? '#ecd6d0' : isPartner ? '#dde6d0' : '#e2dbd0',
                  border: `1px solid ${isRival ? '#4a2020' : isPartner ? '#2a4a20' : '#d6cfc3'}`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <span style={{ fontSize: 10.5, color: '#2b2b2b' }}>{names[cc] || `Nation ${cc}`}</span>
                    <div style={{ fontSize: 9, color: '#9a958c', display: 'flex', gap: 6 }}>
                      <span style={{ color: techColor }}>tech {techStr}</span>
                      {postDF && Math.abs(alVal) > 0.05 && (
                        <span style={{ color: alVal > 0 ? '#6a7a9a' : '#9a6a6a' }}>
                          {alVal < -0.15 ? '← Reach' : alVal > 0.15 ? 'Lattice →' : 'non-aligned'}
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 2 }}>
                    {[
                      { fn: onToggleRival,   active: isRival,   icon: '⚔', activeClr: '#c06040', activeBg: '#e8c8c0', activeBdr: '#6a3030', title: 'Rival' },
                      { fn: onTogglePartner, active: isPartner, icon: '◆', activeClr: '#80c060', activeBg: '#d6e6cc', activeBdr: '#3a6a30', title: 'Partner' },
                      { fn: onToggleEmbargo, active: isEmbargo, icon: '✕', activeClr: '#c0a040', activeBg: '#ece2c8', activeBdr: '#6a5020', title: 'Embargo' },
                    ].map(({ fn, active, icon, activeClr, activeBg, activeBdr, title }) => (
                      <button key={title} onClick={() => fn?.(cc)} title={title} style={{
                        padding: '1px 5px', fontSize: 10, fontFamily: MONO, cursor: 'pointer',
                        background: active ? activeBg : '#d6cfc3',
                        border: `1px solid ${active ? activeBdr : '#c0b9ad'}`,
                        color: active ? activeClr : '#7a7a76', borderRadius: 2,
                      }}>{icon}</button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: 9, color: '#b0aaa0', marginTop: 3 }}>
            ⚔ rival (+2.0 targeting) · ◆ partner (+30% trade, -3.0 targeting) · ✕ embargo (blocks trade)
          </div>
        </div>
      )}

      {/* ── Cultural Policy ── */}
      <div style={S.section}>
        <div style={S.sectionTitle}>
          Cultural Policy
          <span style={{ fontSize: 9, color: '#7a7a76', fontWeight: 400, marginLeft: 6 }}>
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
                <span style={{ fontSize: 9, color: '#7a7a76', width: 42 }}>{label[0]}</span>
                <input type="range" min={-100} max={100}
                  value={Math.round((val || 0) * 100)}
                  onChange={e => onSetCulturePolicy?.(key, Number(e.target.value) / 100)}
                  style={{ flex: 1, accentColor: '#6a6a66' }} />
                <span style={{ fontSize: 9, color: '#7a7a76', width: 42, textAlign: 'right' }}>{label[1]}</span>
              </div>
              <div style={{ fontSize: 8.5, color: '#aaa399', marginTop: 2, lineHeight: 1.4, paddingLeft: 2 }}>
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
            padding: '2px 7px', fontSize: 10, fontFamily: MONO, cursor: 'pointer',
            background: scoutActive ? '#d6cfc3' : '#d6cfc3',
            border: `1px solid ${scoutActive ? '#8a8478' : '#c0b9ad'}`,
            color: scoutActive ? '#1a1a1a' : '#7a7a76', borderRadius: 2,
            fontWeight: scoutActive ? 600 : 400,
          }}>
            {scoutActive ? '◉ SCOUTING (−35% exp)' : '○ Scout'}
          </button>
        </div>
        {ownedArchs.length > 1 && (
          <>
            <div style={{ fontSize: 9, color: '#7a7a76', marginBottom: 3, letterSpacing: '1px', textTransform: 'uppercase' }}>
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
                    background: focused ? '#d6cfc3' : '#e2dbd0',
                    border: `1px solid ${focused ? '#a0998d' : '#d6cfc3'}`,
                    display: 'flex', justifyContent: 'space-between', fontSize: 10.5,
                  }}>
                    <span style={{ color: focused ? '#1a1a1a' : '#6a6a66' }}>
                      {focused ? '▣ ' : '□ '}{names[i]}
                    </span>
                    <span>
                      {arrow && <span style={{ color: arrowColor, fontSize: 10, marginRight: 2 }}>{arrow}</span>}
                      {sov !== undefined && (
                        <span style={{
                          color: sov > 0.6 ? '#7a8a5a' : sov > 0.3 ? '#8a7a3a' : '#a05030',
                          fontSize: 10,
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
