// Space backdrop for the dashboard: ~12 slowly twinkling stars that fade in and out,
// faint star dust, and a thin ray of light from the mouse pointer to the nearest star.
// Injected once into the Streamlit page (see starfield() in main.py); drawn on a fixed
// canvas behind the app, so it never blocks clicks. Respects prefers-reduced-motion.
(function () {
  if (window.__lunaStars) return;
  window.__lunaStars = true;
  const d = document, c = d.createElement("canvas");
  c.id = "luna-stars";
  c.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:-1";
  d.body.prepend(c);
  const x = c.getContext("2d");
  let W = 0, H = 0;
  function size() {
    const r = window.devicePixelRatio || 1;
    W = innerWidth; H = innerHeight; c.width = W * r; c.height = H * r;
    x.setTransform(r, 0, 0, r, 0, 0);
  }
  size(); addEventListener("resize", size);

  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const N = 12, rnd = (a, b) => a + Math.random() * (b - a);
  const star = (t) => ({ x: rnd(.03, .97), y: rnd(.04, .96), r: rnd(1.1, 2.3), born: t,
                         life: rnd(16000, 34000), ph: rnd(0, 6.283) });
  const now = performance.now();
  const stars = Array.from({ length: N }, () => { const s = star(now); s.born = now - rnd(0, s.life); return s; });
  const dust = Array.from({ length: 80 }, () => ({ x: Math.random(), y: Math.random(), a: rnd(.04, .16) }));

  let mx = -1, my = -1, moved = 0;
  addEventListener("mousemove", (e) => { mx = e.clientX; my = e.clientY; moved = performance.now(); }, { passive: true });
  d.addEventListener("mouseleave", () => { mx = -1; });

  function life(s, t) {            // 0..1 fade in, hold, fade out; -1 when expired
    const k = (t - s.born) / s.life;
    return k >= 1 ? -1 : Math.min(k / .15, (1 - k) / .15, 1);
  }
  function frame(t) {
    x.clearRect(0, 0, W, H);
    for (const p of dust) { x.fillStyle = `rgba(225,215,255,${p.a})`; x.fillRect(p.x * W, p.y * H, 1, 1); }
    let best = null, bd = Infinity;
    stars.forEach((s, i) => {
      let a = still ? 1 : life(s, t);
      if (a < 0) { stars[i] = s = star(t); a = 0; }
      s.a = a * (.72 + .28 * Math.sin(t / 950 + s.ph));
      s.px = s.x * W; s.py = s.y * H;
      if (mx >= 0 && a > .35) { const dd = Math.hypot(s.px - mx, s.py - my); if (dd < bd) { bd = dd; best = s; } }
    });
    const ray = mx < 0 ? 0 : Math.max(0, 1 - Math.max(0, t - moved - 1800) / 1200);
    if (best && ray > 0) {
      const g = x.createLinearGradient(mx, my, best.px, best.py);
      g.addColorStop(0, "rgba(255,255,255,0)");
      g.addColorStop(.25, `rgba(255,255,255,${.12 * ray * best.a})`);
      g.addColorStop(1, `rgba(255,255,255,${.42 * ray * best.a})`);
      x.strokeStyle = g; x.lineWidth = 1; x.beginPath(); x.moveTo(mx, my); x.lineTo(best.px, best.py); x.stroke();
    }
    for (const s of stars) {
      const boost = s === best ? 1 + .6 * ray : 1, R = s.r * 7 * boost;
      const g = x.createRadialGradient(s.px, s.py, 0, s.px, s.py, R);
      g.addColorStop(0, `rgba(255,250,255,${Math.min(1, .95 * s.a * boost)})`);
      g.addColorStop(.22, `rgba(205,190,255,${.35 * s.a})`);
      g.addColorStop(1, "rgba(205,190,255,0)");
      x.fillStyle = g; x.beginPath(); x.arc(s.px, s.py, R, 0, 6.283); x.fill();
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
