# -*- coding: utf-8 -*-
"""
Zé Express Churrasco - protótipo acadêmico (Projeto Integrador UNINOVE)
Servidor local em Python puro (sem pip). Porta padrão 8170.
  /        app do cliente (celular)
  /telao   central de operações (mapa + indicadores)
  /qr      QR Code para a plateia escanear
"""
import json, math, os, random, socket, sqlite3, threading, time, hashlib
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))


def achar_web():
    """Localiza a pasta com as telas (web/) mesmo se o script for executado de outro lugar."""
    cands = [os.path.join(BASE, "web"), os.path.join(os.getcwd(), "web"), BASE, os.getcwd()]
    for c in cands:
        if os.path.isfile(os.path.join(c, "telao.html")):
            return c
    return os.path.join(BASE, "web")


WEB = achar_web()
DB_PATH = os.path.join(BASE, "dados", "zeexpress.db")

with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)
LOJAS = {l["id"]: l for l in CFG["lojas"]}
CAT = {c["id"]: c for c in CFG["catalogo"]}

# ---------------------------------------------------------------- CEP -> bairro
# Faixas aproximadas de CEP do município de São Paulo (5 primeiros dígitos).
# Posição = centro aproximado do bairro + deslocamento pelo número (fins acadêmicos).
FAIXAS_CEP = [
    (1000, 1099, "Sé / Centro", -23.5500, -46.6340), (1100, 1199, "Bom Retiro / Luz", -23.5300, -46.6380),
    (1200, 1299, "Santa Cecília / Higienópolis", -23.5400, -46.6520), (1300, 1399, "Bela Vista / Consolação", -23.5560, -46.6500),
    (1400, 1499, "Jardim Paulista", -23.5670, -46.6610), (1500, 1599, "Liberdade / Aclimação", -23.5680, -46.6300),
    (2000, 2099, "Santana", -23.5020, -46.6250), (2100, 2199, "Vila Maria / Vila Guilherme", -23.5100, -46.5900),
    (2200, 2299, "Vila Medeiros / Jaçanã", -23.4800, -46.5800), (2300, 2399, "Tucuruvi / Tremembé", -23.4700, -46.6050),
    (2400, 2499, "Mandaqui", -23.4800, -46.6350), (2500, 2599, "Casa Verde", -23.5050, -46.6600),
    (2600, 2699, "Cachoeirinha", -23.4700, -46.6700), (2700, 2799, "Limão", -23.5000, -46.6800),
    (2800, 2899, "Brasilândia", -23.4650, -46.6900), (2900, 2999, "Freguesia do Ó", -23.4900, -46.7000),
    (3000, 3099, "Brás / Pari", -23.5400, -46.6150), (3100, 3199, "Mooca", -23.5550, -46.5950),
    (3200, 3299, "Vila Prudente", -23.5850, -46.5750), (3300, 3399, "Tatuapé", -23.5400, -46.5750),
    (3400, 3499, "Vila Formosa / Carrão", -23.5550, -46.5450), (3500, 3599, "Vila Matilde / Aricanduva", -23.5400, -46.5250),
    (3600, 3699, "Penha", -23.5250, -46.5450), (3700, 3799, "Cangaíba", -23.5050, -46.5250),
    (3800, 3899, "Ermelino Matarazzo", -23.4950, -46.4800), (3900, 3999, "Sapopemba", -23.6000, -46.5150),
    (4000, 4099, "Paraíso / Vila Mariana", -23.5850, -46.6400), (4100, 4199, "Chácara Klabin", -23.5950, -46.6300),
    (4200, 4299, "Ipiranga", -23.5900, -46.6050), (4300, 4399, "Saúde / Jabaquara", -23.6200, -46.6350),
    (4400, 4499, "Cidade Ademar", -23.6650, -46.6500), (4500, 4599, "Itaim Bibi / Vila Olímpia", -23.5900, -46.6800),
    (4600, 4699, "Campo Belo / Brooklin", -23.6200, -46.6750), (4700, 4799, "Santo Amaro", -23.6500, -46.7050),
    (4800, 4899, "Socorro / Grajaú", -23.7100, -46.6900), (4900, 4999, "Jardim Ângela", -23.7000, -46.7400),
    (5000, 5099, "Perdizes / Pompeia", -23.5350, -46.6800), (5100, 5199, "Pirituba / Jaraguá", -23.4850, -46.7250),
    (5200, 5299, "Perus", -23.4100, -46.7500), (5300, 5399, "Vila Leopoldina / Jaguaré", -23.5350, -46.7300),
    (5400, 5499, "Pinheiros", -23.5650, -46.6900), (5500, 5599, "Butantã", -23.5720, -46.7200),
    (5600, 5699, "Morumbi", -23.6000, -46.7200), (5700, 5799, "Vila Andrade / Campo Limpo", -23.6250, -46.7400),
    (5800, 5899, "Capão Redondo", -23.6600, -46.7700),
    (8000, 8099, "São Miguel Paulista", -23.4950, -46.4450), (8100, 8199, "Itaim Paulista", -23.5000, -46.4000),
    (8200, 8299, "Itaquera", -23.5400, -46.4550), (8300, 8399, "São Mateus", -23.6000, -46.4750),
    (8400, 8499, "Guaianases / Cidade Tiradentes", -23.5600, -46.4050),
]
BAIRROS = [{"idx": i, "nome": f[2]} for i, f in enumerate(FAIXAS_CEP)]
BAIRROS_ORD = sorted(BAIRROS, key=lambda b: b["nome"])


def _jitter(chave, raio=0.011):
    h = hashlib.md5(chave.encode()).digest()
    a = h[0] / 255 * 2 * math.pi
    r = (0.25 + 0.75 * h[1] / 255) * raio
    return r * math.sin(a), r * math.cos(a)


def localizar(cep, numero, bairro_idx=None):
    cep = "".join(ch for ch in str(cep or "") if ch.isdigit())
    faixa = None
    if bairro_idx is not None and str(bairro_idx) != "":
        try:
            faixa = FAIXAS_CEP[int(bairro_idx)]
        except (ValueError, IndexError):
            faixa = None
    elif len(cep) == 8:
        p5 = int(cep[:5])
        for f in FAIXAS_CEP:
            if f[0] <= p5 <= f[1]:
                faixa = f
                break
    if not faixa:
        return None
    dlat, dlon = _jitter(f"{cep}-{numero}-{bairro_idx}")
    return {"bairro": faixa[2], "lat": faixa[3] + dlat, "lon": faixa[4] + dlon}


# ---------------------------------------------------------------- banco
LOCK = threading.RLock()
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
DB = sqlite3.connect(DB_PATH, check_same_thread=False)
DB.row_factory = sqlite3.Row
DB.executescript("""
CREATE TABLE IF NOT EXISTS pedidos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT, nome TEXT, itens TEXT,
  subtotal REAL, desconto REAL, taxa REAL, total REAL,
  cep TEXT, numero TEXT, bairro TEXT, lat REAL, lon REAL,
  modo TEXT, loja_id TEXT, dist_km REAL, preparo_min REAL, desloc_min REAL, total_min REAL,
  t_criado REAL, t_prep_ini REAL, t_prep_fim REAL, t_saida REAL, t_fim REAL, t_retirado REAL,
  demo INTEGER DEFAULT 0
);
""")
for col, tipo in (("aluno", "INTEGER"), ("mora", "TEXT"), ("usaria", "INTEGER")):
    if col not in [r[1] for r in DB.execute("PRAGMA table_info(pedidos)")]:
        DB.execute(f"ALTER TABLE pedidos ADD COLUMN {col} {tipo}")
DB.commit()
ESTADO = {"demo": False}


def hav_km(a_lat, a_lon, b_lat, b_lon):
    R = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def real_s(min_sim):
    return min_sim * 60.0 / CFG["escala_tempo"]


def limpar_itens(itens):
    out = {}
    for k, v in (itens or {}).items():
        try:
            q = int(v)
        except (TypeError, ValueError):
            continue
        if k in CAT and 0 < q <= 20:
            out[k] = q
    return out


def loja_atende(loja, itens):
    return all(CAT[i]["onde"] in ("todas", loja["tipo"]) for i in itens)


def preparo_min(loja, itens):
    t = CFG["tipos_loja"][loja["tipo"]]["preparo_base_min"]
    kits = sum(q for i, q in itens.items() if CAT[i]["grupo"] == "Kits")
    t += 2 * max(0, kits - 1)
    t += sum(CAT[i]["preparo_extra_min"] * q for i, q in itens.items())
    return float(t)


def inicio_fila(loja_id, agora):
    """Momento (real) em que a loja consegue começar um novo preparo."""
    cap = CFG["tipos_loja"][LOJAS[loja_id]["tipo"]]["capacidade"]
    rows = DB.execute("SELECT t_prep_fim FROM pedidos WHERE loja_id=? AND t_prep_fim>? ORDER BY t_prep_fim",
                      (loja_id, agora)).fetchall()
    fins = [r[0] for r in rows]
    if len(fins) < cap:
        return agora, len(fins)
    return fins[len(fins) - cap], len(fins)


def cotar_loja(loja, itens, local, agora):
    ini, fila = inicio_fila(loja["id"], agora)
    prep = preparo_min(loja, itens)
    espera_min = (ini - agora) * CFG["escala_tempo"] / 60.0
    dist = hav_km(loja["lat"], loja["lon"], local["lat"], local["lon"]) * CFG["fator_ruas"]
    desloc = CFG["minutos_saida_moto"] + dist / CFG["velocidade_moto_kmh"] * 60.0
    desloc_cli = CFG["minutos_saida_cliente"] + dist / CFG["velocidade_cliente_kmh"] * 60.0
    return {"loja": loja, "dist_km": round(dist, 1), "espera_min": round(espera_min, 1), "fila": fila,
            "preparo_min": prep, "desloc_min": round(desloc, 1), "desloc_cli_min": round(desloc_cli, 1),
            "retirada_min": round(espera_min + prep), "entrega_min": round(espera_min + prep + desloc),
            "t_ini": ini}


def cotar(itens, local, agora):
    cands = [l for l in CFG["lojas"] if loja_atende(l, itens)]
    if not cands:
        return None
    cots = [cotar_loja(l, itens, local, agora) for l in cands]
    ret = min(cots, key=lambda c: c["dist_km"])            # retirada: ponto mais próximo
    ent = min(cots, key=lambda c: c["entrega_min"])        # entrega: quem chega primeiro
    subtotal = sum(CAT[i]["preco"] * q for i, q in itens.items())
    taxa = CFG["taxa_entrega_base"] + max(0.0, ent["dist_km"] - 2) * CFG["taxa_entrega_por_km_acima_2km"]
    if subtotal >= CFG["frete_gratis_acima"]:
        taxa = 0.0
    desc = round(subtotal * CFG["desconto_retirada_pct"] / 100.0, 2)

    def pub(c):
        l = c["loja"]
        return {"loja_id": l["id"], "loja_nome": l["nome"], "loja_tipo": l["tipo"],
                "tipo_nome": CFG["tipos_loja"][l["tipo"]]["nome"], "dist_km": c["dist_km"],
                "fila": c["fila"], "espera_min": c["espera_min"], "preparo_min": c["preparo_min"],
                "desloc_min": c["desloc_min"], "desloc_cli_min": c["desloc_cli_min"]}
    return {
        "subtotal": round(subtotal, 2),
        "retirada": dict(pub(ret), total_min=ret["retirada_min"], desconto=desc, taxa=0.0,
                         total=round(subtotal - desc, 2)),
        "entrega": dict(pub(ent), total_min=ent["entrega_min"], desconto=0.0, taxa=round(taxa, 2),
                        total=round(subtotal + taxa, 2)),
        "_ret": ret, "_ent": ent,
    }


def criar_pedido(nome, itens, cep, numero, bairro_idx, modo, demo=False, aluno=None, mora="", usaria=None):
    itens = limpar_itens(itens)
    if not itens:
        return {"ok": False, "erro": "Escolha pelo menos um item."}
    if modo not in ("retirada", "entrega"):
        return {"ok": False, "erro": "Escolha retirada ou entrega."}
    local = localizar(cep, numero, bairro_idx)
    if not local:
        return {"ok": False, "erro": "fora", "bairros": BAIRROS_ORD}
    with LOCK:
        agora = time.time()
        q = cotar(itens, local, agora)
        if not q:
            return {"ok": False, "erro": "Nenhum ponto atende essa combinação de itens."}
        c = q["_ret"] if modo == "retirada" else q["_ent"]
        pub = q[modo]
        t_ini = c["t_ini"]
        t_prep_fim = t_ini + real_s(c["preparo_min"])
        if modo == "entrega":
            t_saida = t_prep_fim                                   # moto sai quando o kit fica pronto
            t_fim = t_saida + real_s(c["desloc_min"])              # chegada no cliente
        else:
            # cliente sai de casa para chegar quando o kit fica pronto; retirado quando os dois se encontram
            t_saida = max(agora, t_prep_fim - real_s(c["desloc_cli_min"]))
            t_fim = max(t_prep_fim, t_saida + real_s(c["desloc_cli_min"]))
        nome = (str(nome or "").strip() or "Cliente")[:40]
        sn = lambda v: None if v is None or v == "" else (1 if v in (1, True, "1", "sim", "true") else 0)
        cur = DB.execute("""INSERT INTO pedidos (codigo,nome,itens,subtotal,desconto,taxa,total,cep,numero,bairro,lat,lon,
                modo,loja_id,dist_km,preparo_min,desloc_min,total_min,t_criado,t_prep_ini,t_prep_fim,t_saida,t_fim,demo,aluno,mora,usaria)
                VALUES ('',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (nome, json.dumps(itens), q["subtotal"], pub["desconto"], pub["taxa"], pub["total"],
                          str(cep or ""), str(numero or "")[:10], local["bairro"], local["lat"], local["lon"],
                          modo, c["loja"]["id"], c["dist_km"], c["preparo_min"],
                          c["desloc_min"] if modo == "entrega" else c["desloc_cli_min"], pub["total_min"],
                          agora, t_ini, t_prep_fim, t_saida, t_fim, 1 if demo else 0,
                          sn(aluno), str(mora or "").strip()[:60], sn(usaria)))
        pid = cur.lastrowid
        codigo = f"ZE-{1000 + pid}"
        DB.execute("UPDATE pedidos SET codigo=? WHERE id=?", (codigo, pid))
        DB.commit()
    return {"ok": True, "pedido": pedido_pub(pid)}


def status_de(r, agora):
    if agora < r["t_prep_ini"]:
        return "fila"
    if agora < r["t_prep_fim"]:
        return "preparo"
    if r["modo"] == "entrega":
        return "rota" if agora < r["t_fim"] else "entregue"
    ret = r["t_retirado"] or r["t_fim"]
    return "pronto" if agora < ret else "retirado"


def row_pub(r, agora):
    l = LOJAS[r["loja_id"]]
    return {"id": r["id"], "codigo": r["codigo"], "nome": r["nome"], "itens": json.loads(r["itens"]),
            "subtotal": r["subtotal"], "desconto": r["desconto"], "taxa": r["taxa"], "total": r["total"],
            "bairro": r["bairro"], "numero": r["numero"], "lat": r["lat"], "lon": r["lon"], "modo": r["modo"],
            "loja_id": l["id"], "loja_nome": l["nome"], "loja_tipo": l["tipo"],
            "dist_km": r["dist_km"], "preparo_min": r["preparo_min"], "desloc_min": r["desloc_min"],
            "total_min": r["total_min"], "t_criado": r["t_criado"], "t_prep_ini": r["t_prep_ini"],
            "t_prep_fim": r["t_prep_fim"], "t_saida": r["t_saida"], "t_fim": r["t_fim"],
            "t_retirado": r["t_retirado"], "status": status_de(r, agora), "demo": r["demo"],
            "aluno": r["aluno"], "mora": r["mora"], "usaria": r["usaria"]}


def pedido_pub(pid):
    r = DB.execute("SELECT * FROM pedidos WHERE id=?", (pid,)).fetchone()
    return row_pub(r, time.time()) if r else None


def estado():
    agora = time.time()
    with LOCK:
        rows = DB.execute("SELECT * FROM pedidos ORDER BY id").fetchall()
    peds = [row_pub(r, agora) for r in rows]
    ativos = [p for p in peds if p["status"] in ("fila", "preparo", "rota", "pronto")
              or (agora - (p["t_retirado"] or p["t_fim"] or 0)) < 45]
    n = len(peds)
    fat = sum(p["total"] for p in peds)
    ent = [p for p in peds if p["modo"] == "entrega"]
    ret = [p for p in peds if p["modo"] == "retirada"]
    ranking = {l["id"]: 0 for l in CFG["lojas"]}
    for p in peds:
        ranking[p["loja_id"]] += 1
    # feed de eventos derivado dos horários
    ev = []
    for p in peds[-60:]:
        ev.append((p["t_criado"], "checkin", p))
        if p["t_prep_fim"] <= agora:
            ev.append((p["t_prep_fim"], "saiu" if p["modo"] == "entrega" else "pronto", p))
        if p["modo"] == "entrega" and p["t_fim"] <= agora:
            ev.append((p["t_fim"], "entregue", p))
        if p["modo"] == "retirada" and (p["t_retirado"] or p["t_fim"]) <= agora:
            ev.append((p["t_retirado"] or p["t_fim"], "retirado", p))
    ev.sort(key=lambda e: e[0], reverse=True)
    feed = [{"t": e[0], "tipo": e[1], "nome": e[2]["nome"], "loja": e[2]["loja_nome"],
             "bairro": e[2]["bairro"], "codigo": e[2]["codigo"], "min": e[2]["total_min"]} for e in ev[:14]]
    kpis = {
        "pedidos": n, "faturamento": round(fat, 2), "ticket": round(fat / n, 2) if n else 0,
        "tempo_entrega": round(sum(p["total_min"] for p in ent) / len(ent)) if ent else 0,
        "tempo_retirada": round(sum(p["total_min"] for p in ret) / len(ret)) if ret else 0,
        "pct_retirada": round(100 * len(ret) / n) if n else 0,
        "em_preparo": sum(1 for p in peds if p["status"] in ("fila", "preparo")),
        "em_rota": sum(1 for p in peds if p["status"] == "rota"),
        "aguardando": sum(1 for p in peds if p["status"] == "pronto"),
        "concluidos": sum(1 for p in peds if p["status"] in ("entregue", "retirado")),
    }
    return {"agora": agora, "escala": CFG["escala_tempo"], "ativos": ativos,
            "historico": [[p["lat"], p["lon"], p["modo"]] for p in peds],
            "kpis": kpis, "ranking": ranking, "feed": feed, "demo": ESTADO["demo"]}


# ---------------------------------------------------------------- modo demonstração
NOMES_DEMO = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabi", "Heitor", "Isabela", "João",
              "Karina", "Lucas", "Marina", "Nicolas", "Olívia", "Pedro", "Rafa", "Sofia", "Thiago", "Vitória"]


def loop_demo():
    while True:
        time.sleep(CFG["demo_intervalo_seg"])
        if not ESTADO["demo"]:
            continue
        kits = [c["id"] for c in CFG["catalogo"] if c["grupo"] == "Kits"]
        outros = [c["id"] for c in CFG["catalogo"] if c["grupo"] != "Kits"]
        itens = {random.choice(kits): 1}
        for i in random.sample(outros, random.randint(0, 3)):
            itens[i] = random.randint(1, 2)
        b = random.randrange(len(FAIXAS_CEP))
        try:
            criar_pedido(random.choice(NOMES_DEMO) + " (demo)", itens, "", str(random.randint(1, 3000)), b,
                         random.choice(["entrega", "entrega", "retirada"]), demo=True,
                         aluno=random.choice([1, 1, 0]), mora=FAIXAS_CEP[random.randrange(len(FAIXAS_CEP))][2].split(" / ")[0],
                         usaria=random.choice([1, 1, 1, 0]))
        except Exception as e:
            print("demo:", e)


# ---------------------------------------------------------------- rede
def ip_local():
    if CFG.get("ip_manual"):
        return CFG["ip_manual"]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def todos_ips():
    ips = set()
    try:
        for i in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not i.startswith("127."):
                ips.add(i)
    except OSError:
        pass
    ips.add(ip_local())
    return sorted(ips)


# ---------------------------------------------------------------- HTTP
PAGINAS = {"/": "app.html", "/app": "app.html", "/telao": "telao.html", "/qr": "qr.html", "/checkins": "checkins.html"}
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if p in PAGINAS:
            p = "/web/" + PAGINAS[p]
        if p.startswith("/web/"):
            nome = os.path.basename(p)
            arq = os.path.join(WEB, nome)
            if os.path.isfile(arq):
                with open(arq, "rb") as f:
                    return self._send(200, f.read(), MIME.get(os.path.splitext(nome)[1], "application/octet-stream"))
            return self._send(404, {"erro": "arquivo não encontrado", "procurado_em": arq,
                                    "dica": "a pasta web (app.html, telao.html, qr.html, mapa.js, qrcode.js) precisa estar ao lado do server.py"})
        if p == "/api/config":
            porta = CFG["porta"]
            host = self.headers.get("Host", "localhost")
            h = host.split(":")[0]
            eh_ip = h.replace(".", "").isdigit() or h == "localhost"
            if os.environ.get("PORT") or not eh_ip:  # nuvem/túnel: usa o endereço público de quem acessou
                proto = self.headers.get("X-Forwarded-Proto", "https")
                pub = os.environ.get("PUBLIC_URL") or f"{proto}://{host}/"
                url_app, ips = pub, [pub]
            else:
                url_app, ips = f"http://{ip_local()}:{porta}/", [f"http://{i}:{porta}/" for i in todos_ips()]
            return self._send(200, {
                "nome": CFG["nome"], "rede_wifi": CFG.get("rede_wifi", ""), "escala": CFG["escala_tempo"], "lojas": CFG["lojas"],
                "tipos_loja": CFG["tipos_loja"], "catalogo": CFG["catalogo"], "bairros": BAIRROS_ORD,
                "desconto_retirada_pct": CFG["desconto_retirada_pct"], "frete_gratis_acima": CFG["frete_gratis_acima"],
                "url_app": url_app, "ips": ips})
        if p == "/api/estado":
            return self._send(200, estado())
        if p == "/api/checkins":
            with LOCK:
                rows = DB.execute("SELECT * FROM pedidos ORDER BY id DESC").fetchall()
            agora = time.time()
            return self._send(200, {"agora": agora, "checkins": [row_pub(r, agora) for r in rows]})
        if p == "/api/checkins.csv":
            with LOCK:
                rows = DB.execute("SELECT * FROM pedidos ORDER BY id").fetchall()
            sn = lambda v: "" if v is None else ("Sim" if v else "Não")
            linhas = ["Data/Hora;Código;Nome;Aluno;Onde mora;Bairro do pedido;Ponto de check-in;Tipo do ponto;Modo;Itens;Valor;Tempo prometido (min);Usaria o app;Pedido automático"]
            for r in rows:
                l = LOJAS[r["loja_id"]]
                itens = "; ".join(f"{q}x {CAT[i]['nome']}" for i, q in json.loads(r["itens"]).items())
                dt = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(r["t_criado"]))
                campos = [dt, r["codigo"], r["nome"], sn(r["aluno"]), r["mora"] or "", r["bairro"], l["nome"],
                          CFG["tipos_loja"][l["tipo"]]["nome"], "Entrega" if r["modo"] == "entrega" else "Retirada",
                          itens, f"{r['total']:.2f}".replace(".", ","), str(int(r["total_min"])), sn(r["usaria"]),
                          "Sim" if r["demo"] else "Não"]
                linhas.append(";".join(str(c).replace(";", ",") for c in campos))
            corpo = "\ufeff" + "\r\n".join(linhas)
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="checkins_ze_express.csv"')
            self.send_header("Cache-Control", "no-store")
            corpo = corpo.encode("utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            return self.wfile.write(corpo)
        if p == "/api/pedido":
            try:
                pid = int(parse_qs(u.query).get("id", ["0"])[0])
            except ValueError:
                pid = 0
            with LOCK:
                ped = pedido_pub(pid)
            return self._send(200 if ped else 404, {"ok": bool(ped), "pedido": ped, "agora": time.time()})
        return self._send(404, {"erro": "rota inexistente"})

    def do_POST(self):
        p = urlparse(self.path).path
        d = self._json()
        if p == "/api/cotacao":
            itens = limpar_itens(d.get("itens"))
            local = localizar(d.get("cep"), d.get("numero"), d.get("bairro_idx"))
            if not local:
                return self._send(200, {"ok": False, "erro": "fora", "bairros": BAIRROS_ORD})
            if not itens:
                return self._send(200, {"ok": False, "erro": "Escolha pelo menos um item."})
            with LOCK:
                q = cotar(itens, local, time.time())
            if not q:
                return self._send(200, {"ok": False, "erro": "Nenhum ponto atende essa combinação de itens."})
            q.pop("_ret"); q.pop("_ent")
            return self._send(200, dict(ok=True, local=local, **q))
        if p == "/api/pedido":
            return self._send(200, criar_pedido(d.get("nome"), d.get("itens"), d.get("cep"), d.get("numero"),
                                                d.get("bairro_idx"), d.get("modo"), aluno=d.get("aluno"),
                                                mora=d.get("mora"), usaria=d.get("usaria")))
        if p == "/api/retirar":
            with LOCK:
                DB.execute("UPDATE pedidos SET t_retirado=? WHERE id=? AND modo='retirada' AND t_retirado IS NULL "
                           "AND t_prep_fim<=?", (time.time(), int(d.get("id") or 0), time.time()))
                DB.commit()
                ped = pedido_pub(int(d.get("id") or 0))
            return self._send(200, {"ok": True, "pedido": ped})
        if p == "/api/reset":
            with LOCK:
                DB.execute("DELETE FROM pedidos")
                DB.execute("DELETE FROM sqlite_sequence WHERE name='pedidos'")
                DB.commit()
            return self._send(200, {"ok": True})
        if p == "/api/demo":
            ESTADO["demo"] = bool(d.get("ativo"))
            return self._send(200, {"ok": True, "demo": ESTADO["demo"]})
        return self._send(404, {"erro": "rota inexistente"})


class Servidor(ThreadingHTTPServer):
    # No Windows, allow_reuse_address=True deixaria dois servidores abrirem a mesma porta
    # e o antigo continuaria respondendo. Com False, a porta ocupada gera erro claro.
    allow_reuse_address = os.name != "nt"


def porta_ocupada(porta):
    try:
        with socket.create_connection(("127.0.0.1", porta), timeout=0.5):
            return True
    except OSError:
        return False


def main():
    porta = int(os.environ.get("PORT", CFG["porta"]))
    if porta_ocupada(porta):
        print(f"  A porta {porta} ja esta em uso: existe outra janela do servidor aberta.")
        print("  Feche a outra janela preta e rode INICIAR.bat de novo.")
        try:
            input("  Pressione Enter para sair.")
        except EOFError:
            pass
        return
    threading.Thread(target=loop_demo, daemon=True).start()
    try:
        srv = Servidor(("0.0.0.0", porta), H)
    except OSError as e:
        print(f"  Nao consegui abrir a porta {porta}: {e}")
        print("  Feche a outra janela preta do servidor e rode INICIAR.bat de novo.")
        try:
            input("  Pressione Enter para sair.")
        except EOFError:
            pass
        return
    print("=" * 62)
    print(f"  {CFG['nome']} - servidor ativo na porta {porta}")
    faltam = [a for a in ("app.html", "telao.html", "qr.html", "mapa.js", "qrcode.js") if not os.path.isfile(os.path.join(WEB, a))]
    if faltam:
        print(f"  ATENCAO: nao encontrei {', '.join(faltam)} em {WEB}")
        print("  Extraia o zip completo: a pasta web precisa ficar ao lado do server.py")
    else:
        print(f"  Telas ........ {WEB}")
    print(f"  Telão ........ http://localhost:{porta}/telao")
    print(f"  QR Code ...... http://localhost:{porta}/qr")
    print(f"  Check-ins .... http://localhost:{porta}/checkins")
    for i in todos_ips():
        print(f"  App celular .. http://{i}:{porta}/")
    print("  Feche esta janela para desligar.")
    print("=" * 62)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
