/* ============================================================================
   Q.E.L.T.E.X MULTI-HUD ENGINE (THREE.JS 3D QELTEX + ALL 8 QELTEX HUDS)
   ============================================================================ */
let scene, camera, renderer, particleSystem, particleGeo, ringGroup;
let qeltexState = "LISTENING";
let qeltexHue = 0x00ff55;
const PARTICLE_COUNT = 9500;
let baseRadii, baseAngles, baseY, speeds;

let hud2dTick = 0;
let hud2dPulses = new Array();
let hud2dRings = [0, 2.1, 4.2];
let hud2dScan = 0;
let hud2dStreams = Array.from({ length: 28 }, (_, i) => ({
  x: i * 16,
  y: Math.random() * 360 - 100,
  spd: 1.5 + Math.random() * 2.5
}));

function initThreeQeltex() {
  const canvas = document.getElementById("qeltex-canvas");
  const wrap = document.getElementById("qeltex-container");
  if (!canvas || !wrap || typeof THREE === "undefined") return;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(55, wrap.clientWidth / wrap.clientHeight, 0.1, 1000);
  camera.position.set(0, 1.1, 5.2);
  camera.lookAt(0, 0, 0);

  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
  renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  renderer.setPixelRatio(1);

  particleGeo = new THREE.BufferGeometry();
  const positions = new Float32Array(PARTICLE_COUNT * 3);
  const colors = new Float32Array(PARTICLE_COUNT * 3);
  baseRadii = new Float32Array(PARTICLE_COUNT);
  baseAngles = new Float32Array(PARTICLE_COUNT);
  baseY = new Float32Array(PARTICLE_COUNT);
  speeds = new Float32Array(PARTICLE_COUNT);

  const c1 = new THREE.Color(0x00ff55);
  const c2 = new THREE.Color(0xccff00);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const t = Math.random();
    const radius = 0.25 + Math.pow(t, 0.75) * 2.1;
    const angle = Math.random() * Math.PI * 2;
    const y = (Math.random() - 0.5) * (1.8 * (1.0 - t * 0.55));

    baseRadii[i] = radius;
    baseAngles[i] = angle;
    baseY[i] = y;
    speeds[i] = (0.4 + (1.0 - t) * 1.4) * (Math.random() > 0.15 ? 1 : -0.6);

    positions[i * 3] = Math.cos(angle) * radius;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = Math.sin(angle) * radius;

    const mixed = c1.clone().lerp(c2, Math.random() * 0.35);
    colors[i * 3] = mixed.r;
    colors[i * 3 + 1] = mixed.g;
    colors[i * 3 + 2] = mixed.b;
  }

  particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  particleGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  const mat = new THREE.PointsMaterial({
    size: 0.024,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });

  particleSystem = new THREE.Points(particleGeo, mat);
  scene.add(particleSystem);

  ringGroup = new THREE.Group();
  const ringRadii = [1.55, 1.95, 2.35];
  ringRadii.forEach((r, idx) => {
    const geo = new THREE.RingGeometry(r - 0.015, r, 96, 1, 0, Math.PI * (1.35 + idx * 0.2));
    const rMat = new THREE.MeshBasicMaterial({
      color: 0x00ff55,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.55
    });
    const mesh = new THREE.Mesh(geo, rMat);
    mesh.rotation.x = Math.PI / 2.4 + idx * 0.15;
    ringGroup.add(mesh);
  });
  scene.add(ringGroup);

  window.addEventListener("resize", () => {
    if (!wrap.clientWidth || !wrap.clientHeight) return;
    camera.aspect = wrap.clientWidth / wrap.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  });

  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    if (canvas.style.display === "none") return;
    const dt = clock.getDelta();
    const elapsed = clock.getElapsedTime();

    const speedMult = qeltexState === "SPEAKING" ? 2.8 : (qeltexState === "THINKING" ? 2.1 : (qeltexState === "MUTED" ? 0.2 : 1.0));
    const pulse = qeltexState === "SPEAKING" ? 1.0 + Math.sin(elapsed * 14) * 0.12 : 1.0 + Math.sin(elapsed * 2.5) * 0.03;

    const pos = particleGeo.attributes.position.array;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      baseAngles[i] += speeds[i] * dt * speedMult;
      const r = baseRadii[i] * pulse;
      const swirl = Math.sin(elapsed * 2.0 + baseRadii[i] * 3.0) * 0.08;
      pos[i * 3] = Math.cos(baseAngles[i]) * r;
      pos[i * 3 + 1] = baseY[i] * pulse + swirl;
      pos[i * 3 + 2] = Math.sin(baseAngles[i]) * r;
    }
    particleGeo.attributes.position.needsUpdate = true;

    ringGroup.children.forEach((ring, i) => {
      ring.rotation.z += dt * speedMult * (i % 2 === 0 ? 0.7 : -0.5);
    });

    renderer.render(scene, camera);
  }
  animate();
}

function updateQeltexPalette(hexInt) {
  qeltexHue = hexInt;
  if (!particleGeo || !ringGroup) return;
  const cMain = new THREE.Color(hexInt);
  const cSec = new THREE.Color(0xffffff);
  const cols = particleGeo.attributes.color.array;
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const mix = cMain.clone().lerp(cSec, (i % 7 === 0) ? 0.35 : 0.05);
    cols[i * 3] = mix.r;
    cols[i * 3 + 1] = mix.g;
    cols[i * 3 + 2] = mix.b;
  }
  particleGeo.attributes.color.needsUpdate = true;
  ringGroup.children.forEach(r => r.material.color.setHex(hexInt));
}

function activateHudRenderer(modeName) {
  const m = (modeName || "3d qeltex").toLowerCase().trim();
  const c3d = document.getElementById("qeltex-canvas");
  const c2d = document.getElementById("hud-2d-canvas");

  if (m === "3d qeltex" || m === "classic" || !m) {
    if (c3d) c3d.style.display = "block";
    if (c2d) c2d.style.display = "none";
  } else {
    if (c3d) c3d.style.display = "none";
    if (c2d) c2d.style.display = "block";
  }
}

let _last2dFrame = 0;
function drawActive2dHud(now = 0) {
  requestAnimationFrame(drawActive2dHud);
  if (now - _last2dFrame < 32) return;
  _last2dFrame = now;
  const c2d = document.getElementById("hud-2d-canvas");
  if (!c2d || c2d.style.display === "none") return;

  const rect = c2d.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  if (c2d.width !== Math.round(rect.width) || c2d.height !== Math.round(rect.height)) {
    c2d.width = Math.round(rect.width);
    c2d.height = Math.round(rect.height);
  }

  const ctx = c2d.getContext("2d");
  const W = c2d.width;
  const H = c2d.height;
  const cx = W / 2;
  const cy = H / 2 + 4;
  const fw = Math.min(W, H) * 0.92;
  hud2dTick += 3;

  ctx.clearRect(0, 0, W, H);
  const mode = (typeof appState !== "undefined" ? appState.hud : "legacy radar").toLowerCase();
  const isListening = (qeltexState === "LISTENING");
  const isSpeaking = (qeltexState === "SPEAKING");
  const themeHex = getComputedStyle(document.documentElement).getPropertyValue("--theme").trim() || "#00ff55";

  // Bakgrunns-matrisestrøm
  if (mode.includes("dna") || mode.includes("tactical") || mode.includes("earth") || mode.includes("planet")) {
    const isRed = mode.includes("red") || mode.includes("tactical");
    const isBlue = mode.includes("blue");
    const headCol = isRed ? "#ff003c" : (isBlue ? "#00ffff" : themeHex);
    const tailCol = isRed ? "rgba(85,0,5,0.45)" : (isBlue ? "rgba(0,51,102,0.45)" : "rgba(0,119,34,0.45)");
    const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*";
    ctx.font = "bold 11px 'Courier New', monospace";
    hud2dStreams.forEach(s => {
      s.y += s.spd * (isSpeaking ? 1.8 : 1.0);
      if (s.y > H + 80) s.y = -40;
      const sx = cx - 220 + s.x;
      for (let k = 0; k < 8; k++) {
        const ch = (isRed || isBlue)
          ? (Math.random() > 0.5 ? "1" : "0")
          : chars[Math.floor((hud2dTick * 0.2 + s.x + k * 3) % chars.length)];
        ctx.fillStyle = k === 0 ? headCol : tailCol;
        ctx.fillText(ch, sx, s.y - k * 13);
      }
    });
  }

  // 1. LIGHT CORE
  if (mode.includes("light")) {
    const pulse = Math.sin(hud2dTick * (isSpeaking ? 0.35 : 0.08)) * (isSpeaking ? 8 : 3);
    ctx.fillStyle = isSpeaking ? "#ffffff" : themeHex;
    ctx.beginPath();
    ctx.arc(cx, cy, 6 + pulse, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = themeHex;
    ctx.lineWidth = isSpeaking ? 2 : 1;
    ctx.beginPath();
    ctx.moveTo(cx - 90, cy); ctx.lineTo(cx - 22, cy);
    ctx.moveTo(cx + 22, cy); ctx.lineTo(cx + 90, cy);
    ctx.stroke();

    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.arc(cx, cy, isSpeaking ? 54 : 46, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // 2. CPU CORE
  else if (mode.includes("cpu")) {
    const pulse = Math.cos(hud2dTick * (isSpeaking ? 0.35 : 0.06)) * (isSpeaking ? 8 : 3);
    ctx.fillStyle = isSpeaking ? "#ffffff" : themeHex;
    ctx.fillRect(cx - 6 - pulse / 2, cy - 6 - pulse / 2, 12 + pulse, 12 + pulse);
    ctx.strokeStyle = themeHex;
    ctx.lineWidth = isSpeaking ? 2.5 : 1.5;
    ctx.strokeRect(cx - 32, cy - 32, 64, 64);
    ctx.beginPath();
    ctx.moveTo(cx - 65, cy - 42); ctx.lineTo(cx - 38, cy - 42); ctx.lineTo(cx - 38, cy - 22);
    ctx.moveTo(cx + 38, cy + 42); ctx.lineTo(cx + 65, cy + 42); ctx.lineTo(cx + 65, cy + 22);
    ctx.stroke();
  }

  // 3. DNA CORE
  else if (mode.includes("dna")) {
    const x0 = cx - fw * 0.36;
    const x1 = cx + fw * 0.36;
    const span = x1 - x0;
    const amp = isSpeaking ? 48 + Math.sin(hud2dTick * 0.35) * 10 : 34;
    const speed = isSpeaking ? 0.14 : 0.04;

    for (let x = x0; x <= x1; x += 7) {
      const rel = (x - x0) / span;
      const env = Math.sin(rel * Math.PI);
      const phase = x * 0.032 + hud2dTick * speed;
      const y1 = cy + amp * Math.sin(phase) * env;
      const y2 = cy + amp * Math.sin(phase + Math.PI) * env;
      const depth = Math.cos(phase);

      ctx.strokeStyle = isSpeaking ? `rgba(255, 255, 255, ${0.55 * env})` : `rgba(0, 255, 85, ${0.35 * env})`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(x, y1);
      ctx.lineTo(x, y2);
      ctx.stroke();

      ctx.fillStyle = isSpeaking ? "#ffffff" : themeHex;
      ctx.beginPath();
      ctx.arc(x, y1, (3.2 + depth * 1.2) * env + 1, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "#ccff00";
      ctx.beginPath();
      ctx.arc(x, y2, (3.2 - depth * 1.2) * env + 1, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // 4. TACTICAL RED
  else if (mode.includes("tactical")) {
    const x0 = cx - fw * 0.34, x1 = cx + fw * 0.34, span = x1 - x0;
    ctx.strokeStyle = isSpeaking ? "#ffffff" : "#ff003c";
    ctx.lineWidth = isSpeaking ? 3 : 2.2;
    ctx.beginPath();
    for (let x = x0; x <= x1; x += 3) {
      const env = Math.sin(((x - x0) / span) * Math.PI);
      const s = Math.sin(x * 0.08 + hud2dTick * (isSpeaking ? 0.32 : 0.14));
      const yOff = isSpeaking
        ? (Math.abs(s) > 0.75 ? 54 * Math.sign(s) * env : (Math.random() - 0.5) * 14 * env)
        : 24 * Math.sin(x * 0.05 + hud2dTick * 0.08) * env;
      x === x0 ? ctx.moveTo(x, cy + yOff) : ctx.lineTo(x, cy + yOff);
    }
    ctx.stroke();
  }

  // 5. BLUE EARTH (1:1 som den gamle versjonen: ekolodd-ringer i temafarge fra senter + myk klode)
  else if (mode.includes("earth")) {
    const mapR = fw * 0.24;
    const img = document.getElementById("img-blue-earth");

    // 1. Svake konsentriske radar-sirkler i temafarge (grønn)
    for (let i = 0; i < 8; i++) {
      const r = fw * (0.48 - i * 0.025);
      ctx.strokeStyle = themeHex;
      ctx.globalAlpha = 0.14 * (1 - i / 8);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.globalAlpha = 1.0;

    // 2. Ekolodd-/sonarringer som starter inne fra senter og stråler helt ut
    const maxLim = fw * 0.56;
    const pulseSpd = isSpeaking ? 4.8 : 2.2;
    const spawnChance = isSpeaking ? 0.08 : 0.03;
    hud2dPulses = hud2dPulses.map(r => r + pulseSpd).filter(r => r < maxLim);
    if (hud2dPulses.length < 4 && (hud2dPulses.length === 0 || Math.random() < spawnChance)) {
      if (hud2dPulses.length === 0 || hud2dPulses[hud2dPulses.length - 1] > fw * 0.16) {
        hud2dPulses.push(4);
      }
    }
    hud2dPulses.forEach(pr => {
      const alpha = Math.max(0, 0.85 * (1.0 - pr / maxLim));
      ctx.strokeStyle = themeHex;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = isSpeaking ? 2.2 : 1.6;
      ctx.beginPath();
      ctx.arc(cx, cy, pr, 0, Math.PI * 2);
      ctx.stroke();
    });
    ctx.globalAlpha = 1.0;

    // 3. Ytre radar-ring og trådkors fra kant til kant
    ctx.strokeStyle = themeHex;
    ctx.globalAlpha = 0.45;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, fw * 0.36, 0, Math.PI * 2);
    ctx.stroke();

    ctx.globalAlpha = 0.25;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - fw * 0.50, cy); ctx.lineTo(cx + fw * 0.50, cy);
    ctx.moveTo(cx, cy - fw * 0.50); ctx.lineTo(cx, cy + fw * 0.50);
    ctx.stroke();
    ctx.globalAlpha = 1.0;

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, mapR, 0, Math.PI * 2);
    ctx.clip();
    if (img && img.complete && img.naturalWidth > 0) {
      const zoom = 1.48;
      const drawSize = mapR * 2 * zoom;
      ctx.drawImage(img, cx - drawSize / 2, cy - drawSize / 2, drawSize, drawSize);
    } else {
      ctx.fillStyle = "#001428";
      ctx.fillRect(cx - mapR, cy - mapR, mapR * 2, mapR * 2);
    }
    ctx.restore();

    if (isSpeaking) {
      const waveBase = fw * 0.34;
      ctx.strokeStyle = "#00ffff";
      ctx.lineWidth = 2.6;
      ctx.beginPath();
      for (let deg = 0; deg <= 360; deg += 3) {
        const rad = (deg * Math.PI) / 180;
        const noise = (10 + Math.random() * 24) * Math.sin(deg * 0.18 + hud2dTick * 0.55);
        const wr = waveBase + noise;
        const wx = cx + wr * Math.cos(rad);
        const wy = cy + wr * Math.sin(rad);
        deg === 0 ? ctx.moveTo(wx, wy) : ctx.lineTo(wx, wy);
      }
      ctx.closePath();
      ctx.stroke();
    }
  }

  // 8. LEGACY RADAR
  else {
    const speakMult = isSpeaking ? 3.2 : 1.0;
    hud2dRings[0] = (hud2dRings[0] + 0.012 * speakMult) % (Math.PI * 2);
    hud2dRings[1] = (hud2dRings[1] - 0.018 * speakMult) % (Math.PI * 2);
    hud2dRings[2] = (hud2dRings[2] + 0.008 * speakMult) % (Math.PI * 2);
    hud2dScan = (hud2dScan + 0.035 * speakMult) % (Math.PI * 2);

    ctx.save();
    ctx.shadowColor = themeHex;
    ctx.shadowBlur = isSpeaking ? 18 : 8;

    // 1. Ytre segmentert sikte-ring
    const segments = 12;
    const segAngle = (Math.PI * 2) / segments;
    for (let i = 0; i < segments; i++) {
      const a1 = hud2dRings[0] + i * segAngle;
      const a2 = a1 + segAngle * 0.65;
      ctx.strokeStyle = (i % 3 === 0 && isSpeaking) ? "#ffffff" : themeHex;
      ctx.lineWidth = isSpeaking ? 3.5 : 2.0;
      ctx.beginPath();
      ctx.arc(cx, cy, fw * 0.45, a1, a2);
      ctx.stroke();
    }

    // 2. Roterende sekskant-skjold
    ctx.strokeStyle = isSpeaking ? "#ffffff" : themeHex;
    ctx.lineWidth = isSpeaking ? 2.5 : 1.5;
    ctx.beginPath();
    for (let i = 0; i <= 6; i++) {
      const angle = hud2dRings[1] + (i * Math.PI) / 3;
      const rHex = fw * (isSpeaking ? 0.36 + Math.sin(hud2dTick * 0.3) * 0.015 : 0.35);
      const hx = cx + Math.cos(angle) * rHex;
      const hy = cy + Math.sin(angle) * rHex;
      if (i === 0) ctx.moveTo(hx, hy);
      else ctx.lineTo(hx, hy);
    }
    ctx.stroke();

    // 3. Sirkulære lydbølge-stolper rundt kjernen
    const bars = 36;
    for (let i = 0; i < bars; i++) {
      const ba = hud2dRings[2] + (i * Math.PI * 2) / bars;
      const wave = isSpeaking
        ? Math.abs(Math.sin(hud2dTick * 0.35 + i * 0.7)) * (fw * 0.08) + 4
        : Math.abs(Math.sin(hud2dTick * 0.05 + i * 0.4)) * 4 + 2;
      const rIn = fw * 0.24;
      const rOut = rIn + wave;

      ctx.strokeStyle = (isSpeaking && wave > fw * 0.05) ? "#ffffff" : themeHex;
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ba) * rIn, cy + Math.sin(ba) * rIn);
      ctx.lineTo(cx + Math.cos(ba) * rOut, cy + Math.sin(ba) * rOut);
      ctx.stroke();
    }

    // 4. Utvidende sjokkbølger når Q.E.L.T.E.X snakker
    if (isSpeaking) {
      for (let i = 0; i < 2; i++) {
        const prog = (hud2dTick * 0.035 + i * 0.5) % 1.0;
        const pr = fw * 0.22 + prog * (fw * 0.26);
        ctx.strokeStyle = themeHex;
        ctx.globalAlpha = 0.65 * (1 - prog);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, pr, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.globalAlpha = 1.0;
    }

    // 5. Indre kjerne og tekst
    const orbPulse = isSpeaking ? (1.0 + Math.sin(hud2dTick * 0.45) * 0.1) : 1.0;
    ctx.fillStyle = isSpeaking ? "rgba(0, 255, 130, 0.25)" : "rgba(0, 80, 45, 0.35)";
    ctx.beginPath();
    ctx.arc(cx, cy, fw * 0.21 * orbPulse, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = isSpeaking ? "#ffffff" : themeHex;
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = isSpeaking ? "#ffffff" : themeHex;
    ctx.font = "bold 14px 'Courier New', monospace";
    ctx.textAlign = "center";
    ctx.fillText("Q.E.L.T.E.X", cx, cy + 5);

    ctx.restore();
  }
}
