// ═══════════════════════════════════════════════════════════
// TurnTimer.jsx — Circular countdown timer
// SVG ring fills clockwise over duration, then fires onComplete.
// Click to advance immediately. Accepts `size` prop (default 72).
// ═══════════════════════════════════════════════════════════

import { useEffect, useRef, useState } from 'react';

const STROKE = 4;
const TICK_MS = 50;

export default function TurnTimer({ duration, onComplete, paused, finished, size = 72 }) {
  const RADIUS = (size - STROKE) / 2;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

  const startRef = useRef(null);
  const intervalRef = useRef(null);
  const [progress, setProgress] = useState(0);
  const [secondsLeft, setSecondsLeft] = useState(Math.ceil(duration / 1000));
  const completedRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (paused || finished) {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }
      return;
    }

    completedRef.current = false;
    startRef.current = Date.now();
    setProgress(0);
    setSecondsLeft(Math.ceil(duration / 1000));

    intervalRef.current = setInterval(() => {
      const elapsed = Date.now() - startRef.current;
      const p = Math.min(1, elapsed / duration);
      setProgress(p);
      setSecondsLeft(Math.max(0, Math.ceil((duration - elapsed) / 1000)));

      if (p >= 1 && !completedRef.current) {
        completedRef.current = true;
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        onCompleteRef.current();
      }
    }, TICK_MS);

    return () => { if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; } };
  }, [duration, paused, finished]);

  const dashOffset = CIRCUMFERENCE * (1 - progress);
  const ringColor = finished ? '#3a2a1a' : paused ? '#4a3a2a' : progress > 0.75 ? '#a07030' : '#8a7a3a';
  const fontSize = size < 50 ? Math.round(size * 0.22) : size < 60 ? 12 : 16;

  return (
    <div
      onClick={() => {
        if (!finished && !completedRef.current) {
          completedRef.current = true;
          if (intervalRef.current) clearInterval(intervalRef.current);
          onCompleteRef.current();
        }
      }}
      style={{
        cursor: finished ? 'default' : 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        position: 'relative', width: size, height: size,
        flexShrink: 0,
      }}
      title={finished ? 'Game over' : paused ? 'Paused — click to advance' : 'Click to advance now'}
    >
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={RADIUS}
          fill="none" stroke="#1a1408" strokeWidth={STROKE} />
        <circle cx={size/2} cy={size/2} r={RADIUS}
          fill="none" stroke={ringColor} strokeWidth={STROKE}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{ transition: 'stroke 0.3s' }}
        />
      </svg>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        fontFamily: "'JetBrains Mono','Fira Code',monospace",
      }}>
        <div style={{
          fontSize, fontWeight: 700,
          color: finished ? '#3a2a1a' : paused ? '#6a5a3a' : '#d4b896',
        }}>
          {finished ? '--' : paused ? '||' : secondsLeft}
        </div>
      </div>
    </div>
  );
}
