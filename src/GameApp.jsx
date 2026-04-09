// ═══════════════════════════════════════════════════════════
// GameApp.jsx — 1-Player Turn-Based Game Mode
// Strategy-map globe + SimEngine tick-by-tick interface.
// Fork of App.jsx rendering patterns; simulate.js untouched.
// ═══════════════════════════════════════════════════════════

import { useState, useEffect, useRef, useCallback, useMemo, useReducer } from 'react';
import * as THREE from 'three';
import { buildWorld } from './engine/world.js';
import { SimEngine, DEFAULT_PARAMS } from './engine/SimEngine.js';
import { POLITY_NAMES } from './engine/constants.js';
import { mulberry32 } from './engine/rng.js';
import PolitySelect from './components/PolitySelect.jsx';
import TurnDashboard from './components/TurnDashboard.jsx';
import EventPopup, { ERA_DESCRIPTIONS, TECH_MILESTONES } from './components/EventPopup.jsx';
import { FOCUSES } from './components/TurnDashboard.jsx';

const R = 5;

// ── Polity name shuffler (same logic as history.js) ──────

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

// ── Color helpers ────────────────────────────────────────

// ── Antique cartography palette ─────────────────────────
const FOG_COLOR = new THREE.Color(0.08, 0.06, 0.04);       // terra incognita — dark umber
const RUMOR_COLOR = new THREE.Color(0.22, 0.18, 0.12);     // rumor — faint sepia hint
const FRONTIER_COLOR = new THREE.Color(0.45, 0.35, 0.20);  // frontier — aged brown
const PLAYER_COLOR = new THREE.Color(0.16, 0.12, 0.08);    // player — dark ink

function factionColor(archIdx, controller, playerCore, snapshot, visibility) {
  const vis = visibility?.[archIdx] || 'unknown';

  if (vis === 'unknown') return FOG_COLOR;
  if (vis === 'rumor') return RUMOR_COLOR;
  if (vis === 'owned') return PLAYER_COLOR;
  if (vis === 'frontier') {
    // Frontier shows who controls it
    if (controller === archIdx) return FRONTIER_COLOR; // independent
    if (controller === playerCore) return PLAYER_COLOR; // ours somehow
    // Owned by someone else — muted sepia faction color
    const cpos = snapshot?.cpos?.[controller];
    if (cpos) {
      const ci = (cpos[0] + 1) * 0.5;
      const io = (cpos[1] + 1) * 0.5;
      return new THREE.Color(0.25 + ci * 0.25, 0.18 + io * 0.18, 0.10 + (1 - ci) * 0.12);
    }
    return FRONTIER_COLOR;
  }
  // 'contacted' — full faction color in sepia tones
  if (controller === playerCore) return PLAYER_COLOR;
  const cpos = snapshot?.cpos?.[controller];
  if (cpos) {
    const ci = (cpos[0] + 1) * 0.5;
    const io = (cpos[1] + 1) * 0.5;
    return new THREE.Color(0.35 + ci * 0.3, 0.25 + io * 0.2, 0.12 + (1 - ci) * 0.15);
  }
  return new THREE.Color(0.4, 0.32, 0.22);
}

// ── Camera: compute quaternion to face a point on the sphere ──

function quatToFace(cx, cy, cz) {
  // Rotate globe so (cx,cy,cz) faces camera (camera is on +Z)
  const target = new THREE.Vector3(cx, cy, cz).normalize();
  const forward = new THREE.Vector3(0, 0, 1);
  const q = new THREE.Quaternion().setFromUnitVectors(target, forward);
  return q;
}

// ── Game reducer ─────────────────────────────────────────

const INITIAL_STATE = {
  phase: 'SELECT_POLITY', // SELECT_POLITY | PLAYING | GAME_OVER
  playerCore: null,
  engine: null,
  snapshot: null,
  activeFocus: 'balanced',
  allocation: { expansion: 33, techShare: 34, consolidation: 33 },
  selectedTargets: new Set(),
  frontier: [],
  eventLog: [],
  speed: 1,           // 0=paused, 1/5/10
  pendingPopup: null,  // { type, data }
  timerKey: 0,         // bump to reset timer
  lastEra: null,
  lastTech: 0,
  contactedSet: new Set(),
};

function gameReducer(state, action) {
  switch (action.type) {
    case 'SELECT_POLITY': {
      const { playerCore, world, substrate } = action;
      const engine = new SimEngine(
        { archs: world.archs, plateauEdges: world.plateauEdges, seed: world.seed, substrate },
        DEFAULT_PARAMS,
        playerCore
      );
      // Skip the boring early game — start at tick 60 (~17000 BP, tech ~1.5)
      engine.skipToTick(60);
      const snapshot = engine.snapshot();
      const frontier = engine.getFrontier(playerCore);
      const eraName = snapshot.year < -5000 ? 'Antiquity' : snapshot.year < -2000 ? 'Serial Contact'
        : snapshot.year < -500 ? 'Colonial' : snapshot.year < -200 ? 'Industrial' : 'Nuclear';
      return {
        ...state,
        phase: 'PLAYING',
        playerCore,
        engine,
        snapshot,
        frontier,
        selectedTargets: new Set(),
        eventLog: [],
        activeFocus: 'balanced',
        allocation: { expansion: 33, techShare: 34, consolidation: 33 },
        speed: 1,
        pendingPopup: null,
        timerKey: 0,
        lastEra: eraName,
        lastTech: snapshot.tech?.[playerCore] || 0,
        contactedSet: new Set(snapshot.contactedCores || []),
      };
    }

    case 'SET_FOCUS': {
      const focus = FOCUSES.find(f => f.key === action.focus);
      if (!focus) return state;
      return {
        ...state,
        activeFocus: action.focus,
        allocation: { ...focus.alloc },
      };
    }

    case 'SET_SPEED':
      return { ...state, speed: action.speed };

    case 'DISMISS_POPUP':
      return { ...state, pendingPopup: null, timerKey: state.timerKey + 1 };

    case 'TOGGLE_TARGET': {
      const next = new Set(state.selectedTargets);
      if (next.has(action.target)) next.delete(action.target);
      else next.add(action.target);
      return { ...state, selectedTargets: next };
    }

    case 'ADVANCE_TURN': {
      const { engine, playerCore, allocation, selectedTargets, eventLog } = state;
      if (!engine || engine.finished || state.pendingPopup) return state;

      const decision = {
        expansion: allocation.expansion / 100,
        techShare: allocation.techShare / 100,
        consolidation: allocation.consolidation / 100,
        targets: [...selectedTargets],
      };

      const snapshot = engine.advanceTick(decision);
      const frontier = engine.getFrontier(playerCore);

      // Build event log entries — fog of war: only show events we can see
      const newEvents = [...eventLog];
      const vis = snapshot.visibility;
      let popup = null; // first popup-worthy event wins

      for (const ev of snapshot.events) {
        const yearStr = `Y${(snapshot.tick || 60) - 60}`;
        if (ev.core === playerCore) {
          const targetName = action.names[ev.target];
          newEvents.push({ yearStr, text: `You absorbed ${targetName}`, color: '#8a7a3a' });
          if (!popup) {
            popup = {
              type: 'absorption',
              data: { name: targetName, territory: snapshot.playerStats?.territory || '?' },
            };
          }
        } else if (ev.target !== undefined && snapshot.controller?.[ev.target] !== playerCore
          && state.snapshot?.controller?.[ev.target] === playerCore) {
          // We lost territory
          const targetName = action.names[ev.target];
          const aggressorName = action.names[ev.core];
          newEvents.push({ yearStr, text: `${aggressorName} seized ${targetName} from you!`, color: '#a04030' });
          if (!popup) {
            popup = {
              type: 'territory_lost',
              data: { name: targetName, aggressor: aggressorName },
            };
          }
        } else {
          const targetVis = vis?.[ev.target] || 'unknown';
          const coreVis = vis?.[ev.core] || 'unknown';
          if (targetVis === 'unknown' && coreVis === 'unknown') continue;
          if (targetVis === 'rumor' && coreVis === 'rumor') {
            newEvents.push({ yearStr, text: `Rumors of conflict near ${action.names[ev.target]}`, color: '#3a2a1a' });
          } else {
            newEvents.push({ yearStr, text: `${action.names[ev.core]} absorbed ${action.names[ev.target]}`, color: '#6a5a3a' });
          }
        }
      }

      // Check for first contact — new civilizations discovered
      const newContacts = snapshot.contactedCores || [];
      const prevContacted = state.contactedSet;
      const newContactedSet = new Set(newContacts);
      for (const cc of newContacts) {
        if (!prevContacted.has(cc) && !popup) {
          const cpos = snapshot.cpos?.[cc];
          const cultureLabel = cpos
            ? `${cpos[0] > 0 ? 'individualist' : 'collectivist'}-${cpos[1] > 0 ? 'outward' : 'inward'}`
            : 'unknown';
          popup = {
            type: 'first_contact',
            data: {
              name: action.names[cc] || `Nation ${cc}`,
              culture: cultureLabel,
              tech: snapshot.tech?.[cc] || '?',
            },
          };
        }
      }

      // Check era transition
      const year = snapshot.year;
      const eraName = year < -5000 ? 'Antiquity' : year < -2000 ? 'Serial Contact'
        : year < -500 ? 'Colonial' : year < -200 ? 'Industrial' : 'Nuclear';
      if (eraName !== state.lastEra && !popup) {
        popup = {
          type: 'era_transition',
          data: { era: eraName, description: ERA_DESCRIPTIONS[eraName] || `The ${eraName} era begins.` },
        };
      }

      // Check tech milestones
      const playerTech = snapshot.tech?.[playerCore] || 0;
      const prevTech = state.lastTech;
      for (const [level, info] of Object.entries(TECH_MILESTONES)) {
        const tl = Number(level);
        if (playerTech >= tl && prevTech < tl && !popup) {
          popup = {
            type: 'tech_milestone',
            data: { description: info.desc },
          };
        }
      }

      // Dark Forest detection
      if (snapshot.dfYear && !state.snapshot?.dfYear) {
        const contactedCores = snapshot.contactedCores || [];
        const canSeeDF = snapshot.dfArch === playerCore || snapshot.dfDetector === playerCore
          || contactedCores.includes(snapshot.dfArch) || contactedCores.includes(snapshot.dfDetector);
        if (canSeeDF) {
          const yearStr = `Y${(snapshot.tick || 60) - 60}`;
          newEvents.push({ yearStr, text: 'DARK FOREST CONTACT DETECTED', color: '#a04030' });
          popup = { type: 'dark_forest', data: {} };
        }
      }

      // Prune stale targets that are no longer on frontier
      const frontierSet = new Set(frontier.map(f => f.index));
      const nextTargets = new Set([...selectedTargets].filter(t => frontierSet.has(t)));

      // Check for defeat — lost all territory
      const playerTerritory = snapshot.playerStats?.territory || 0;
      const defeated = playerTerritory === 0;
      if (defeated && !popup) {
        popup = { type: 'defeat', data: {} };
      }

      return {
        ...state,
        snapshot,
        frontier,
        selectedTargets: nextTargets,
        eventLog: newEvents,
        phase: (snapshot.finished || defeated) ? 'GAME_OVER' : 'PLAYING',
        pendingPopup: popup,
        timerKey: state.timerKey + 1,
        lastEra: eraName,
        lastTech: playerTech,
        contactedSet: newContactedSet,
      };
    }

    default:
      return state;
  }
}

// ═══════════════════════════════════════════════════════════
// Main component
// ═══════════════════════════════════════════════════════════

function GameInner({ seed, onBack }) {
  const mountRef = useRef(null);
  const sceneRef = useRef({});
  const globeQuat = useRef(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), 0.3));
  const zoomRef = useRef(18);
  const targetZoom = useRef(18); // for smooth zoom lerp
  const dragData = useRef({ active: false, startPoint: null, startQuat: null, lastGood: null });
  const lastM = useRef({ x: 0, y: 0 });
  const clickStart = useRef({ x: 0, y: 0 });
  const [highlightedArch, setHighlightedArch] = useState(null);

  const world = useMemo(() => {
    // Build world without running full history (we'll use SimEngine instead)
    // We still need archs, plateauEdges, substrate from buildWorld
    return buildWorld(seed);
  }, [seed]);

  const names = useMemo(() => shuffleNames(seed), [seed]);

  const [game, dispatch] = useReducer(gameReducer, INITIAL_STATE);

  // ── Three.js setup ──────────────────────────────────────

  useEffect(() => {
    const el = mountRef.current;
    if (!el) return;
    const w = el.clientWidth, h = el.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 200);
    camera.position.set(0, 0, zoomRef.current);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x0a0804); // dark umber void
    el.appendChild(renderer.domElement);

    const ambLight = new THREE.AmbientLight(0x998866, 0.5); // warm sepia ambient
    scene.add(ambLight);
    const dirLight = new THREE.DirectionalLight(0xffe8c0, 0.9); // candlelight directional
    dirLight.position.set(0, 2, 10);
    scene.add(dirLight);

    const globeGroup = new THREE.Group();
    scene.add(globeGroup);

    // Atmosphere glow — warm parchment halo
    globeGroup.add(new THREE.Mesh(
      new THREE.IcosahedronGeometry(R * 1.02, 3),
      new THREE.MeshBasicMaterial({ color: 0xd4b896, transparent: true, opacity: 0.06, side: THREE.BackSide })
    ));

    // Ocean sphere — warm parchment surface
    globeGroup.add(new THREE.Mesh(
      new THREE.IcosahedronGeometry(R * 0.998, 5),
      new THREE.MeshPhongMaterial({ color: new THREE.Color(0.58, 0.48, 0.34), shininess: 3, specular: new THREE.Color(0x1a1408) })
    ));

    // Archipelago markers
    const markers = [];
    for (let i = 0; i < world.archs.length; i++) {
      const arch = world.archs[i];
      const geo = new THREE.SphereGeometry(0.06 + (arch.shelfR || 0.06) * 0.3, 8, 6);
      const mat = new THREE.MeshPhongMaterial({ color: 0x2a1f14, emissive: 0x0a0804, shininess: 2 }); // dark ink landmasses
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(arch.cx * R * 1.001, arch.cy * R * 1.001, arch.cz * R * 1.001);
      mesh.userData.archIdx = i;
      globeGroup.add(mesh);
      markers.push(mesh);
    }

    // Edge lines (trade routes / plateau connections)
    const edgeGroup = new THREE.Group();
    for (const [ai, bi] of world.plateauEdges) {
      const a = world.archs[ai], b = world.archs[bi];
      const pts = [];
      const steps = 12;
      for (let s = 0; s <= steps; s++) {
        const t = s / steps;
        let x = a.cx * (1 - t) + b.cx * t;
        let y = a.cy * (1 - t) + b.cy * t;
        let z = a.cz * (1 - t) + b.cz * t;
        const len = Math.sqrt(x * x + y * y + z * z) || 1;
        x /= len; y /= len; z /= len;
        pts.push(new THREE.Vector3(x * R * 0.999, y * R * 0.999, z * R * 0.999));
      }
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const line = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0x2a1f14, transparent: true, opacity: 0.4 }));
      edgeGroup.add(line);
    }
    globeGroup.add(edgeGroup);

    // Name labels
    const labelGroup = new THREE.Group();
    for (let i = 0; i < world.archs.length; i++) {
      const arch = world.archs[i];
      const canvas = document.createElement('canvas');
      canvas.width = 256; canvas.height = 64;
      const ctx = canvas.getContext('2d');
      ctx.font = "bold 24px 'JetBrains Mono','Fira Code',monospace";
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.strokeStyle = 'rgba(10,8,4,0.8)'; ctx.lineWidth = 3;
      ctx.strokeText(names[i], 128, 32);
      ctx.fillStyle = '#c8a878'; // parchment gold text
      ctx.fillText(names[i], 128, 32);

      const tex = new THREE.CanvasTexture(canvas);
      const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false, opacity: 0.6 });
      const sprite = new THREE.Sprite(mat);
      sprite.position.set(arch.cx * R * 1.04, arch.cy * R * 1.04, arch.cz * R * 1.04);
      sprite.scale.set(1.2, 0.3, 1);
      sprite.userData.archIdx = i;
      labelGroup.add(sprite);
    }
    globeGroup.add(labelGroup);

    const st = sceneRef.current;
    st.scene = scene; st.camera = camera; st.renderer = renderer;
    st.globeGroup = globeGroup; st.markers = markers; st.edgeGroup = edgeGroup;
    st.labelGroup = labelGroup; st.dirLight = dirLight;

    // Animation loop with per-frame resize check
    let running = true;
    let lastW = 0, lastH = 0;
    function animate() {
      if (!running) return;
      requestAnimationFrame(animate);
      // Resize check — dashboard may appear/disappear, changing container size
      const cw = el.clientWidth, ch = el.clientHeight;
      if (cw !== lastW || ch !== lastH) {
        lastW = cw; lastH = ch;
        camera.aspect = cw / ch;
        camera.updateProjectionMatrix();
        renderer.setSize(cw, ch);
      }
      globeGroup.quaternion.copy(globeQuat.current);
      zoomRef.current += (targetZoom.current - zoomRef.current) * 0.08;
      camera.position.set(0, 0, zoomRef.current);
      dirLight.position.copy(camera.position).normalize().multiplyScalar(10);
      renderer.render(scene, camera);
    }
    animate();

    return () => {
      running = false;
      renderer.dispose();
      el.removeChild(renderer.domElement);
    };
  }, [world, names]);

  // ── Center camera on player's archipelago when game starts ──

  useEffect(() => {
    if (game.phase === 'PLAYING' && game.playerCore !== null) {
      const arch = world.archs[game.playerCore];
      globeQuat.current.copy(quatToFace(arch.cx, arch.cy, arch.cz));
      targetZoom.current = R * 1.8; // close view on player's island
    }
  }, [game.phase, game.playerCore, world.archs]);

  // ── Update marker colors on game state change (FOG OF WAR) ──

  useEffect(() => {
    const st = sceneRef.current;
    if (!st.markers) return;

    const vis = game.snapshot?.visibility;

    for (let i = 0; i < st.markers.length; i++) {
      const mesh = st.markers[i];
      if (game.phase === 'SELECT_POLITY') {
        if (i === highlightedArch) {
          mesh.material.color.set(0xb8923a); // highlighted gold
          mesh.material.emissive.set(0x3a2a10);
          mesh.scale.setScalar(1.3);
        } else {
          mesh.material.color.set(0x2a1f14); // dark ink
          mesh.material.emissive.set(0x0a0804);
          mesh.scale.setScalar(1.0);
        }
        mesh.visible = true;
      } else if (game.snapshot) {
        const ctrl = game.snapshot.controller[i];
        const v = vis?.[i] || 'unknown';
        const color = factionColor(i, ctrl, game.playerCore, game.snapshot, vis);
        mesh.material.color.copy(color);

        // Visibility-based rendering
        if (v === 'unknown') {
          mesh.material.emissive.set(0x050402);
          mesh.visible = false;
        } else if (v === 'rumor') {
          mesh.material.color.set(0x1a1408);
          mesh.material.emissive.set(0x0a0804);
          mesh.visible = true;
          mesh.scale.setScalar(0.7);
        } else if (v === 'frontier') {
          mesh.material.color.set(0x1a1408); // dark ink
          mesh.material.emissive.set(0x1a1408);
          mesh.visible = true;
          mesh.scale.setScalar(1.0);
          if (game.selectedTargets.has(i)) {
            mesh.material.emissive.set(0x5a4a2a);
            mesh.scale.setScalar(1.2);
          }
        } else if (v === 'contacted') {
          mesh.material.color.copy(color);
          mesh.material.emissive.set(0x14100a);
          mesh.visible = true;
          mesh.scale.setScalar(0.9);
        } else { // owned
          mesh.material.color.set(0x0e0a06); // darkest ink for owned
          mesh.material.emissive.set(0x2a1f14);
          mesh.visible = true;
          mesh.scale.setScalar(1.15);
        }
      }
    }

    // Edge visibility — only show edges where at least one end is visible
    if (st.edgeGroup && vis) {
      const edges = world.plateauEdges;
      for (let e = 0; e < edges.length; e++) {
        const line = st.edgeGroup.children[e];
        if (!line) continue;
        const [ai, bi] = edges[e];
        const va = vis[ai] || 'unknown';
        const vb = vis[bi] || 'unknown';
        const anyKnown = va !== 'unknown' && va !== 'rumor' && vb !== 'unknown' && vb !== 'rumor';
        line.visible = anyKnown;
        if (anyKnown) {
          const isPlayerEdge = va === 'owned' || vb === 'owned';
          line.material.opacity = isPlayerEdge ? 0.65 : 0.35;
          line.material.color.set(isPlayerEdge ? 0x4a3a20 : 0x2a1f14);
        }
      }
    }

    // Label visibility — only show for owned, frontier, and contacted
    if (st.labelGroup) {
      for (const sprite of st.labelGroup.children) {
        const idx = sprite.userData.archIdx;
        if (idx === undefined) continue;
        if (game.phase === 'SELECT_POLITY') {
          sprite.material.opacity = 0.6;
          sprite.visible = true;
        } else if (vis) {
          const v = vis[idx];
          if (v === 'owned') {
            sprite.material.color.set(0xffffff); // full brightness — gold label
            sprite.material.opacity = 0.95;
            sprite.visible = true;
          } else if (v === 'frontier') {
            sprite.material.color.set(0xc0a070); // warm muted
            sprite.material.opacity = 0.7;
            sprite.visible = true;
          } else if (v === 'contacted') {
            sprite.material.color.set(0x8a7a5a); // faded sepia
            sprite.material.opacity = 0.5;
            sprite.visible = true;
          } else if (v === 'rumor') {
            sprite.material.color.set(0x6a5a3a); // very faded
            sprite.material.opacity = 0.2;
            sprite.visible = true;
          } else {
            sprite.visible = false;
          }
        }
      }
    }
  }, [game.snapshot, game.phase, game.playerCore, game.selectedTargets, highlightedArch, world.plateauEdges]);

  // ── Arcball camera ─────────────────────────────────────

  function raycastToSphere(clientX, clientY, quatOverride) {
    const st = sceneRef.current;
    if (!st.renderer || !st.camera) return null;
    const el = mountRef.current; if (!el) return null;
    const rect = el.getBoundingClientRect();
    const ndcX = ((clientX - rect.left) / rect.width) * 2 - 1;
    const ndcY = -((clientY - rect.top) / rect.height) * 2 + 1;
    const cam = st.camera;
    const rayDir = new THREE.Vector3(ndcX, ndcY, 0.5).unproject(cam).sub(cam.position).normalize();
    const rayOrigin = cam.position.clone();
    const q = quatOverride || globeQuat.current;
    const invQ = q.clone().invert();
    rayOrigin.applyQuaternion(invQ);
    rayDir.applyQuaternion(invQ);
    const a = rayDir.dot(rayDir), b = rayOrigin.dot(rayDir), c = rayOrigin.dot(rayOrigin) - R * R;
    const disc = b * b - a * c;
    if (disc < 0) return null;
    const t = (-b - Math.sqrt(disc)) / a;
    if (t < 0) return null;
    return rayOrigin.add(rayDir.multiplyScalar(t)).normalize();
  }

  const onPointerDown = useCallback(e => {
    clickStart.current = { x: e.clientX, y: e.clientY };
    const hit = raycastToSphere(e.clientX, e.clientY);
    if (hit) {
      dragData.current = { active: true, startPoint: hit, startQuat: globeQuat.current.clone(), lastGood: { x: e.clientX, y: e.clientY } };
    } else {
      dragData.current = { active: true, startPoint: null, startQuat: null, lastGood: null };
      lastM.current = { x: e.clientX, y: e.clientY };
    }
  }, []);

  const onPointerMove = useCallback(e => {
    const dd = dragData.current;
    if (!dd.active) return;
    if (dd.startPoint && dd.startQuat) {
      const hit = raycastToSphere(e.clientX, e.clientY, dd.startQuat);
      if (hit) {
        const p1 = dd.startPoint, p2 = hit;
        const axis = new THREE.Vector3().crossVectors(p1, p2);
        const len = axis.length();
        if (len > 0.0001) {
          axis.divideScalar(len);
          const angle = Math.acos(Math.max(-1, Math.min(1, p1.dot(p2))));
          const rot = new THREE.Quaternion().setFromAxisAngle(axis, angle);
          globeQuat.current.copy(dd.startQuat).multiply(rot);
        }
        dd.lastGood = { x: e.clientX, y: e.clientY };
      } else {
        dd.startPoint = null; dd.startQuat = null;
        lastM.current = dd.lastGood || { x: e.clientX, y: e.clientY };
      }
    } else {
      const dx = e.clientX - lastM.current.x, dy = e.clientY - lastM.current.y;
      lastM.current = { x: e.clientX, y: e.clientY };
      const qY = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), dx * 0.004);
      const qX = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), dy * 0.004);
      globeQuat.current.premultiply(new THREE.Quaternion().multiplyQuaternions(qX, qY));
    }
  }, []);

  const onPointerUp = useCallback(e => {
    dragData.current.active = false;
    // Detect click
    const dx = e.clientX - clickStart.current.x, dy = e.clientY - clickStart.current.y;
    if (Math.abs(dx) < 5 && Math.abs(dy) < 5) {
      // Raycasting to find clicked arch
      const st = sceneRef.current;
      if (!st.camera || !st.markers) return;
      const el = mountRef.current; if (!el) return;
      const rect = el.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, st.camera);
      const hits = raycaster.intersectObjects(st.markers, false);
      if (hits.length > 0) {
        const ai = hits[0].object.userData.archIdx;
        if (ai !== undefined) {
          if (game.phase === 'PLAYING') {
            // Toggle expansion target if on frontier
            const onFrontier = game.frontier.some(f => f.index === ai);
            if (onFrontier) dispatch({ type: 'TOGGLE_TARGET', target: ai });
          }
        }
      }
    }
  }, [game.phase, game.frontier]);

  const onWheel = useCallback(e => {
    e.preventDefault();
    const z = targetZoom.current;
    targetZoom.current = Math.max(R * 1.1, Math.min(40, z * (1 + e.deltaY * 0.002)));
  }, []);

  // ── Callbacks ──────────────────────────────────────────

  const handleSelectPolity = useCallback((archIdx) => {
    dispatch({
      type: 'SELECT_POLITY',
      playerCore: archIdx,
      world: {
        archs: world.archs,
        plateauEdges: world.plateauEdges,
        seed: world.seed,
      },
      substrate: world.substrate,
    });
  }, [world]);

  const handleAdvance = useCallback(() => {
    dispatch({ type: 'ADVANCE_TURN', names });
  }, [names]);

  const handleSetFocus = useCallback((focus) => {
    dispatch({ type: 'SET_FOCUS', focus });
  }, []);

  const handleSetSpeed = useCallback((speed) => {
    dispatch({ type: 'SET_SPEED', speed });
  }, []);

  const handleDismissPopup = useCallback(() => {
    dispatch({ type: 'DISMISS_POPUP' });
  }, []);

  const handleToggleTarget = useCallback((target) => {
    dispatch({ type: 'TOGGLE_TARGET', target });
  }, []);

  // ── Render ─────────────────────────────────────────────

  return (
    <div style={{
      width: '100%', height: '100vh', background: '#0a0804', color: '#c8a878',
      fontFamily: "'JetBrains Mono','Fira Code',monospace",
      display: 'flex', flexDirection: 'column', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '8px 20px', borderBottom: '1px solid #2a1f14', flexShrink: 0,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'linear-gradient(180deg,#120e08,#0a0804)',
      }}>
        <div>
          <div style={{ fontSize: 9, color: '#8a7a5a', letterSpacing: '3px', textTransform: 'uppercase', marginBottom: 1 }}>
            Game Mode
          </div>
          <div style={{ fontSize: 14, color: '#d4b896', fontWeight: 600 }}>
            AEOLIA — STRATEGY
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ fontSize: 8, color: '#6a5a3a' }}>seed {seed}</div>
          <button onClick={onBack} style={{
            padding: '4px 12px', fontSize: 8, fontFamily: 'inherit', cursor: 'pointer',
            background: '#14100a', border: '1px solid #2a1f14', color: '#8a7a5a',
            letterSpacing: '1px', borderRadius: 2,
          }}>
            Observatory
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Globe */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden', minWidth: 0 }}>
          <div ref={mountRef} style={{ width: '100%', height: '100%', cursor: 'grab' }}
            onPointerDown={onPointerDown} onPointerMove={onPointerMove}
            onPointerUp={onPointerUp} onPointerLeave={() => { dragData.current.active = false; }}
            onWheel={onWheel}
          />

          {/* Polity Select overlay */}
          {game.phase === 'SELECT_POLITY' && (
            <PolitySelect
              archs={world.archs}
              substrate={world.substrate}
              names={names}
              onSelect={handleSelectPolity}
              onHighlight={setHighlightedArch}
            />
          )}
        </div>

        {/* Dashboard (right panel) — only during gameplay */}
        {(game.phase === 'PLAYING' || game.phase === 'GAME_OVER') && (
          <TurnDashboard
            snapshot={game.snapshot}
            frontier={game.frontier}
            names={names}
            playerCore={game.playerCore}
            activeFocus={game.activeFocus}
            onSetFocus={handleSetFocus}
            selectedTargets={game.selectedTargets}
            onToggleTarget={handleToggleTarget}
            onAdvance={handleAdvance}
            eventLog={game.eventLog}
            speed={game.speed}
            onSetSpeed={handleSetSpeed}
            timerDuration={game.speed > 0 ? 10000 / game.speed : 10000}
            timerPaused={!!game.pendingPopup}
            timerKey={game.timerKey}
          />
        )}
      </div>

      {/* Event popup overlay */}
      {game.pendingPopup && (
        <EventPopup event={game.pendingPopup} onDismiss={handleDismissPopup} />
      )}
    </div>
  );
}

// ── Wrapper: seed state + key-based remount ──────────────

export default function GameApp({ seed: initialSeed, onBack }) {
  const [seed] = useState(initialSeed || 42);
  return <GameInner key={seed} seed={seed} onBack={onBack} />;
}
