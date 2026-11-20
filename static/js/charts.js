/* Small dependency-free SVG charts: line chart with reference line + hover
   crosshair, and a sparkline. Data: [{date: "YYYY-MM-DD", value: Number}] */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

  function el(name, attrs, parent) {
    const node = document.createElementNS(NS, name);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  const toTime = (d) => new Date(d + "T00:00:00Z").getTime();
  const fmtDate = (d) => { const t = new Date(d + "T00:00:00Z"); return `${t.getUTCDate()} ${MONTHS[t.getUTCMonth()]} ${t.getUTCFullYear()}`; };

  function niceTicks(min, max, count) {
    const span = max - min || 1;
    const step0 = span / count;
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= count) || 10 * mag;
    const ticks = [];
    for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(+v.toFixed(6));
    return ticks;
  }

  function lineChart(container, data, opts) {
    opts = Object.assign({ prefix: "", suffix: "", decimals: 2, height: 230, ref: null, label: "" }, opts || {});
    container.innerHTML = "";
    if (!data || data.length < 2) {
      container.innerHTML = `<p class="chart-empty">${opts.empty || "Not enough data yet."}</p>`;
      return;
    }
    const W = 560, H = opts.height, m = { t: 14, r: 64, b: 26, l: 44 };
    const xs = data.map((d) => toTime(d.date)), ys = data.map((d) => d.value);
    let ymin = Math.min(...ys), ymax = Math.max(...ys);
    if (opts.ref) { ymin = Math.min(ymin, opts.ref.value); ymax = Math.max(ymax, opts.ref.value); }
    const pad = (ymax - ymin) * 0.12 || 1;
    ymin -= pad; ymax += pad;
    const x0 = xs[0], x1 = xs[xs.length - 1];
    const sx = (t) => m.l + ((t - x0) / (x1 - x0 || 1)) * (W - m.l - m.r);
    const sy = (v) => H - m.b - ((v - ymin) / (ymax - ymin)) * (H - m.t - m.b);
    const fmt = (v) => opts.prefix + v.toLocaleString("en-NG", { minimumFractionDigits: opts.decimals, maximumFractionDigits: opts.decimals }) + opts.suffix;

    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": opts.label, tabindex: 0 }, container);
    const grid = el("g", { class: "grid" }, svg), axis = el("g", { class: "axis" }, svg);
    niceTicks(ymin, ymax, 4).forEach((v) => {
      el("line", { x1: m.l, x2: W - m.r, y1: sy(v), y2: sy(v) }, grid);
      const t = el("text", { x: m.l - 8, y: sy(v) + 4, "text-anchor": "end" }, axis);
      t.textContent = opts.prefix + v.toLocaleString("en-NG", { maximumFractionDigits: v % 1 ? 1 : 0 });
    });
    // month ticks
    const first = new Date(x0), last = new Date(x1);
    let cur = Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 1);
    const months = [];
    while (cur <= x1) { months.push(cur); const d = new Date(cur); cur = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1); }
    const every = Math.ceil(months.length / 6) || 1;
    months.forEach((t, i) => {
      if (i % every) return;
      const tx = el("text", { x: sx(t), y: H - 6, "text-anchor": "middle" }, axis);
      tx.textContent = MONTHS[new Date(t).getUTCMonth()];
    });

    if (opts.ref) {
      const y = sy(opts.ref.value);
      el("line", { class: "ref", x1: m.l, x2: W - m.r, y1: y, y2: y }, svg);
      const rl = el("text", { class: "ref-label", x: W - m.r + 6, y: y + 4 }, svg);
      rl.textContent = opts.ref.short || "";
    }

    const d = data.map((p, i) => `${i ? "L" : "M"}${sx(xs[i]).toFixed(1)},${sy(p.value).toFixed(1)}`).join("");
    el("path", { class: "series", d }, svg);
    const lastPt = data[data.length - 1];
    el("circle", { class: "dot", cx: sx(x1), cy: sy(lastPt.value), r: 4 }, svg);
    const endLabel = el("text", { class: "end-label", x: sx(x1) + 8, y: sy(lastPt.value) + 4 }, svg);
    endLabel.textContent = fmt(lastPt.value);
    // keep end and reference labels from colliding
    if (opts.ref && Math.abs(sy(lastPt.value) - sy(opts.ref.value)) < 14) {
      endLabel.setAttribute("y", sy(lastPt.value) + (sy(lastPt.value) < sy(opts.ref.value) ? -6 : 16));
    }

    // hover layer
    const cross = el("line", { class: "crosshair", y1: m.t, y2: H - m.b, opacity: 0 }, svg);
    const hdot = el("circle", { class: "dot", r: 4.5, opacity: 0 }, svg);
    const tip = document.createElement("div");
    tip.className = "tooltip";
    container.appendChild(tip);
    const hit = el("rect", { x: m.l, y: 0, width: W - m.l - m.r, height: H, fill: "transparent" }, svg);
    let idx = data.length - 1;

    function show(i) {
      idx = Math.max(0, Math.min(data.length - 1, i));
      const p = data[idx], cx = sx(xs[idx]), cy = sy(p.value);
      cross.setAttribute("x1", cx); cross.setAttribute("x2", cx); cross.setAttribute("opacity", 1);
      hdot.setAttribute("cx", cx); hdot.setAttribute("cy", cy); hdot.setAttribute("opacity", 1);
      const box = svg.getBoundingClientRect(), scale = box.width / W;
      tip.style.left = cx * scale + "px";
      tip.style.top = cy * scale + "px";
      tip.innerHTML = `<b>${fmt(p.value)}</b><br>${fmtDate(p.date)}`;
      tip.style.opacity = 1;
    }
    function hide() { cross.setAttribute("opacity", 0); hdot.setAttribute("opacity", 0); tip.style.opacity = 0; }
    function nearest(evt) {
      const box = svg.getBoundingClientRect();
      const x = ((evt.clientX - box.left) / box.width) * W;
      const t = x0 + ((x - m.l) / (W - m.l - m.r)) * (x1 - x0);
      let best = 0, bd = Infinity;
      xs.forEach((v, i) => { const dd = Math.abs(v - t); if (dd < bd) { bd = dd; best = i; } });
      return best;
    }
    hit.addEventListener("pointermove", (e) => show(nearest(e)));
    hit.addEventListener("pointerleave", hide);
    svg.addEventListener("focus", () => show(idx));
    svg.addEventListener("blur", hide);
    svg.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft") { show(idx - 1); e.preventDefault(); }
      if (e.key === "ArrowRight") { show(idx + 1); e.preventDefault(); }
    });

    // table view: every value readable without hovering
    const det = document.createElement("details");
    det.className = "table-view";
    det.innerHTML = `<summary>Show as table</summary><div class="scroll"><table><thead><tr><th>Date</th><th class="num">Value</th></tr></thead><tbody>${
      data.slice().reverse().map((p) => `<tr><td>${fmtDate(p.date)}</td><td class="num">${fmt(p.value)}</td></tr>`).join("")
    }</tbody></table></div>`;
    container.appendChild(det);
  }

  function sparkline(container, data) {
    container.innerHTML = "";
    if (!data || data.length < 2) return;
    const W = 200, H = 34, ys = data.map((d) => d.value);
    const min = Math.min(...ys), max = Math.max(...ys), span = max - min || 1;
    const pts = data.map((p, i) => `${((i / (data.length - 1)) * (W - 4) + 2).toFixed(1)},${(H - 3 - ((p.value - min) / span) * (H - 6)).toFixed(1)}`);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", class: "spark", "aria-hidden": "true" }, container);
    el("polyline", { points: pts.join(" "), fill: "none", stroke: "var(--brand)", "stroke-width": 1.75, "vector-effect": "non-scaling-stroke", "stroke-linejoin": "round" }, svg);
  }

  window.RoiCharts = { lineChart, sparkline };
})();
