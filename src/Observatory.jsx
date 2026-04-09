// ═══════════════════════════════════════════════════════════
// Observatory.jsx — Full-history civilization viewer
// 0-player mode. Runs the full 10,000-year simulation and
// presents interactive tech/population curves + event timeline.
// Designed for the Lanthier presentation demo.
// ═══════════════════════════════════════════════════════════

import { useState, useEffect, useMemo, useCallback } from 'react';
import { buildWorld } from './engine/world.js';
import { SimEngine, DEFAULT_PARAMS } from './engine/SimEngine.js';
import { POLITY_NAMES } from './engine/constants.js';
import { mulberry32 } from './engine/rng.js';

// ── Name shuffler (same as GameApp) ──────────────────────

function shuffleNames(seed) {
  const rng = mulberry32(((seed || 42) * 19 + 7) | 0);
  const shuffled = [...POLITY_NAMES];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  shuffled[0] = 'The Reach';
  shuffled[1] = 'The Lattice';
  return shuffled;
}

// ── Color palette for polities ────────────────────────────

const POLITY_COLORS = [
  '#b8923a', // amber — The Reach
  '#5a8a6a', // teal — The Lattice
  '#a04030', // red
  '#6a7aaa', // blue-grey
  '#9a7a3a', // dark gold
  '#7a5a9a', // purple
  '#4a8a8a', // cyan
  '#aa6a4a', // terracotta
  '#6a9a5a', // green
  '#8a5a7a', // mauve
];

// ── Era definitions ───────────────────────────────────────

const ERAS = [
  { name: 'Antiquity',      yearStart: -20000, yearEnd: -5000, color: '#2a1f14' },
  { name: 'Serial Contact', yearStart: -5000,  yearEnd: -2000, color: '#1f2a1a' },
  { name: 'Colonial',       yearStart: -2000,  yearEnd: -500,  color: '#2a2214' },
  { name: 'Industrial',     yearStart: -500,   yearEnd: -200,  color: '#1a2020' },
  { name: 'Nuclear',        yearStart: -200,   yearEnd: 0,     color: '#1a1a2a' },
];

// ── Shared styles ─────────────────────────────────────────

const FONT = "'JetBrains Mono','Fira Code',monospace";

const S = {
  root: {
    width: '100%', height: '100vh', background: '#0a0804',
    color: '#c8a878', fontFamily: FONT,
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
  },
  header: {
    padding: '10px 18px 8px',
    borderBottom: '1px solid #2a1f14',
    display: 'flex', alignItems: 'center', gap: 16,
    background: '#0e0b07',
    flexShrink: 0,
  },
  title: { fontSize: 13, fontWeight: 700, letterSpacing: '3px', color: '#d4b896' },
  subtitle: { fontSize: 8, color: '#6a5a3a', letterSpacing: '2px' },
  backBtn: {
    padding: '5px 14px', fontSize: 9, fontFamily: FONT,
    background: '#14100a', border: '1px solid #3a2a1a', color: '#8a7a5a',
    cursor: 'pointer', letterSpacing: '1px', borderRadius: 3,
    marginLeft: 'auto',
  },
  body: {
    flex: 1, display: 'flex', overflow: 'hidden',
  },
  left: {
    width: 200, borderRight: '1px solid #1a1410', display: 'flex',
    flexDirection: 'column', overflow: 'hidden', flexShrink: 0,
  },
  center: {
    flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden',
  },
  right: {
    width: 240, borderLeft: '1px solid #1a1410', display: 'flex',
    flexDirection: 'column', overflow: 'hidden', flexShrink: 0,
  },
  sectionLabel: {
    fontSize: 7, color: '#6a5a3a', letterSpacing: '2px', textTransform: 'uppercase',
    padding: '8px 12px 4px', borderBottom: '1px solid #1a1410',
  },
  chartWrap: {
    flex: 1, padding: '8px 12px', overflow: 'hidden', position: 'relative',
  },
};

// ── SVG Line Chart ────────────────────────────────────────

function LineChart({ series, width, height, yMax, yLabel, selectedIdx, onHover }) {
  if (!series || series.length === 0) return null;
  const PAD = { top: 8, right: 12, bottom: 24, left: 36 };
  const W = width - PAD.left - PAD.right;
  const H = height - PAD.top - PAD.bottom;
  const nPoints = series[0]?.data.length || 0;
  if (nPoints < 2) return null;

  const xScale = (i) => PAD.left + (i / (nPoints - 1)) * W;
  const yScale = (v) => PAD.top + H - (v / yMax) * H;

  // Tick marks
  const yTicks = [0, yMax * 0.25, yMax * 0.5, yMax * 0.75, yMax];

  return (
    <svg width={width} height={height} style={{ overflow: 'visible' }}>
      {/* Grid lines */}
      {yTicks.map((v, i) => (
        <line key={i}
          x1={PAD.left} y1={yScale(v)} x2={PAD.left + W} y2={yScale(v)}
          stroke="#2a1f14" strokeWidth={0.5}
        />
      ))}
      {/* Era bands */}
      {ERAS.map((era, i) => {
        // Map year to index approximation
        const totalYears = 20000;
        const x1 = PAD.left + Math.max(0, (-era.yearStart - 20000) / totalYears * -W + W * (20000 + era.yearStart) / totalYears);
        const x2 = PAD.left + Math.max(0, (20000 + era.yearEnd) / totalYears * W);
        if (x2 <= PAD.left) return null;
        return (
          <rect key={i}
            x={Math.max(PAD.left, x1)} y={PAD.top}
            width={Math.min(W, x2) - Math.max(PAD.left, x1)} height={H}
            fill={era.color} opacity={0.4}
          />
        );
      })}
      {/* Y-axis labels */}
      {yTicks.filter((_, i) => i > 0).map((v, i) => (
        <text key={i} x={PAD.left - 4} y={yScale(v) + 3}
          textAnchor="end" fill="#6a5a3a" fontSize={7} fontFamily={FONT}>
          {v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toFixed(v < 10 ? 1 : 0)}
        </text>
      ))}
      {/* Y label */}
      <text x={8} y={PAD.top + H / 2} textAnchor="middle" fill="#4a3a2a"
        fontSize={7} fontFamily={FONT} transform={`rotate(-90, 8, ${PAD.top + H / 2})`}>
        {yLabel}
      </text>
      {/* Series lines */}
      {series.map((s, si) => {
        const pts = s.data.map((v, i) => `${xScale(i)},${yScale(Math.min(v, yMax))}`).join(' ');
        return (
          <polyline key={si} points={pts}
            fill="none" stroke={s.color} strokeWidth={1.5} opacity={0.85}
            strokeLinejoin="round"
          />
        );
      })}
      {/* Selected tick line */}
      {selectedIdx !== null && selectedIdx >= 0 && (
        <line
          x1={xScale(selectedIdx)} y1={PAD.top}
          x2={xScale(selectedIdx)} y2={PAD.top + H}
          stroke="#c8a878" strokeWidth={1} strokeDasharray="3,2" opacity={0.7}
        />
      )}
      {/* X-axis: era labels */}
      {ERAS.map((era, i) => {
        const totalYears = 20000;
        const midYear = (era.yearStart + era.yearEnd) / 2;
        const xMid = PAD.left + (20000 + midYear) / totalYears * W;
        return (
          <text key={i} x={xMid} y={PAD.top + H + 14}
            textAnchor="middle" fill="#4a3a2a" fontSize={6} fontFamily={FONT}>
            {era.name}
          </text>
        );
      })}
    </svg>
  );
}

// ── Event timeline panel ──────────────────────────────────

function EventTimeline({ events, names, selectedYear, onSelectYear }) {
  if (!events || events.length === 0) {
    return (
      <div style={{ padding: 12, fontSize: 8, color: '#4a3a2a' }}>
        No events recorded.
      </div>
    );
  }

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      {events.map((ev, i) => (
        <div key={i}
          onClick={() => onSelectYear(ev.year)}
          style={{
            padding: '6px 12px',
            borderBottom: '1px solid #1a1410',
            cursor: 'pointer',
            background: ev.year === selectedYear ? '#1a1410' : 'transparent',
            transition: 'background 0.15s',
          }}
        >
          <div style={{ fontSize: 7, color: '#6a5a3a', marginBottom: 2 }}>
            Y{20000 + ev.year}  •  {ev.year < 0 ? `${Math.abs(ev.year)} BP` : `${ev.year} AP`}
          </div>
          <div style={{ fontSize: 8, color: ev.color || '#c8a878', lineHeight: 1.4 }}>
            {ev.text}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Stats panel ───────────────────────────────────────────

function StatsPanel({ snapshot, names }) {
  if (!snapshot) return null;
  const cores = [...new Set(snapshot.controller)].sort((a, b) => a - b);
  const polityData = cores.map(c => {
    const arches = snapshot.controller.reduce((n, ctrl, j) => ctrl === c ? n + 1 : n, 0);
    const pop = snapshot.pop.reduce((s, p, j) => snapshot.controller[j] === c ? s + p : s, 0);
    const tech = snapshot.tech[c] || 0;
    return { c, arches, pop, tech, name: names[c] || `Nation ${c}` };
  }).sort((a, b) => b.pop - a.pop).slice(0, 8);

  const worldPop = snapshot.pop.reduce((s, v) => s + v, 0);

  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #1a1410' }}>
        <div style={{ fontSize: 7, color: '#6a5a3a', marginBottom: 4 }}>YEAR</div>
        <div style={{ fontSize: 13, color: '#d4b896', letterSpacing: '1px' }}>
          {snapshot.year < 0 ? `${Math.abs(snapshot.year)} BP` : `${snapshot.year} AP`}
        </div>
        <div style={{ fontSize: 8, color: '#6a5a3a', marginTop: 2 }}>
          World pop: {(worldPop / 1000).toFixed(1)}k
        </div>
        <div style={{ fontSize: 8, color: '#6a5a3a' }}>
          Polities: {cores.length}
        </div>
      </div>
      {polityData.map((p, i) => (
        <div key={p.c} style={{
          padding: '5px 12px', borderBottom: '1px solid #150f09',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <div style={{
            width: 6, height: 6, borderRadius: 1, flexShrink: 0,
            background: POLITY_COLORS[i % POLITY_COLORS.length],
          }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 8, color: '#c8a878', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.name}
            </div>
            <div style={{ fontSize: 7, color: '#6a5a3a' }}>
              T{p.tech.toFixed(1)}  ·  {p.arches} arch  ·  pop {(p.pop / 1000).toFixed(1)}k
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main Observatory component ────────────────────────────

export default function Observatory({ seed, onBack }) {
  const [status, setStatus] = useState('loading'); // loading | ready
  const [historyData, setHistoryData] = useState(null);
  const [selectedIdx, setSelectedIdx] = useState(0);

  const names = useMemo(() => shuffleNames(seed), [seed]);

  // Run the full simulation on mount
  useEffect(() => {
    setStatus('loading');
    // Use setTimeout to let the "loading" render paint first
    const tid = setTimeout(() => {
      try {
        const world = buildWorld(seed);
        const engine = new SimEngine(
          { archs: world.archs, plateauEdges: world.plateauEdges, seed: world.seed, substrate: world.substrate },
          DEFAULT_PARAMS,
          null  // no player
        );
        engine.skipToTick(400);

        // Collect data we need for charts
        const timeline = engine.timeline;

        // Find top polities by final population
        const finalController = [...engine.controller];
        const finalPop = Array.from(engine.pop);
        const finalTech = Array.from(engine.tech);

        const coreSet = new Set(finalController);
        const polityFinalPop = {};
        for (const c of coreSet) {
          polityFinalPop[c] = 0;
          for (let j = 0; j < finalPop.length; j++) {
            if (finalController[j] === c) polityFinalPop[c] += finalPop[j];
          }
        }

        // Top 8 polities by final pop
        const topCores = [...coreSet]
          .sort((a, b) => polityFinalPop[b] - polityFinalPop[a])
          .slice(0, 8);

        // Build time-series data for each top polity
        // For each timeline entry, compute max tech and total pop per polity
        const polityTechSeries = topCores.map(core => ({
          core,
          name: names[core] || `Nation ${core}`,
          color: POLITY_COLORS[topCores.indexOf(core) % POLITY_COLORS.length],
          data: timeline.map(entry => {
            // At this tick, what was the tech of this core?
            return entry.tech[core] || 0;
          }),
        }));

        const polityPopSeries = topCores.slice(0, 5).map(core => ({
          core,
          name: names[core] || `Nation ${core}`,
          color: POLITY_COLORS[topCores.indexOf(core) % POLITY_COLORS.length],
          data: timeline.map(entry => {
            let pp = 0;
            for (let j = 0; j < entry.pop.length; j++) {
              if (entry.controller[j] === core) pp += entry.pop[j];
            }
            return pp;
          }),
        }));

        // World population series
        const worldPopSeries = [{
          core: -1,
          name: 'World',
          color: '#4a3a2a',
          data: timeline.map(entry => entry.pop.reduce((s, v) => s + v, 0)),
        }];

        // Build major event list for the timeline panel
        const events = [];

        // Era transitions
        const YEAR_ERA = [
          { year: -5000, text: 'Serial Contact Era begins', color: '#a09060' },
          { year: -2000, text: 'Colonial Era begins', color: '#8a7a5a' },
          { year: -500,  text: 'Industrial Era begins', color: '#7a8a6a' },
          { year: -200,  text: 'Nuclear Era begins', color: '#8a4040' },
        ];
        for (const ev of YEAR_ERA) events.push(ev);

        // Scrambles
        if (engine.scrambleOnset !== null) {
          const tick = engine.scrambleOnset;
          const year = -20000 + tick * 50;
          events.push({ year, text: 'Naphtha Scramble begins', color: '#8a6a3a' });
        }
        if (engine.puScrambleOnset !== null) {
          const tick = engine.puScrambleOnset;
          const year = -20000 + tick * 50;
          events.push({ year, text: 'Pyra Scramble begins', color: '#7a1a1a' });
        }

        // Dark Forest
        if (engine.dfYear !== null) {
          events.push({
            year: engine.dfYear,
            text: `Dark Forest detection (${names[engine.dfArch] || 'unknown'} ↔ ${names[engine.dfDetector] || 'unknown'})`,
            color: '#a04040',
          });
        }

        // Major absorptions (top 10 by tick)
        const bigAbsorptions = engine.expansionLog
          .filter(e => e.resource_driven || e.tech_gap > 2)
          .slice(0, 20);
        for (const e of bigAbsorptions) {
          const year = -20000 + e.tick * 50;
          events.push({
            year,
            text: `${names[e.core] || `Nation ${e.core}`} absorbed ${names[e.target] || `arch ${e.target}`}`,
            color: '#5a4a2a',
          });
        }

        // Sort all events by year
        events.sort((a, b) => a.year - b.year);

        // Compute max values for chart scaling
        const maxTech = Math.ceil(Math.max(...polityTechSeries.flatMap(s => s.data), 10));
        const maxPop = Math.ceil(Math.max(...worldPopSeries[0].data) * 1.05);

        setHistoryData({
          timeline,
          polityTechSeries,
          polityPopSeries,
          worldPopSeries,
          events,
          maxTech,
          maxPop,
          dfYear: engine.dfYear,
          scrambleOnset: engine.scrambleOnset,
          puScrambleOnset: engine.puScrambleOnset,
          finalEngine: {
            controller: finalController,
            pop: finalPop,
            tech: finalTech,
          },
        });
        setSelectedIdx(timeline.length > 0 ? timeline.length - 1 : 0);
        setStatus('ready');
      } catch (err) {
        console.error('Observatory sim failed:', err);
        setStatus('error');
      }
    }, 50);
    return () => clearTimeout(tid);
  }, [seed]);

  // Derive snapshot at the selected timeline index
  const selectedSnapshot = useMemo(() => {
    if (!historyData || !historyData.timeline[selectedIdx]) return null;
    return historyData.timeline[selectedIdx];
  }, [historyData, selectedIdx]);

  const selectedYear = selectedSnapshot?.year ?? -20000;

  if (status === 'loading') {
    return (
      <div style={{ ...S.root, alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 9, color: '#6a5a3a', letterSpacing: '3px', marginBottom: 12 }}>
            RUNNING SIMULATION
          </div>
          <div style={{ fontSize: 11, color: '#b8923a', letterSpacing: '1px' }}>
            10,000 years of history...
          </div>
          <div style={{ fontSize: 8, color: '#4a3a2a', marginTop: 8 }}>
            Seed {seed}
          </div>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div style={{ ...S.root, alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: 9, color: '#a04030' }}>Simulation failed.</div>
        <button onClick={onBack} style={{ ...S.backBtn, marginLeft: 0, marginTop: 12 }}>
          ← BACK
        </button>
      </div>
    );
  }

  const { polityTechSeries, polityPopSeries, worldPopSeries, events, maxTech, maxPop } = historyData;

  return (
    <div style={S.root}>
      {/* Header */}
      <div style={S.header}>
        <div>
          <div style={S.title}>OBSERVATORY</div>
          <div style={S.subtitle}>
            SEED {seed} · 10,000-YEAR SIMULATION · {historyData.timeline.length} SNAPSHOTS
          </div>
        </div>
        <button onClick={onBack} style={S.backBtn}>← BACK</button>
      </div>

      {/* Main body */}
      <div style={S.body}>
        {/* Left: Event timeline */}
        <div style={S.left}>
          <div style={S.sectionLabel}>EVENTS</div>
          <EventTimeline
            events={events}
            names={names}
            selectedYear={selectedYear}
            onSelectYear={(year) => {
              if (!historyData) return;
              // Find closest timeline entry
              const idx = historyData.timeline.reduce((best, entry, i) => {
                return Math.abs(entry.year - year) < Math.abs(historyData.timeline[best].year - year) ? i : best;
              }, 0);
              setSelectedIdx(idx);
            }}
          />
        </div>

        {/* Center: Charts */}
        <div style={S.center}>
          {/* Tech chart */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderBottom: '1px solid #1a1410' }}>
            <div style={S.sectionLabel}>TECHNOLOGY LEVEL — TOP POLITIES</div>
            <div style={{ ...S.chartWrap, display: 'flex', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, height: '100%', minHeight: 0 }}>
                <AutoSizeChart>
                  {(w, h) => (
                    <LineChart
                      series={polityTechSeries}
                      width={w} height={h}
                      yMax={maxTech}
                      yLabel="Tech"
                      selectedIdx={selectedIdx}
                    />
                  )}
                </AutoSizeChart>
              </div>
              {/* Legend */}
              <div style={{ width: 100, paddingLeft: 8, paddingTop: 4, flexShrink: 0 }}>
                {polityTechSeries.slice(0, 6).map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                    <div style={{ width: 12, height: 2, background: s.color, flexShrink: 0 }} />
                    <div style={{
                      fontSize: 7, color: '#8a7a5a', overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {s.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Population chart */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={S.sectionLabel}>POPULATION — WORLD + MAJOR POLITIES</div>
            <div style={{ ...S.chartWrap, display: 'flex', alignItems: 'flex-start' }}>
              <div style={{ flex: 1, height: '100%', minHeight: 0 }}>
                <AutoSizeChart>
                  {(w, h) => (
                    <LineChart
                      series={[...worldPopSeries, ...polityPopSeries]}
                      width={w} height={h}
                      yMax={maxPop}
                      yLabel="Pop"
                      selectedIdx={selectedIdx}
                    />
                  )}
                </AutoSizeChart>
              </div>
              {/* Legend */}
              <div style={{ width: 100, paddingLeft: 8, paddingTop: 4, flexShrink: 0 }}>
                {[...worldPopSeries, ...polityPopSeries].slice(0, 6).map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                    <div style={{
                      width: 12, height: 2, flexShrink: 0,
                      background: i === 0 ? '#4a3a2a' : POLITY_COLORS[(i - 1) % POLITY_COLORS.length],
                    }} />
                    <div style={{
                      fontSize: 7, color: '#8a7a5a', overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {s.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Timeline scrubber */}
          <div style={{
            flexShrink: 0, padding: '10px 12px',
            borderTop: '1px solid #1a1410', background: '#0e0b07',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4,
            }}>
              <div style={{ fontSize: 7, color: '#6a5a3a', letterSpacing: '1px', flexShrink: 0 }}>
                TIMELINE
              </div>
              <input
                type="range"
                min={0}
                max={historyData.timeline.length - 1}
                value={selectedIdx}
                onChange={e => setSelectedIdx(Number(e.target.value))}
                style={{ flex: 1, accentColor: '#b8923a', cursor: 'pointer' }}
              />
              <div style={{ fontSize: 8, color: '#b8923a', flexShrink: 0, minWidth: 80, textAlign: 'right' }}>
                {selectedYear < 0 ? `${Math.abs(selectedYear)} BP` : `${selectedYear} AP`}
              </div>
            </div>
            {/* Era markers */}
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingLeft: 60, paddingRight: 88 }}>
              {ERAS.map((era, i) => (
                <div key={i} style={{ fontSize: 6, color: '#4a3a2a', letterSpacing: '0.5px' }}>
                  {era.name.split(' ')[0]}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Stats at selected tick */}
        <div style={S.right}>
          <div style={S.sectionLabel}>POLITY STANDINGS</div>
          {selectedSnapshot && (
            <StatsPanel snapshot={selectedSnapshot} names={names} />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Auto-sizing wrapper for SVG charts ────────────────────

function AutoSizeChart({ children }) {
  const [size, setSize] = useState({ w: 400, h: 200 });
  const ref = useCallback(node => {
    if (!node) return;
    const obs = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) setSize({ w: width, h: height });
      }
    });
    obs.observe(node);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ width: '100%', height: '100%' }}>
      {children(size.w, size.h)}
    </div>
  );
}
