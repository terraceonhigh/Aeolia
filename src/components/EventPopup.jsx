// ═══════════════════════════════════════════════════════════
// EventPopup.jsx — Modal event notification
// Pauses auto-advance. Player clicks Continue to dismiss.
// All narrative text grounded in the Aeolia series bible.
// ═══════════════════════════════════════════════════════════

import {
  ERA_NARRATIVES,
  TECH_MILESTONE_NARRATIVES,
  getFirstContactBody,
  getDarkForestBody,
  getSchismBody,
} from '../engine/narrativeText.js';

const STYLES = {
  overlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(10,8,4,0.82)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 20,
  },
  card: (accentColor) => ({
    width: 420, background: '#0e0a06',
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
  titleWrap: {
    flex: 1,
  },
  title: (accentColor) => ({
    fontSize: 12, fontWeight: 700, color: accentColor,
    letterSpacing: '1.5px', textTransform: 'uppercase', lineHeight: 1.2,
  }),
  subtitle: {
    fontSize: 8, color: '#6a5a3a', letterSpacing: '1px',
    textTransform: 'uppercase', marginTop: 2,
  },
  body: {
    padding: '14px 18px',
    fontSize: 9, color: '#c8a878', lineHeight: 1.8,
  },
  secondaryBlock: (accentColor) => ({
    padding: '8px 18px 12px',
    fontSize: 8, color: '#8a7a5a', lineHeight: 1.6,
    borderTop: `1px solid ${accentColor}20`,
  }),
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

// ── Event type definitions ──────────────────────────────────

function buildEventDef(type, eventData, names, playerCore) {
  switch (type) {

    // ─ First Contact ───────────────────────────────────────
    case 'first_contact': {
      const d = eventData || {};
      const seed = (d.idx ?? 0) * 31 + (d.name?.charCodeAt(0) ?? 0);
      const contactTech = d.tech != null ? Number(d.tech) : 0;
      const secondaryText = contactTech >= 8.5
        ? `ADMIRALTY ASSESSMENT — This contact has been escalated to strategic-level review. Intelligence, diplomatic, and nuclear-posture assessments are ongoing. Epidemiological monitoring protocols are in effect. All trade discussions are suspended pending strategic review.`
        : `Your intelligence officers have designated this contact for ongoing assessment. Trade routes, diplomatic posture, and epidemiological monitoring protocols are being established.`;
      return {
        icon: '◉',
        color: '#b8923a',
        title: contactTech >= 8.5 ? 'Strategic Contact' : 'First Contact',
        subtitle: d.year ? `Year ${d.year}` : undefined,
        body: getFirstContactBody({
          name: d.name || 'an unknown civilization',
          culture: d.culture || 'unknown disposition',
          tech: contactTech.toFixed(1),
          crop: d.crop,
        }, seed),
        secondary: secondaryText,
      };
    }

    // ─ Absorption ──────────────────────────────────────────
    case 'absorption': {
      const d = eventData || {};
      return {
        icon: '⚔',
        color: '#8a7a3a',
        title: 'Territory Absorbed',
        subtitle: d.name,
        body: `${d.name} has been brought under your control through ${d.method || 'military force'}. Sovereignty is low — garrison costs will be high until the population is administered. Your domain now spans ${d.territory} archipelagos.`,
        secondary: d.crop
          ? `The acquisition brings ${d.crop} cultivation and whatever other resources the geological survey confirms. Sovereignty stabilization will take several turns.`
          : `Sovereignty stabilization will take several turns. Consider assigning administrative focus.`,
      };
    }

    // ─ Territory Lost ──────────────────────────────────────
    case 'territory_lost': {
      const d = eventData || {};
      return {
        icon: '⚠',
        color: '#a04030',
        title: 'Territory Seized',
        subtitle: d.name,
        body: `${d.aggressor} has seized ${d.name} from your holdings. A military intervention was insufficient or not attempted. Your domain has contracted.`,
        secondary: `This loss may create a vulnerability in your frontier. Intelligence assessment is recommended before further expansion in this region.`,
      };
    }

    // ─ Era Transition ──────────────────────────────────────
    case 'era_transition': {
      const d = eventData || {};
      const era = ERA_NARRATIVES[d.era] || ERA_NARRATIVES['Serial Contact'];
      return {
        icon: era.icon || '◆',
        color: era.color || '#a09060',
        title: `${d.era || 'New'} Era`,
        subtitle: 'Historical threshold crossed',
        body: era.long || d.description || '',
        secondary: era.short,
      };
    }

    // ─ Tech Milestone ──────────────────────────────────────
    case 'tech_milestone': {
      const d = eventData || {};
      const level = Math.round(d.tech || 0);
      const milestone = TECH_MILESTONE_NARRATIVES[level];
      if (milestone) {
        return {
          icon: '◈',
          color: milestone.color || '#9a8a5a',
          title: milestone.title,
          subtitle: `Technology level ${level}`,
          body: milestone.body,
          secondary: d.description || undefined,
        };
      }
      return {
        icon: '◈',
        color: '#9a8a5a',
        title: 'Technology Milestone',
        subtitle: `Level ${d.tech}`,
        body: d.description || `Your civilization has achieved technology level ${d.tech}.`,
      };
    }

    // ─ Dark Forest ─────────────────────────────────────────
    case 'dark_forest': {
      return {
        icon: '⚠',
        color: '#8a2020',
        title: 'Dark Forest Contact',
        subtitle: 'Nuclear peer detected — Deterrence Era begins',
        body: getDarkForestBody(names, playerCore),
        secondary: `Both civilizations now operate under the mutual-annihilation constraint. Territorial expansion between hegemons has effectively frozen — neither side can absorb the other's territory without triggering the deterrence cascade. The arms race continues: both powers invest in delivery systems, hardened installations, second-strike capability. The map is fixed; the capabilities are not. Intelligence operations are the primary instrument of statecraft from this point forward.`,
      };
    }

    // ─ Fishery Collapse ────────────────────────────────────
    case 'fishery_collapse': {
      const d = eventData || {};
      return {
        icon: '◌',
        color: '#3a5a6a',
        title: 'Fishery Collapse',
        subtitle: d.archName ? `${d.archName} stock critically depleted` : 'Marine stock depleted',
        body: `Fishery stock in your territory has fallen below viable levels. Sustained over-exploitation — population density exceeding the regenerative capacity of the marine ecosystem — has triggered a collapse. The fish are not gone; they have retreated beyond accessible range, and the remaining population is too sparse to support commercial harvest. Recovery, if it occurs, will take generations. Populations dependent on the fishery face caloric shortfall. Expect food deficit pressure and sovereignty stress in coastal territories.`,
        secondary: `The fishery collapse will cascade into the energy budget as a food deficit. Reducing extraction pressure — restricting population growth in affected archipelagos, or diverting fishing effort to other regions — allows partial stock recovery at a rate of roughly 8% per generation.`,
      };
    }

    // ─ Schism ──────────────────────────────────────────────
    case 'schism': {
      const d = eventData || {};
      const count = d.count || 1;
      const seed = (d.core ?? 0) * 13 + (d.year ?? 0);
      return {
        icon: '⊕',
        color: '#6a3a8a',
        title: 'Religious Schism',
        subtitle: count > 1 ? `${count} territories lost to fragmentation` : 'Peripheral territory lost to fragmentation',
        body: getSchismBody({ count, polityName: 'your realm' }, seed),
        secondary: `High piety without institutional depth has a historical failure mode: the center's claim to authority rests on religious legitimacy, and when that legitimacy fractures, so does the administrative order. Rebuilding sovereignty in the affected territories requires either military presence or doctrinal accommodation — the latter being the more durable solution and the more politically difficult one.`,
      };
    }

    // ─ Naphtha Scramble ────────────────────────────────────
    case 'naphtha_scramble': {
      return {
        icon: '⛏',
        color: '#8a6a3a',
        title: 'The Scramble Begins',
        subtitle: 'Naphtha deposits contested',
        body: `Multiple powers have confirmed the industrial value of naphtha deposits across the frontier. What was prospecting has become a race. The pattern is East India Company before it was British India — commercial penetration first, political control as a second step. The islands your geological surveys have flagged will not remain unclaimed.`,
        secondary: `Carbon-rich islands on your frontier are now high-priority targets. Commercial absorption precedes military control — but the outcome of inaction is the same.`,
      };
    }

    // ─ Pyra Scramble ───────────────────────────────────────
    case 'pyra_scramble': {
      return {
        icon: '⚠',
        color: '#7a1a1a',
        title: 'Fission Demonstrated',
        subtitle: 'Pyra becomes existential',
        body: `The first chain reaction has been achieved. Every pyra deposit on Aeolia changed strategic value in the same moment. Islands that were filed as "interesting geology" are now objects of military urgency. The populations living above those deposits had no say in what the geology under their feet was suddenly worth. The scramble for pyra will be faster and less commercially mediated than the naphtha scramble. Speed is the only variable.`,
        secondary: `Plutonium-bearing islands on your frontier are now the highest-value targets on the map. The window for acquisition is 150–250 years — three to five turns — before hegemon deterrence freezes the map.`,
      };
    }

    // ─ Epidemic Wave ───────────────────────────────────────
    case 'epidemic_wave': {
      const d = eventData || {};
      return {
        icon: '◉',
        color: '#6a4a2a',
        title: 'Epidemic Wave',
        subtitle: d.source ? `Origin: ${d.source}` : 'Trade-route propagation',
        body: `A disease event is propagating through the contact network. Population losses of ${d.mortality ? `${Math.round(d.mortality * 100)}%` : '5–20%'} are reported in affected archipelagos. The contact network that enables your trade also carries pathogens between populations that have had no prior exposure to each other's disease pools. The cost of connection, paid again.`,
        secondary: `Trade restrictions reduce propagation risk but interrupt revenue. Intelligence on affected partners will inform the best response.`,
      };
    }

    // ─ Defeat ──────────────────────────────────────────────
    case 'defeat': {
      return {
        icon: '✦',
        color: '#6a3020',
        title: 'Civilization Fallen',
        subtitle: undefined,
        body: `Your last archipelago has been seized. Your people are scattered — absorbed into the administrative structure of the conquering power, their language and institutional memory compressed into a substrate layer. The ocean remembers no names. A future archaeologist will find your harbor walls and your qahwa-house benches and wonder what you called yourselves.`,
        secondary: undefined,
      };
    }

    // ─ Simulation Complete (turn 340) ─────────────────────
    case 'simulation_complete': {
      return {
        icon: '◎',
        color: '#8a9a6a',
        title: 'End of Record',
        subtitle: 'The simulation has concluded',
        body: `Ten thousand years of ocean history have been played. The relay trade has risen and fragmented; the scrambles have been won and lost; the Strange Peace, if it came, holds or does not hold. What remains is the record — the institutions built, the territories held, the decisions made under uncertainty with imperfect information. The ocean does not judge. It simply continues.`,
        secondary: `A full accounting of your reign follows.`,
      };
    }

    default:
      return null;
  }
}

// ── Component ───────────────────────────────────────────────

export default function EventPopup({ event, onDismiss, names, playerCore }) {
  if (!event) return null;

  const def = buildEventDef(event.type, event.data, names, playerCore);
  if (!def) return null;

  const color = def.color;

  return (
    <div style={STYLES.overlay} onClick={onDismiss}>
      <div style={STYLES.card(color)} onClick={e => e.stopPropagation()}>
        <div style={STYLES.header(color)}>
          <span style={STYLES.icon(color)}>{def.icon}</span>
          <div style={STYLES.titleWrap}>
            <div style={STYLES.title(color)}>{def.title}</div>
            {def.subtitle && (
              <div style={STYLES.subtitle}>{def.subtitle}</div>
            )}
          </div>
        </div>
        <div style={STYLES.body}>{def.body}</div>
        {def.secondary && (
          <div style={STYLES.secondaryBlock(color)}>{def.secondary}</div>
        )}
        <div style={STYLES.footer}>
          <button style={STYLES.button(color)} onClick={onDismiss}>
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Legacy exports for GameApp.jsx ─────────────────────────

// ERA_DESCRIPTIONS used by ADVANCE_TURN in GameApp.jsx
export const ERA_DESCRIPTIONS = Object.fromEntries(
  Object.entries(ERA_NARRATIVES).map(([k, v]) => [k, v.short])
);

// TECH_MILESTONES used by ADVANCE_TURN in GameApp.jsx
export const TECH_MILESTONES = Object.fromEntries(
  Object.entries(TECH_MILESTONE_NARRATIVES).map(([k, v]) => [k, { desc: v.body }])
);
