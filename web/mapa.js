/* Mapa vetorial estilizado de São Paulo (offline, sem tiles). Uso acadêmico. */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const LON0 = -46.84, LON1 = -46.34, LAT0 = -23.36, LAT1 = -23.80;
  const COS = Math.cos(23.58 * Math.PI / 180);
  const K = 1000 / ((LON1 - LON0) * COS);
  const W = 1000, H = Math.round((LAT0 - LAT1) * K);

  function xy(lat, lon) { return [(lon - LON0) * COS * K, (LAT0 - lat) * K]; }
  function pts(arr) { return arr.map(([lon, lat]) => xy(lat, lon).map(v => v.toFixed(1)).join(",")).join(" "); }
  // curva suave (Catmull-Rom -> Bezier) passando pelos pontos
  function suave(arr, fechado) {
    const P = arr.map(([lon, lat]) => xy(lat, lon)), n = P.length;
    const g = i => fechado ? P[(i + n) % n] : P[Math.max(0, Math.min(n - 1, i))];
    let d = `M${P[0][0].toFixed(1)},${P[0][1].toFixed(1)}`;
    const fim = fechado ? n : n - 1;
    for (let i = 0; i < fim; i++) {
      const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2);
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += `C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
    }
    return fechado ? d + "Z" : d;
  }
  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  // Contorno aproximado do município (lon, lat)
  const CIDADE = [
    [-46.750,-23.380],[-46.700,-23.362],[-46.650,-23.372],[-46.605,-23.398],[-46.565,-23.438],[-46.530,-23.455],
    [-46.505,-23.462],[-46.470,-23.478],[-46.430,-23.483],[-46.395,-23.478],[-46.368,-23.492],[-46.366,-23.520],
    [-46.372,-23.545],[-46.385,-23.575],[-46.405,-23.598],[-46.440,-23.618],[-46.475,-23.628],[-46.515,-23.622],
    [-46.550,-23.618],[-46.575,-23.628],[-46.595,-23.655],[-46.615,-23.675],[-46.628,-23.700],[-46.622,-23.740],
    [-46.625,-23.790],[-46.640,-23.850],[-46.690,-23.870],[-46.735,-23.840],[-46.760,-23.790],[-46.790,-23.745],
    [-46.815,-23.705],[-46.806,-23.668],[-46.792,-23.628],[-46.782,-23.600],[-46.765,-23.585],[-46.770,-23.560],
    [-46.782,-23.540],[-46.800,-23.520],[-46.818,-23.495],[-46.808,-23.460],[-46.790,-23.430],[-46.775,-23.400]
  ];
  const TIETE = [[-46.820,-23.505],[-46.790,-23.515],[-46.760,-23.522],[-46.735,-23.527],[-46.705,-23.522],[-46.675,-23.513],
    [-46.645,-23.515],[-46.615,-23.520],[-46.590,-23.520],[-46.560,-23.518],[-46.530,-23.510],[-46.500,-23.497],
    [-46.465,-23.487],[-46.430,-23.482],[-46.380,-23.478]];
  const PINHEIROS = [[-46.745,-23.528],[-46.735,-23.545],[-46.718,-23.563],[-46.703,-23.582],[-46.698,-23.605],
    [-46.696,-23.630],[-46.700,-23.655],[-46.705,-23.680],[-46.708,-23.700]];
  const TAMANDUATEI = [[-46.632,-23.520],[-46.628,-23.545],[-46.618,-23.565],[-46.605,-23.585],[-46.590,-23.605],[-46.575,-23.625]];
  const VIAS = [
    [[-46.640,-23.550],[-46.600,-23.547],[-46.560,-23.545],[-46.520,-23.543],[-46.480,-23.541],[-46.440,-23.545]], // Radial Leste
    [[-46.640,-23.555],[-46.648,-23.585],[-46.655,-23.615],[-46.658,-23.645],[-46.662,-23.675]],                   // 23 de Maio / W. Luís
    [[-46.660,-23.562],[-46.690,-23.578],[-46.720,-23.590],[-46.760,-23.605]],                                     // Rebouças / Francisco Morato
    [[-46.635,-23.530],[-46.628,-23.500],[-46.620,-23.470],[-46.610,-23.440]],                                     // Norte (Cruzeiro do Sul)
    [[-46.650,-23.548],[-46.680,-23.535],[-46.710,-23.520],[-46.745,-23.505]]                                      // Oeste (Lapa)
  ];
  const BILLINGS = [[-46.635,-23.735],[-46.660,-23.745],[-46.675,-23.770],[-46.665,-23.800],[-46.645,-23.815],[-46.628,-23.790],[-46.625,-23.760]];
  const GUARAPIRANGA = [[-46.715,-23.695],[-46.735,-23.705],[-46.760,-23.725],[-46.770,-23.750],[-46.750,-23.760],[-46.730,-23.745],[-46.718,-23.720]];
  const ZONAS = [["Norte",-23.445,-46.640],["Leste",-23.575,-46.470],["Sul",-23.690,-46.668],["Oeste",-23.595,-46.772],["Centro",-23.542,-46.642]];

  function criar(svg, lojas, opt) {
    opt = opt || {};
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svg.innerHTML = "";
    const defs = el("defs", {}, svg);
    const sfx = opt.sufixo || "";
    const fl = el("filter", { id: "glow" + sfx, x: "-30%", y: "-30%", width: "160%", height: "160%" }, defs);
    el("feGaussianBlur", { stdDeviation: 3.5 }, fl);
    // moto de entrega vista de cima, apontando para +x
    const moto = el("g", { id: "icoMoto" + sfx }, defs);
    el("rect", { x: -13, y: -2, width: 5, height: 4, rx: 1.2, fill: "#111" }, moto);
    el("rect", { x: 8, y: -2, width: 5, height: 4, rx: 1.2, fill: "#111" }, moto);
    el("rect", { x: -9, y: -3, width: 18, height: 6, rx: 3, fill: "#FFCC00", stroke: "#000", "stroke-width": 1.5 }, moto);
    el("rect", { x: -9.5, y: -4.5, width: 6, height: 9, rx: 1.5, fill: "#FF5A1F", stroke: "#000", "stroke-width": 1.2 }, moto);
    el("line", { x1: 5, y1: -5.5, x2: 5, y2: 5.5, stroke: "#000", "stroke-width": 2, "stroke-linecap": "round" }, moto);
    el("circle", { cx: -0.5, cy: 0, r: 3.6, fill: "#000" }, moto);
    el("circle", { cx: 0.6, cy: -0.8, r: 1.1, fill: "#FFCC00" }, moto);
    // carro do cliente (retirada), apontando para +x
    const car = el("g", { id: "icoCarro" + sfx }, defs);
    [[-7, -6], [3, -6], [-7, 4.5], [3, 4.5]].forEach(([x, y]) => el("rect", { x, y, width: 4, height: 1.8, rx: .6, fill: "#111" }, car));
    el("rect", { x: -10, y: -4.5, width: 20, height: 9, rx: 3, fill: "#5CC8FF", stroke: "#000", "stroke-width": 1.5 }, car);
    el("rect", { x: -4.5, y: -3.2, width: 7.5, height: 6.4, rx: 1.5, fill: "#0B2A3A" }, car);
    el("rect", { x: 8.2, y: -3.5, width: 1.6, height: 2.2, fill: "#FFF3A0" }, car);
    el("rect", { x: 8.2, y: 1.3, width: 1.6, height: 2.2, fill: "#FFF3A0" }, car);
    // casa do cliente
    const casa = el("g", { id: "icoCasa" + sfx }, defs);
    el("path", { d: "M-8,-1 L0,-8 L8,-1 L8,7 L-8,7 Z", fill: "#FFF6D6", stroke: "#000", "stroke-width": 1.6, "stroke-linejoin": "round" }, casa);
    el("rect", { x: -2.2, y: 1.5, width: 4.4, height: 5.5, fill: "#000" }, casa);
    const cp = el("clipPath", { id: "clipCidade" + sfx }, defs);
    el("path", { d: suave(CIDADE, true) }, cp);

    const base = el("g", { class: "m-base" }, svg);
    el("path", { d: suave(CIDADE, true), class: "m-cidade" }, base);
    // textura de quarteirões, recortada pelo contorno
    const grade = el("g", { "clip-path": `url(#clipCidade${opt.sufixo || ""})`, class: "m-grade" }, base);
    const gr = el("g", { transform: `rotate(-14 ${W / 2} ${H / 2})` }, grade);
    for (let i = -400; i < 1400; i += 17) {
      el("line", { x1: i, y1: -300, x2: i, y2: H + 300 }, gr);
      el("line", { x1: -300, y1: i, x2: W + 300, y2: i }, gr);
    }
    el("path", { d: suave(BILLINGS, true), class: "m-agua" }, base);
    el("path", { d: suave(GUARAPIRANGA, true), class: "m-agua" }, base);
    VIAS.forEach(v => el("path", { d: suave(v, false), class: "m-via" }, base));
    [TIETE, PINHEIROS, TAMANDUATEI].forEach(r => el("path", { d: suave(r, false), class: "m-rio" }, base));
    if (!opt.semZonas) ZONAS.forEach(([n, lat, lon]) => {
      const [x, y] = xy(lat, lon);
      el("text", { x, y, class: "m-zona", "text-anchor": "middle" }, base).textContent = n;
    });

    const camadas = {};
    ["historico", "rotas", "destinos", "lojas", "motos", "rotulos"].forEach(n => camadas[n] = el("g", { class: "m-" + n }, svg));

    const lojaEls = {};
    (lojas || []).forEach(l => {
      const [x, y] = xy(l.lat, l.lon);
      const g = el("g", { transform: `translate(${x},${y})`, class: "loja " + l.tipo }, camadas.lojas);
      el("circle", { r: 16, class: "loja-halo" }, g);
      if (l.tipo === "ze_point") {
        el("rect", { x: -9, y: -9, width: 18, height: 18, rx: 3, transform: "rotate(45)", class: "loja-ico" }, g);
        el("text", { y: 4.5, "text-anchor": "middle", class: "loja-letra" }, g).textContent = "Z";
      } else {
        el("circle", { r: 8, class: "loja-ico" }, g);
      }
      if (!opt.semNomes) el("text", { x: 14, y: -12, class: "loja-nome" }, g).textContent = l.nome.replace(/^(Zé Point|Açougue Parceiro|Casa de Carnes|Boutique de Carnes) /, "");
      const badge = el("g", { class: "loja-badge", transform: "translate(-15,-17)", style: "display:none" }, g);
      el("circle", { r: 8 }, badge);
      el("text", { y: 3.5, "text-anchor": "middle" }, badge);
      lojaEls[l.id] = { g, badge, x, y };
    });
    return { svg, camadas, lojaEls, W, H };
  }

  // Rota "de rua": segue a malha inclinada do mapa (-14°), com dobras determinísticas por origem/destino
  const ANG = -14 * Math.PI / 180, CA = Math.cos(ANG), SA = Math.sin(ANG);
  const rot = ([x, y]) => [x * CA + y * SA, -x * SA + y * CA];
  const unrot = ([u, v]) => [u * CA - v * SA, u * SA + v * CA];
  function rota(a, b) {
    const A = rot(xy(a.lat, a.lon)), B = rot(xy(b.lat, b.lon));
    const h = Math.abs(Math.sin(A[0] * 12.9898 + B[1] * 78.233)), h2 = Math.abs(Math.sin(A[1] * 39.42 + B[0] * 7.17));
    const du = B[0] - A[0], dv = B[1] - A[1];
    const u1 = A[0] + du * (0.18 + 0.22 * h), v1 = A[1] + dv * (0.35 + 0.35 * h2);
    const u2 = A[0] + du * (0.62 + 0.25 * h2), v2 = A[1] + dv * (0.75 + 0.2 * h);
    const raw = [[A[0], A[1]], [u1, A[1]], [u1, v1], [u2, v1], [u2, v2], [B[0], v2], [B[0], B[1]]];
    const p = [];
    raw.forEach(q => { const w = unrot(q); const l = p[p.length - 1]; if (!l || Math.hypot(w[0] - l[0], w[1] - l[1]) > 0.5) p.push(w); });
    let tot = 0; const seg = [];
    for (let i = 1; i < p.length; i++) { const d = Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); seg.push(d); tot += d; }
    return { p, seg, tot };
  }
  function ponto(r, f) {
    f = Math.max(0, Math.min(1, f));
    let alvo = r.tot * f;
    for (let i = 0; i < r.seg.length; i++) {
      if (alvo <= r.seg[i] || i === r.seg.length - 1) {
        const t = r.seg[i] ? alvo / r.seg[i] : 0, a = r.p[i], b = r.p[i + 1];
        return { x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, ang: Math.atan2(b[1] - a[1], b[0] - a[0]) };
      }
      alvo -= r.seg[i];
    }
    const u = r.p[r.p.length - 1]; return { x: u[0], y: u[1], ang: 0 };
  }
  function trecho(r, f) {   // pontos percorridos até a fração f
    const out = [r.p[0]]; let alvo = r.tot * Math.max(0, Math.min(1, f));
    for (let i = 0; i < r.seg.length; i++) {
      if (alvo >= r.seg[i]) { out.push(r.p[i + 1]); alvo -= r.seg[i]; }
      else { const t = r.seg[i] ? alvo / r.seg[i] : 0, a = r.p[i], b = r.p[i + 1]; out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); break; }
    }
    return out;
  }
  const str = arr => arr.map(p => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");

  window.ZeMapa = { criar, rota, ponto, trecho, str, xy, el, W, H };
})();
