// ═══════════════════════════════════════════════════════════
// TurnTimer.jsx — TOTP-style circular countdown timer
// SVG ring fills clockwise over duration, then fires onComplete.
// Click to advance immediately. Uses setInterval for reliability.
// ═══════════════════════════════════════════════════════════

import { useEffect, useRef, useState } from 'react';

const SIZE = 72;
const STROKE = 4;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const TICK_MS = 50; // update every 50ms

export default function TurnTimer({ duration, onComplete, paused, finished }) {
  const startRef = useRef(null);
  const intervalRef = useRef(null);
  const [progress, setProgress] = useState(0); // 0..1
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
  const ringColor = finished ? '#4a3a2a' : paused ? '#3a4a5a' : progress > 0.75 ? '#cc8844' : '#3a8a5a';

  return (
    <div
      onClick={() => { if (!finished && !completedRef.current) { completedRef.current = true; if (intervalRef.current) clearInterval(intervalRef.current); onCompleteRef.current(); } }}
      style={{
        cursor: finished ? 'default' : 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        position: 'relative', width: SIZE, height: SIZE,
        margin: '0 auto',
      }}
      title={finished ? 'Game over' : paused ? 'Paused — click to advance' : 'Click to advance now'}
    >
      <svg width={SIZE} height={SIZE} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background ring */}
        <circle cx={SIZE/2} cy={SIZE/2} r={RADIUS}
          fill="none" stroke="#0f1a28" strokeWidth={STROKE} />
        {/* Progress ring */}
        <circle cx={SIZE/2} cy={SIZE/2} r={RADIUS}
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
          fontSize: 16, fontWeight: 700,
          color: finished ? '#4a3a2a' : paused ? '#607888' : '#c8d4e0',
        }}>
          {finished ? '--' : paused ? '||' : secondsLeft}
        </div>
      </div>
    </div>
  );
}
