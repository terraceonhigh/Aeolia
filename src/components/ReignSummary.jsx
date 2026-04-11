// ═══════════════════════════════════════════════════════════
// ReignSummary.jsx — Terminal game report
// Shown when game ends (defeat at territory=0, or turn 340).
// Dispatch register: terse, consequential, source-tagged.
// ═══════════════════════════════════════════════════════════

import { useMemo } from 'react';

const S = {
  overlay: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(10,8,4,0.92)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 25,
  },
  card: {
    width: '90%', maxWidth: 780,
    background: '#0e0a06',
    border: '1px solid #4a3a2a',
    borderRadius: 6,
    overflow: 'auto',
    maxHeight: '92vh',
    fontFamily: "'JetBrains Mono','Fira Code',monospace",
  },
  header: {
    padding: '24px 28px 16px',
    borderBottom: '1px solid #4a3a2a',
    textAlign: 'center',
  },
  outcome: {
    fontSize: 16, fontWeight: 700, letterSpacing: '3px',
    textTransform: 'uppercase', marginBottom: 6,
  },
  subtitle: {
    fontSize: 9, color: '#8a7a5a', letterSpacing: '1px',
  },
  section: {
    padding: '14px 28px',
    borderBottom: '1px solid #1a140a',
  },
  sectionTitle: {
    fontSize: 10, fontWeight: 700, color: '#b8923a',
    letterSpacing: '1.5px', textTransform: 'uppercase',
    marginBottom: 10,
  },
  grid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px',
  },
  stat: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 9, lineHeight: 1.7,
  },
  label: { color: '#8a7a5a' },
  value: { color: '#d4b896', fontWeight: 600 },
  eventRow: {
    fontSize: 8.5, lineHeight: 1.8, color: '#9a8a6a',
    padding: '3px 0', borderBottom: '1px solid #14100a',
  },
  eventSource: {
    color: '#6a5a3a', fontWeight: 600, marginRight: 6,
  },
  narrative: {
    fontSize: 9, lineHeight: 1.9, color: '#b8a878',
    padding: '14px 28px 10px',
    borderBottom: '1px solid #1a140a',
    fontStyle: 'italic',
  },
  footer: {
    padding: '14px 28px',
    display: 'flex', justifyContent: 'flex-end', gap: 12,
    background: '#0a0804',
  },
  btn: (primary) => ({
    padding: '8px 28px', fontSize: 9, fontFamily: 'inherit',
    cursor: 'pointer', fontWeight: 600, letterSpacing: '1.5px',
    background: primary ? '#2a1f14' : '#14100a',
    border: `1px solid ${primary ? '#8a7a3a' : '#2a1f14'}`,
    color: primary ? '#d4b896' : '#6a5a3a',
    borderRadius: 3, textTransform: 'uppercase',
  }),
};

function outcomeText(ps, snapshot) {
  if (!ps || ps.territory === 0) {
    const year = snapshot?.year ?? 0;
    if (year > -5000) return { header: 'CIVILIZATION DISSOLVED', color: '#6a3020', body: 'Your last archipelago has fallen under foreign administration. The harbor walls still stand. The qahwa-houses are occupied by other people\'s merchants. In two generations, your institutional memory will be a substrate layer — something an archaeologist will find and wonder about.' };
    return { header: 'POLITY COLLAPSED', color: '#6a3020', body: 'Your territory was absorbed before the industrial era. The ocean is large and indifferent. Elsewhere, the relay trade continues without you.' };
  }
  const hegemons = snapshot?.dfHegemonPair;
  const isHegemon = hegemons && (hegemons[0] === snapshot._playerCore || hegemons[1] === snapshot._playerCore);
  if (isHegemon) {
    return { header: 'DOMINION ESTABLISHED', color: '#b8923a', body: 'The Strange Peace holds. Your naval intelligence has resolved the second-strike capability of your nuclear peer. Both civilizations hold the ocean in suspension — mutual annihilation is not a theoretical constraint but the governing condition of all statecraft. You have won the scramble for pyra. Winning means standing still across thousands of kilometers of dark water, watching.' };
  }
  if (ps.tech >= 9.0) {
    return { header: 'NUCLEAR CAPABILITY ACHIEVED', color: '#9a8a5a', body: 'Your polity has reached the nuclear threshold. Whether this makes you safer or more dangerous depends on who else has done the same. The ocean is smaller than it used to be.' };
  }
  if (ps.territory >= 5) {
    return { header: 'THE REALM ENDURES', color: '#8a9a6a', body: 'The simulation has concluded. Your archipelago holds its position — not dominant, not dissolved, but present. The relay trade knows your name. The administered networks include your merchants. In ten thousand years of ocean history, persistence is its own achievement.' };
  }
  return { header: 'SIMULATION CONCLUDED', color: '#8a7a5a', body: 'The simulation has run its course. Your polity survived. The ocean remembers those who persist.' };
}

function pickKeyEvents(eventLog, playerCore) {
  const events = [];
  // Find distinctive dispatch entries
  const firstExpansion = eventLog.find(e => e.source === 'ADMIRALTY' && /absorbed|expanded|seized/i.test(e.text));
  const firstContact = eventLog.find(e => e.source === 'CARTOGRAPHIC' && /contact|discovered/i.test(e.text));
  const dfEvent = eventLog.find(e => e.type === 'dark_forest_detected' || /dark forest|nuclear peer/i.test(e.text || ''));
  const lastTerritoryLost = [...eventLog].reverse().find(e => e.source === 'ADMIRALTY' && /lost|seized.*your/i.test(e.text));
  const eraTransition = [...eventLog].reverse().find(e => /era transition|guild charter|industrial|nuclear/i.test(e.text || ''));

  if (firstContact) events.push({ label: 'FIRST CONTACT', text: firstContact.text, year: firstContact.year });
  if (firstExpansion) events.push({ label: 'FIRST EXPANSION', text: firstExpansion.text, year: firstExpansion.year });
  if (eraTransition) events.push({ label: 'ERA MILESTONE', text: eraTransition.text, year: eraTransition.year });
  if (dfEvent) events.push({ label: 'DARK FOREST', text: dfEvent.text || 'Nuclear peer detected', year: dfEvent.year });
  if (lastTerritoryLost) events.push({ label: 'FINAL LOSS', text: lastTerritoryLost.text, year: lastTerritoryLost.year });

  return events.slice(0, 6);
}

export default function ReignSummary({ snapshot, eventLog, names, playerCore, focusHistory, onPlayAgain, onMainMenu }) {
  const ps = snapshot?.playerStats;
  const { header, color, body } = useMemo(() => outcomeText(ps, { ...snapshot, _playerCore: playerCore }), [ps, snapshot, playerCore]);
  const keyEvents = useMemo(() => pickKeyEvents(eventLog || [], playerCore), [eventLog, playerCore]);

  // Rank among polities by population
  const polityPops = snapshot?.polityPops || {};
  const sortedPops = Object.entries(polityPops).sort((a, b) => b[1] - a[1]);
  const rank = sortedPops.findIndex(([c]) => parseInt(c) === playerCore) + 1;
  const nPolities = snapshot?.nPolities || sortedPops.length;

  // Focus history summary
  const focusCounts = {};
  if (focusHistory && focusHistory.length > 0) {
    for (const f of focusHistory) {
      focusCounts[f] = (focusCounts[f] || 0) + 1;
    }
  }

  const polityName = names?.[playerCore] || `Polity ${playerCore}`;
  const turns = (snapshot?.tick || 60) - 60;
  const startYear = -17000;
  const endYear = snapshot?.year || 0;

  return (
    <div style={S.overlay}>
      <div style={S.card} onClick={e => e.stopPropagation()}>

        {/* Outcome header */}
        <div style={S.header}>
          <div style={{ ...S.outcome, color }}>{header}</div>
          <div style={S.subtitle}>
            {polityName} &middot; {turns} turns &middot; Year {endYear}
          </div>
        </div>

        {/* Narrative body */}
        <div style={S.narrative}>{body}</div>

        {/* Stats */}
        <div style={S.section}>
          <div style={S.sectionTitle}>Final Record</div>
          <div style={S.grid}>
            <div style={S.stat}><span style={S.label}>Population</span><span style={S.value}>{ps?.pop?.toLocaleString() || '—'}</span></div>
            <div style={S.stat}><span style={S.label}>Territory</span><span style={S.value}>{ps?.territory || 0} archipelagos</span></div>
            <div style={S.stat}><span style={S.label}>Technology</span><span style={S.value}>{ps?.tech || '—'}</span></div>
            <div style={S.stat}><span style={S.label}>Culture</span><span style={S.value}>{ps?.cultureLabel || '—'}</span></div>
            <div style={S.stat}><span style={S.label}>Contacts</span><span style={S.value}>{ps?.contacts || 0} polities</span></div>
            <div style={S.stat}><span style={S.label}>Piety</span><span style={S.value}>{ps?.piety !== undefined ? (ps.piety > 0.75 ? 'Fervent' : ps.piety > 0.5 ? 'Devout' : ps.piety > 0.25 ? 'Moderate' : 'Secular') : '—'}</span></div>
            <div style={S.stat}><span style={S.label}>Rank</span><span style={S.value}>#{rank || '—'} of {nPolities}</span></div>
            <div style={S.stat}><span style={S.label}>Dark Forest</span><span style={S.value}>{snapshot?.dfYear ? `Year ${snapshot.dfYear}` : 'Did not fire'}</span></div>
          </div>
        </div>

        {/* Key events */}
        {keyEvents.length > 0 && (
          <div style={S.section}>
            <div style={S.sectionTitle}>Key Events</div>
            {keyEvents.map((ev, i) => (
              <div key={i} style={S.eventRow}>
                <span style={S.eventSource}>{ev.label}</span>
                {ev.year && <span style={{ color: '#6a5a3a', marginRight: 6 }}>Year {ev.year}</span>}
                <span>{ev.text?.slice(0, 120)}{ev.text?.length > 120 ? '…' : ''}</span>
              </div>
            ))}
          </div>
        )}

        {/* Decision record (focus history) */}
        {Object.keys(focusCounts).length > 0 && (
          <div style={S.section}>
            <div style={S.sectionTitle}>Decision Record</div>
            <div style={S.grid}>
              {Object.entries(focusCounts).sort((a, b) => b[1] - a[1]).map(([focus, count]) => (
                <div key={focus} style={S.stat}>
                  <span style={S.label}>{focus.toUpperCase()}</span>
                  <span style={S.value}>{count} turns</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Buttons */}
        <div style={S.footer}>
          <button style={S.btn(false)} onClick={onMainMenu}>Main Menu</button>
          <button style={S.btn(true)} onClick={onPlayAgain}>Play Again</button>
        </div>
      </div>
    </div>
  );
}
