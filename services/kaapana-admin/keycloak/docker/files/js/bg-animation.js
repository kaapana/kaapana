/*
 * Kaapana login background: transient "constellations" of medical-imaging nodes
 * that form, hold, then dissolve. Vanilla canvas, no dependencies (CSP/offline safe).
 * Node glyphs are tinted versions of the icons in ./icons/.
 */
(function () {
  "use strict";

  var canvas = document.getElementById("kaapana-bg");
  if (!canvas) return;
  var ctx = canvas.getContext("2d");

  var reduceMotion = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // palette + opacities adapt to the OS colour scheme
  var darkMQ = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
  var COLORS, A_EDGE, A_NODE, A_GLYPH;
  function applyScheme() {
    var dark = darkMQ ? darkMQ.matches : true;
    if (dark) {
      COLORS = ["#1AB4D4", "#8DC445", "#3f8fd0", "#6fd0e0"];
      A_EDGE = 0.16; A_NODE = 0.70; A_GLYPH = 0.55;
    } else {
      COLORS = ["#005BA0", "#0288a5", "#5a9e2f", "#1AB4D4"];
      A_EDGE = 0.22; A_NODE = 0.55; A_GLYPH = 0.55;
    }
  }
  applyScheme();

  // ---- icons: preload + tint cache (black silhouettes → coloured sprites) ----
  var ICONS = ["ai", "brain", "microscope", "slide", "mri", "network", "neural", "workflow"];
  var img = {}, ready = {};
  ICONS.forEach(function (name) {
    var im = new Image();
    im.onload = function () { ready[name] = true; if (reduceMotion) staticRender(); };
    im.src = (window.KAAPANA_ICONS_BASE || "icons/") + name + ".png";
    img[name] = im;
  });
  var tintCache = {};
  function sprite(name, hex) {
    if (!ready[name]) return null;
    var key = name + "|" + hex;
    if (tintCache[key]) return tintCache[key];
    var S = 128;
    var c = document.createElement("canvas");
    c.width = S; c.height = S;
    var g = c.getContext("2d");
    g.drawImage(img[name], 0, 0, S, S);
    g.globalCompositeOperation = "source-in";
    g.fillStyle = hex;
    g.fillRect(0, 0, S, S);
    tintCache[key] = c;
    return c;
  }

  var W = 0, H = 0, dpr = 1;
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = canvas.clientWidth;
    H = canvas.clientHeight;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function rand(a, b) { return a + Math.random() * (b - a); }
  function pick(arr) { return arr[(Math.random() * arr.length) | 0]; }

  // cap how many of each icon may be on screen at once
  var MAX_PER_ICON = 2;
  var iconUse = {};
  ICONS.forEach(function (n) { iconUse[n] = 0; });

  // ---- constellation model ----
  function makeConstellation() {
    var cx = rand(0.08, 0.92) * W;
    var cy = rand(0.08, 0.92) * H;
    var spread = rand(80, 160);
    var count = (rand(4, 7)) | 0;
    var color = pick(COLORS);
    var nodes = [];
    for (var i = 0; i < count; i++) {
      var glyph = null;
      if (Math.random() < 0.5) {
        var avail = ICONS.filter(function (n) { return iconUse[n] < MAX_PER_ICON; });
        if (avail.length) { glyph = pick(avail); iconUse[glyph]++; }
      }
      nodes.push({
        x: cx + rand(-spread, spread),
        y: cy + rand(-spread, spread),
        vx: rand(-4, 4), vy: rand(-4, 4),
        r: glyph ? rand(18, 26) : rand(1.6, 2.8),
        glyph: glyph,
        phase: rand(0, Math.PI * 2)
      });
    }
    // edges: connect each node to its nearest 1-2 neighbours
    var edges = [];
    for (var a = 0; a < nodes.length; a++) {
      var dists = [];
      for (var b = 0; b < nodes.length; b++) {
        if (a === b) continue;
        var dx = nodes[a].x - nodes[b].x, dy = nodes[a].y - nodes[b].y;
        dists.push({ b: b, d: dx * dx + dy * dy });
      }
      dists.sort(function (p, q) { return p.d - q.d; });
      var links = 1 + ((Math.random() < 0.5) ? 1 : 0);
      for (var l = 0; l < links && l < dists.length; l++) {
        var j = dists[l].b;
        if (a < j) edges.push([a, j]); else edges.push([j, a]);
      }
    }
    return {
      nodes: nodes, edges: edges, color: color,
      born: now(),
      fadeIn: rand(1200, 2000),
      hold: rand(4000, 8000),
      fadeOut: rand(1800, 2800),
      alpha: 0, dead: false
    };
  }

  function releaseGlyphs(c) {
    for (var i = 0; i < c.nodes.length; i++) {
      if (c.nodes[i].glyph) iconUse[c.nodes[i].glyph]--;
    }
  }

  function now() { return (window.performance && performance.now) ? performance.now() : Date.now(); }

  function envelope(c, t) {
    var age = t - c.born;
    if (age < c.fadeIn) return age / c.fadeIn;
    if (age < c.fadeIn + c.hold) return 1;
    var out = age - c.fadeIn - c.hold;
    if (out < c.fadeOut) return 1 - out / c.fadeOut;
    c.dead = true; return 0;
  }

  var constellations = [];
  var TARGET = 5;

  function hexA(hex, a) {
    var n = parseInt(hex.slice(1), 16);
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }

  function drawConstellation(c, t) {
    var e = envelope(c, t);
    c.alpha = e;
    if (e <= 0) return;
    var eased = e * e * (3 - 2 * e); // smoothstep

    // edges
    ctx.lineWidth = 1;
    for (var i = 0; i < c.edges.length; i++) {
      var n1 = c.nodes[c.edges[i][0]], n2 = c.nodes[c.edges[i][1]];
      ctx.strokeStyle = hexA(c.color, A_EDGE * eased);
      ctx.beginPath(); ctx.moveTo(n1.x, n1.y); ctx.lineTo(n2.x, n2.y); ctx.stroke();
    }
    // nodes
    for (var k = 0; k < c.nodes.length; k++) {
      var nd = c.nodes[k];
      var pulse = 0.85 + 0.15 * Math.sin(t / 900 + nd.phase);
      if (nd.glyph) {
        var spr = sprite(nd.glyph, c.color);
        if (spr) {
          var sz = nd.r * 2.4;
          ctx.globalAlpha = A_GLYPH * eased * pulse;
          ctx.drawImage(spr, nd.x - sz / 2, nd.y - sz / 2, sz, sz);
          ctx.globalAlpha = 1;
        }
      } else {
        ctx.fillStyle = hexA(c.color, A_NODE * eased * pulse);
        ctx.beginPath(); ctx.arc(nd.x, nd.y, nd.r, 0, Math.PI * 2); ctx.fill();
      }
    }
  }

  function step(nodes, dt) {
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      n.x += n.vx * dt; n.y += n.vy * dt;
    }
  }

  var last = now();
  function frame() {
    var t = now();
    var dt = Math.min((t - last) / 1000, 0.05);
    last = t;
    ctx.clearRect(0, 0, W, H);

    for (var i = constellations.length - 1; i >= 0; i--) {
      var c = constellations[i];
      step(c.nodes, dt);
      drawConstellation(c, t);
      if (c.dead) { releaseGlyphs(c); constellations.splice(i, 1); }
    }
    while (constellations.length < TARGET) constellations.push(makeConstellation());

    requestAnimationFrame(frame);
  }

  function staticRender() {
    ctx.clearRect(0, 0, W, H);
    ICONS.forEach(function (n) { iconUse[n] = 0; });
    for (var i = 0; i < 3; i++) {
      var c = makeConstellation();
      c.born = now() - c.fadeIn; // fully faded in
      drawConstellation(c, now());
    }
  }

  window.addEventListener("resize", function () {
    resize();
    if (reduceMotion) staticRender();
  });
  if (darkMQ && darkMQ.addEventListener) {
    darkMQ.addEventListener("change", function () {
      applyScheme();
      if (reduceMotion) staticRender();
    });
  }
  resize();

  if (reduceMotion) {
    staticRender();
  } else {
    for (var i = 0; i < TARGET; i++) {
      var c = makeConstellation();
      c.born = now() - rand(0, c.fadeIn + c.hold); // stagger so they don't all appear at once
      constellations.push(c);
    }
    requestAnimationFrame(frame);
  }
})();
