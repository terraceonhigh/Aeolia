import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import AeoliaLOD from './App.jsx';
import GameApp from './GameApp.jsx';
import Observatory from './Observatory.jsx';

function ModeSelector() {
  // null = menu, 'observatory' = history viewer, 'lod' = LOD terrain, 'game' = 1-player game
  const [mode, setMode] = useState(null);
  const [seed, setSeed] = useState(216089);  // primary calibrated seed — DF fires at year -200

  if (mode === 'lod') return <AeoliaLOD />;
  if (mode === 'observatory') return <Observatory seed={seed} onBack={() => setMode(null)} />;
  if (mode === 'game') return <GameApp seed={seed} onBack={() => setMode(null)} />;

  return (
    <div style={{
      width: '100%', height: '100vh', background: '#0a0804', color: '#c8a878',
      fontFamily: "'JetBrains Mono','Fira Code',monospace",
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{ textAlign: 'center', maxWidth: 480 }}>
        <div style={{
          fontSize: 9, color: '#8a7a5a', letterSpacing: '4px',
          textTransform: 'uppercase', marginBottom: 8,
        }}>
          4.6x Earth Circumference Ocean World
        </div>
        <div style={{
          fontSize: 28, color: '#d4b896', fontWeight: 700,
          letterSpacing: '6px', marginBottom: 24,
        }}>
          AEOLIA
        </div>

        <div style={{
          display: 'flex', gap: 16, justifyContent: 'center', marginBottom: 24,
          flexWrap: 'wrap',
        }}>
          <button onClick={() => setMode('observatory')} style={{
            padding: '14px 28px', fontSize: 11, fontFamily: 'inherit', cursor: 'pointer',
            background: '#14100a', border: '1px solid #3a2f1e', color: '#b8923a',
            letterSpacing: '2px', borderRadius: 4, minWidth: 180,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>OBSERVATORY</div>
            <div style={{ fontSize: 8, color: '#6a5a3a' }}>10,000-year history viewer</div>
          </button>

          <button onClick={() => setMode('game')} style={{
            padding: '14px 28px', fontSize: 11, fontFamily: 'inherit', cursor: 'pointer',
            background: '#1a1408', border: '1px solid #6a5430', color: '#d4b896',
            letterSpacing: '2px', borderRadius: 4, minWidth: 180,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>STRATEGY</div>
            <div style={{ fontSize: 8, color: '#8a7a5a' }}>1-player turn-based game</div>
          </button>

          <button onClick={() => setMode('lod')} style={{
            padding: '14px 28px', fontSize: 11, fontFamily: 'inherit', cursor: 'pointer',
            background: '#14100a', border: '1px solid #1a2010', color: '#6a8a6a',
            letterSpacing: '2px', borderRadius: 4, minWidth: 180,
          }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>TERRAIN</div>
            <div style={{ fontSize: 8, color: '#4a5a3a' }}>LOD globe renderer</div>
          </button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 8, color: '#6a5a3a', marginBottom: 4 }}>World Seed</div>
          <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))}
            style={{
              width: 120, padding: '6px 10px', fontSize: 11, fontFamily: 'inherit',
              background: '#14100a', border: '1px solid #2a1f14', color: '#d4b896',
              textAlign: 'center', letterSpacing: '2px', borderRadius: 3,
            }}
          />
        </div>

        <div style={{ fontSize: 7, color: '#4a3a2a', lineHeight: 1.6 }}>
          Archipelago world · 10,000-year simulation · nuclear deterrence equilibrium
        </div>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<ModeSelector />);
