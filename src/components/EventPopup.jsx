// ═══════════════════════════════════════════════════════════
// EventPopup.jsx — Modal event notification
// Pauses auto-advance. Player clicks Continue to dismiss.
// ═══════════════════════════════════════════════════════════

const STYLES = {
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(10,8,4,0.80)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 20,
  },
  card: (accentColor) => ({
    width: 400, background: '#0e0a06',
    border: `1px solid ${accentColor}40`,
    borderLeft: `3px solid ${accentColor}`,
    borderRadius: 6, overflow: 'hidden',
    fontFamily: "'JetBrains Mono','Fira Code',monospace",
    boxShadow: `0 4px 32px ${accentColor}20, 0 8px 48px rgba(0,0,0,0.6)`,
  }),
  header: (accentColor) => ({
    padding: '14px 18px 10px',
    borderBottom: `1px solid ${accentColor}30`,
    display: 'flex', alignItems: 'center', gap: 10,
  }),
  icon: (accentColor) => ({
    fontSize: 20, color: accentColor, flexShrink: 0,
  }),
  title: (accentColor) => ({
    fontSize: 12, fontWeight: 700, color: accentColor,
    letterSpacing: '1.5px', textTransform: 'uppercase',
  }),
  body: {
    padding: '12px 18px',
    fontSize: 9, color: '#c8a878', lineHeight: 1.7,
  },
  footer: {
    padding: '10px 18px 14px',
    display: 'flex', justifyContent: 'flex-end',
  },
  button: (accentColor) => ({
    padding: '6px 20px', fontSize: 9, fontFamily: 'inherit',
    cursor: 'pointer', fontWeight: 600, letterSpacing: '1.5px',
    background: `${accentColor}15`,
    border: `1px solid ${accentColor}60`,
    color: accentColor, borderRadius: 3,
    textTransform: 'uppercase',
  }),
};

// ── Event type definitions ──────────────────────────────

const EVENT_DEFS = {
  first_contact: {
    icon: '◉',
    color: '#b8923a',
    title: 'First Contact',
    body: (data) => `Your traders have encountered ${data.name} — a ${data.culture} civilization with tech level ${data.tech}. Trade routes may now form between your peoples.`,
  },
  absorption: {
    icon: '⚔',
    color: '#8a7a3a',
    title: 'Territory Absorbed',
    body: (data) => `${data.name} has been brought under your control. Your domain now spans ${data.territory} archipelagos.`,
  },
  territory_lost: {
    icon: '⚠',
    color: '#a04030',
    title: 'Territory Lost',
    body: (data) => `${data.aggressor} has seized ${data.name} from your holdings.`,
  },
  era_transition: {
    icon: '◆',
    color: '#a09060',
    title: (data) => `${data.era} Era`,
    body: (data) => data.description,
  },
  tech_milestone: {
    icon: '◈',
    color: '#9a8a5a',
    title: 'Technology Milestone',
    body: (data) => data.description,
  },
  dark_forest: {
    icon: '⚠',
    color: '#8a2020',
    title: 'Dark Forest Contact',
    body: () => `Two nuclear-capable civilizations have detected each other across the ocean. The age of mutual annihilation begins. The world will never be the same.`,
  },
  defeat: {
    icon: '✦',
    color: '#6a3020',
    title: 'Civilization Fallen',
    body: () => `Your last archipelago has been seized. Your people are scattered, your culture absorbed. The ocean remembers no names.`,
  },
};

const ERA_DESCRIPTIONS = {
  'Serial Contact': 'Ocean-going vessels now connect distant archipelagos. Civilizations that were once isolated begin to learn of each other through trade and rumor.',
  'Colonial': 'Superior naval technology enables distant conquest. Stronger polities begin absorbing weaker neighbors across vast ocean distances.',
  'Industrial': 'Naphtha extraction transforms economies. Those who control fossil reserves gain enormous energy surpluses, accelerating technology and military power.',
  'Nuclear': 'The splitting of the atom. Civilizations with access to plutonium achieve devastating military capability. The Dark Forest looms.',
};

const TECH_MILESTONES = {
  2: { desc: 'Sail technology achieved. Your people can now project power across the plateau edges, absorbing neighboring archipelagos.' },
  5: { desc: 'Administered trade unlocked. Long-distance commerce now flows through your territory, generating energy surplus from far-flung partners.' },
  7: { desc: 'Naphtha exploitation begins. Your civilization can now extract fossil energy, powering rapid industrialization — but reserves are finite.' },
  9: { desc: 'Nuclear capability achieved. With access to plutonium, your civilization commands existential destructive power.' },
};

export default function EventPopup({ event, onDismiss }) {
  if (!event) return null;

  const def = EVENT_DEFS[event.type];
  if (!def) return null;

  const color = def.color;
  const title = typeof def.title === 'function' ? def.title(event.data) : def.title;
  const body = def.body(event.data);

  return (
    <div style={STYLES.overlay} onClick={onDismiss}>
      <div style={STYLES.card(color)} onClick={e => e.stopPropagation()}>
        <div style={STYLES.header(color)}>
          <span style={STYLES.icon(color)}>{def.icon}</span>
          <span style={STYLES.title(color)}>{title}</span>
        </div>
        <div style={STYLES.body}>{body}</div>
        <div style={STYLES.footer}>
          <button style={STYLES.button(color)} onClick={onDismiss}>
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}

export { ERA_DESCRIPTIONS, TECH_MILESTONES };
