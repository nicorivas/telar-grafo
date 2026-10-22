#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Brinca
"""grafo.py — la maquinaria del grafo de conocimiento de Brinca.

Hace tres cosas sobre las mismas aristas, y por eso viven juntas:
  1. REGENERA los bloques `## Referido por` (el espejo de cada arista, derivado).
  2. VALIDA que cada arista apunte a un archivo que existe dentro del repositorio.
  3. VALIDA que cada `tipo` esté declarado en el núcleo o en un diccionario local, y que
     cada palabra local aterrice con `más-general` en una declarada.

Principio: una arista se escribe UNA vez, del lado del origen, en `## Conexiones` (con su
«por qué»). Este script deriva el espejo: en cada nodo de destino escribe un `## Referido por`
con solo tipo + link, sin el «por qué», que vive en el origen. Así un lector ve su vecindario
sin grep y sin duplicar significado. La sintaxis y el vocabulario están en `nucleo.md`, al
lado de este archivo.

Configuración opcional en `.grafo.toml`, en la raíz del repositorio:

  nucleo  = "metodo/grafo/nucleo.md"     # por defecto, el nucleo.md junto a este script
  locales = ["grafo.local.md"]           # diccionarios con las palabras propias del repo
  raices  = ["eventos", "webinars"]      # por defecto, todo el repositorio
  excluir = ["borradores", "eventos/x"]  # nombres de carpeta o rutas que no se recorren
  no_escribir = ["informe/generado.md"]  # archivos que escribe otro programa: no reciben espejo
  detectar_generados = true              # también los que lo declaran en sus primeras líneas

Uso:
  python3 metodo/grafo/grafo.py                       # aplica los cambios
  python3 metodo/grafo/grafo.py --check               # no escribe; reporta deriva y errores (exit 1)
  python3 metodo/grafo/grafo.py --json                # el grafo entero en JSON; no escribe
  python3 metodo/grafo/grafo.py vecinos RUTA [--json] # lo que sale de un documento y lo que le llega

El JSON trae los nodos que participan en alguna arista ({ruta, titulo, lede}), las aristas
({origen, tipo, destino, titulo_destino, locus, porque, estado}) y el vocabulario declarado
({tipo: {glosa, fuente}}). Las rutas son relativas a la raíz del repositorio. `estado` es `ok`,
`roto` (el destino no existe) o `externo` (sale del repositorio).
"""
import argparse, json, os, re, subprocess, sys
import tomllib
from urllib.parse import unquote

AQUI = os.path.dirname(os.path.abspath(__file__))
SKIP = {"node_modules", ".next", ".venv", "venv", "__pycache__", ".git", "dist", "build",
        "out", "_archive", "_site", ".vercel"}
# La ruta admite un nivel de paréntesis: una carpeta llamada «taller (en pausa)» cortaba el
# link en el primer `)` y la arista salía como rota sin estarlo.
EDGE = re.compile(r"^- `([^`]+)` \[([^\]]+)\]\(((?:[^()]|\([^()]*\))+)\)")
# Una entrada del diccionario es un encabezado que empieza por un codespan: `#### `tipo``.
# Puede declarar dos tipos a la vez: `profundiza` ⇄ `comprime`.
ENTRADA = re.compile(r"^#{2,4}\s+(`.+)$", re.M)
GEN_MARK = ("<!-- AUTO-GENERADO por {script} · no editar a mano · "
            "el «por qué» vive en el origen (## Conexiones) -->")
# Reconoce también la marca de versiones anteriores del script (otra ruta, otro nombre),
# para que un repositorio que migra no se quede con espejos huérfanos.
GEN_RE = re.compile(r"<!-- AUTO-GENERADO por \S*grafo[\w.-]*\.py ")
# Un archivo que produce otro programa se reescribe entero desde su fuente: un bloque que le
# escribamos se pierde en la próxima corrida de SU generador, y quedaríamos reportando deriva
# para siempre. Con `detectar_generados = true`, un archivo que lo declara en sus primeras
# líneas no recibe espejo; `no_escribir` los nombra uno por uno.
GENERADO = re.compile(r"no editar a mano|generado desde|auto-?generado", re.I)


def raiz_repo():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def leer_config(repo, args):
    cfg = {}
    ruta = os.path.join(repo, ".grafo.toml")
    if os.path.isfile(ruta):
        with open(ruta, "rb") as f:
            cfg = tomllib.load(f)
    nucleo = args.nucleo or cfg.get("nucleo")
    nucleo = os.path.join(repo, nucleo) if nucleo else os.path.join(AQUI, "nucleo.md")
    locales = args.local or cfg.get("locales", [])
    raices = args.raices or cfg.get("raices", [])
    excluir = set(cfg.get("excluir", [])) | set(args.excluir or [])
    return {
        "detectar_generados": bool(cfg.get("detectar_generados", False)),
        # La copia del núcleo tampoco recibe espejo: tiene que seguir idéntica a la original.
        "no_escribir": {os.path.normpath(os.path.join(repo, p)) for p in cfg.get("no_escribir", [])}
                       | {os.path.normpath(nucleo)},
        "repo": repo,
        "nucleo": nucleo,
        "locales": [os.path.join(repo, p) for p in locales],
        "raices": [os.path.normpath(os.path.join(repo, r)) for r in raices] or [repo],
        "excluir_nombres": SKIP | {e for e in excluir if "/" not in e},
        "excluir_rutas": {os.path.normpath(os.path.join(repo, e)) for e in excluir if "/" in e},
    }


def entradas(path):
    """{tipo: texto de su entrada} de un diccionario; None si el archivo no existe."""
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        return None
    txt = re.sub(r"^```.*?^```", "", txt, flags=re.M | re.S)   # un ejemplo dentro de un bloque de código no declara nada
    out, marcas = {}, list(ENTRADA.finditer(txt))
    for i, m in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(txt)
        sig = re.search(r"^#{1,4}\s", txt[m.end():fin], re.M)   # la entrada termina en el próximo encabezado
        cuerpo = txt[m.end(): m.end() + sig.start()] if sig else txt[m.end():fin]
        for tipo in re.findall(r"`([^`]+)`", m.group(1)):
            out[tipo] = cuerpo
    return out


def vocabulario(cfg):
    """Los tipos declarados y los errores del propio vocabulario.

    El vocabulario es infinito pero **anclado**: cualquier palabra vale si tiene entrada con
    `más-general` hacia una palabra declarada. Sin algo que lo compruebe, esa regla se pudre
    sola: en un repositorio de Brinca, un tercio de las aristas llegó a usar tipos sin declarar.
    """
    rel = lambda p: os.path.relpath(p, cfg["repo"])
    nucleo = entradas(cfg["nucleo"])
    if nucleo is None:
        return None, [f"no encontré el núcleo: {rel(cfg['nucleo'])}"]
    declarados, errores, locales = set(nucleo), [], {}
    for abs_path in cfg["locales"]:
        path = rel(abs_path)
        loc = entradas(abs_path)
        if loc is None:
            errores.append(f"no encontré el diccionario local: {path}")
            continue
        for tipo, cuerpo in loc.items():
            if tipo in nucleo:
                errores.append(f"`{tipo}` ya está en el núcleo; un diccionario local no lo redefine ({path})")
                continue
            locales[tipo] = (cuerpo, path)
    declarados |= set(locales)
    for tipo, (cuerpo, path) in locales.items():
        m = re.search(r"más-general:?\s*`([^`]+)`", cuerpo)
        if not m:
            errores.append(f"`{tipo}` no dice con `más-general` en qué palabra declarada aterriza ({path})")
        elif m.group(1) not in declarados:
            errores.append(f"`{tipo}` aterriza en `{m.group(1)}`, que no está declarada ({path})")
    return declarados, errores


def excluido(path, cfg):
    ap = os.path.normpath(path)
    return any(ap == r or ap.startswith(r + os.sep) for r in cfg["excluir_rutas"])


def md_files(cfg):
    for base in cfg["raices"]:
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if d not in cfg["excluir_nombres"] and not d.startswith(".")
                      and not excluido(os.path.join(dp, d), cfg)]
            for fn in fns:
                if fn.endswith(".md"):
                    yield os.path.join(dp, fn)


def in_scope(path, cfg):
    ap = os.path.abspath(path)
    return (any(ap.startswith(r + os.sep) for r in cfg["raices"]) and not excluido(ap, cfg))


def title(path):
    """Título legible del nodo: frontmatter `titulo` o `title`, su H1, o el nombre del archivo."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return os.path.splitext(os.path.basename(path))[0]
    if lines and lines[0].strip() == "---":
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            m = re.match(r"\s*(?:titulo|title):\s*(.+)", ln)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    for ln in lines:
        if ln.startswith("# "):
            return re.sub(r"[*`\\]", "", ln[2:]).strip()
    return os.path.splitext(os.path.basename(path))[0]


def es_generado(path, content, cfg):
    """¿Lo escribe otro programa? Por lista (`no_escribir`) o porque lo declara en su cabecera."""
    if os.path.normpath(path) in cfg["no_escribir"]:
        return True
    if not cfg["detectar_generados"]:
        return False
    for line in content.splitlines()[:20]:
        if GEN_RE.search(line):              # nuestra propia marca no cuenta
            continue
        if GENERADO.search(line):
            return True
    return False


def lede(path):
    """El resumen del nodo: la primera línea `>` bajo el H1 o, si no hay, su primer párrafo."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        return ""
    txt = re.sub(r"\A---\n.*?\n---\n", "", txt, flags=re.S)
    m = re.search(r"^# .*\n", txt, re.M)
    cuerpo = txt[m.end():] if m else txt
    for parrafo in re.split(r"\n\s*\n", cuerpo):
        p = parrafo.strip()
        if not p or p.startswith(("#", "|", "```", "<!--", "![")):
            continue
        p = re.sub(r"^>\s?", "", p, flags=re.M)
        return " ".join(p.split())[:600]
    return ""


def partes_arista(resto):
    """(locus, porque) del texto que sigue al enlace: ` · §X · por qué` o ` · por qué`."""
    partes = [p.strip() for p in resto.split(" · ")]
    partes = [p for p in partes if p] if partes and partes[0] in ("", "·") else partes
    if partes and partes[0].startswith("·"):
        partes[0] = partes[0].lstrip("· ").strip()
    if len(partes) >= 2 and (partes[0].startswith(("§", "[")) or len(partes[0]) <= 30):
        return partes[0], " · ".join(partes[1:])
    return "", " · ".join(partes)


def conexiones_edges(text, detalle=False):
    """(tipo, ruta) de cada arista DENTRO del bloque `## Conexiones`.

    Con `detalle`, (tipo, título, ruta, locus, porque).
    """
    edges, in_sec, in_fence = [], False, False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence            # no parsear ejemplos dentro de code fences
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            in_sec = line.strip() == "## Conexiones"
            continue
        if in_sec:
            m = EDGE.match(line)
            if m and detalle:
                edges.append((m.group(1), m.group(2), m.group(3)) + partes_arista(line[m.end():]))
            elif m:
                edges.append((m.group(1), m.group(3)))
    return edges


def bloque_referidos(content):
    """(inicio, fin) del bloque `## Referido por` que empieza en una línea propia, o None."""
    marker = "## Referido por"
    pos = content.find(marker)
    while pos != -1 and pos != 0 and content[pos - 1] != "\n":
        pos = content.find(marker, pos + 1)
    if pos == -1:
        return None
    nxt = re.search(r"\n## ", content[pos + len(marker):])
    fin = pos + len(marker) + nxt.start() + 1 if nxt else len(content)
    return pos, fin


def upsert(content, block):
    """Reemplaza un `## Referido por` existente (de encabezado a encabezado) o lo añade al final."""
    span = bloque_referidos(content)
    if span is None:
        return content.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
    before, after = content[:span[0]].rstrip("\n"), content[span[1]:]
    if after:
        return before + "\n\n" + block.rstrip("\n") + "\n\n" + after
    return before + "\n\n" + block.rstrip("\n") + "\n"


def strip_referidos(content):
    """Quita un bloque `## Referido por` generado (de encabezado a encabezado o al final)."""
    span = bloque_referidos(content)
    if span is None or not GEN_RE.search(content[span[0]:span[1]]):
        return content
    before, after = content[:span[0]].rstrip("\n"), content[span[1]:]
    return before + "\n\n" + after if after else before + "\n"


def glosas(cfg):
    """{tipo: {glosa, fuente}} del núcleo y de los diccionarios locales."""
    out = {}
    for path in [cfg["nucleo"]] + cfg["locales"]:
        for tipo, cuerpo in (entradas(path) or {}).items():
            if tipo in out:
                continue                 # el núcleo manda: un local no lo redefine
            m = re.search(r"^Glosa:\s*(.+)$", cuerpo, re.M)
            out[tipo] = {"glosa": m.group(1).strip() if m else "",
                         "fuente": os.path.relpath(path, cfg["repo"])}
    return out


def salida_consulta(args, cfg, repo, aristas):
    """Imprime el grafo (--json) o el vecindario de un documento (vecinos). Nunca escribe."""
    def nodo(ruta):
        ap = os.path.join(repo, ruta)
        return {"ruta": ruta, "titulo": title(ap), "lede": lede(ap)}

    if args.accion == "vecinos":
        ruta = args.ruta if os.path.exists(args.ruta) else os.path.join(repo, args.ruta)
        ruta = os.path.relpath(os.path.abspath(ruta), repo)
        if not os.path.isfile(os.path.join(repo, ruta)):
            print(f"no existe: {ruta}", file=sys.stderr)
            return 2
        salen = [a for a in aristas if a["origen"] == ruta]
        llegan = [a for a in aristas if a["destino"] == ruta and a["estado"] == "ok"]
        if args.json:
            print(json.dumps({"nodo": nodo(ruta), "salientes": salen, "entrantes": llegan},
                             ensure_ascii=False, indent=2))
            return 0
        print(f"{title(os.path.join(repo, ruta))} · {ruta}")
        for a in salen:
            locus = f" · {a['locus']}" if a["locus"] else ""
            print(f"  → `{a['tipo']}` {a['destino']}{locus} · {a['porque']}")
        for a in llegan:
            locus = f" · {a['locus']}" if a["locus"] else ""
            print(f"  ← `{a['tipo']}` {a['origen']}{locus} · {a['porque']}")
        if not salen and not llegan:
            print("  sin aristas")
        return 0

    rutas = sorted({a["origen"] for a in aristas} |
                   {a["destino"] for a in aristas if a["estado"] == "ok"
                    and os.path.isfile(os.path.join(repo, a["destino"]))})
    print(json.dumps({"repo": os.path.basename(repo),
                      "nucleo": os.path.relpath(cfg["nucleo"], repo),
                      "locales": [os.path.relpath(p, repo) for p in cfg["locales"]],
                      "nodos": [nodo(r) for r in rutas], "aristas": aristas,
                      "vocabulario": glosas(cfg)}, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Regenera `## Referido por` y valida el grafo.")
    ap.add_argument("--check", action="store_true",
                    help="no escribe; reporta deriva, links rotos y tipos sin declarar (exit 1)")
    ap.add_argument("--repo", help="raíz del repositorio (por defecto, la de git)")
    ap.add_argument("--nucleo", help="ruta del núcleo, relativa al repositorio")
    ap.add_argument("--local", action="append", help="diccionario local (se puede repetir)")
    ap.add_argument("--raices", nargs="+", help="carpetas que se recorren")
    ap.add_argument("--excluir", nargs="+", help="nombres de carpeta o rutas que no se recorren")
    ap.add_argument("--json", action="store_true", help="imprime el grafo en JSON; no escribe")
    ap.add_argument("accion", nargs="?", choices=["vecinos"],
                    help="vecinos RUTA: lo que sale de un documento y lo que le llega; no escribe")
    ap.add_argument("ruta", nargs="?", help="el documento, para `vecinos`")
    args = ap.parse_args()
    if args.accion and not args.ruta:
        ap.error("vecinos necesita la ruta de un documento")

    repo = os.path.abspath(args.repo) if args.repo else raiz_repo()
    cfg = leer_config(repo, args)

    rev, dangling, usados = {}, [], {}   # rev: target_abs -> {source_abs -> set(tipos)}
    aristas = []                         # cada arista con su detalle, para --json y vecinos
    declarados, errores_vocab = vocabulario(cfg)
    for src in md_files(cfg):
        with open(src, encoding="utf-8", errors="replace") as f:
            text = f.read()
        for tipo, titulo_dest, rel, locus, porque in conexiones_edges(text, detalle=True):
            rel = rel.split("#")[0].strip()
            if not rel or rel.startswith(("http://", "https://", "mailto:")):
                continue
            arista = {"origen": os.path.relpath(src, repo), "tipo": tipo, "destino": rel,
                      "titulo_destino": titulo_dest, "locus": locus, "porque": porque,
                      "estado": "ok"}
            aristas.append(arista)
            # El tipo se comprueba aunque el link esté roto: son dos deudas distintas.
            usados.setdefault(tipo, []).append(src)
            # Un link escrito con %20 o %28 es válido en markdown; sin decodificar, toda ruta
            # con espacios o paréntesis se reportaba rota.
            tgt = os.path.normpath(os.path.join(os.path.dirname(src), unquote(rel)))
            # Un link que sale del repositorio resuelve solo en la máquina de quien lo escribió:
            # se reporta aunque el archivo exista.
            if not tgt.startswith(repo + os.sep):
                arista["estado"] = "externo"
                dangling.append((src, tipo, rel + "  (sale del repositorio)"))
                continue
            arista["destino"] = os.path.relpath(tgt, repo)
            if os.path.isdir(tgt):
                if not os.path.isfile(os.path.join(tgt, "README.md")):
                    continue             # carpeta sin README: el link vale, no hay dónde espejarlo
                tgt = os.path.join(tgt, "README.md")
                arista["destino"] = os.path.relpath(tgt, repo)
            if not os.path.isfile(tgt):
                arista["estado"] = "roto"
                dangling.append((src, tipo, rel))
                continue
            rev.setdefault(tgt, {}).setdefault(src, set()).add(tipo)

    if args.json or args.accion:
        sys.exit(salida_consulta(args, cfg, repo, aristas))

    script = os.path.relpath(os.path.abspath(__file__), repo)
    marca = GEN_MARK.format(script=script if not script.startswith("..") else "grafo.py")
    changed, generados = [], []
    for tgt, sources in rev.items():
        # El espejo se escribe SOLO en markdown: pegarle un bloque a un .html o a un .json lo rompe.
        if not in_scope(tgt, cfg) or not tgt.endswith(".md"):
            continue
        with open(tgt, encoding="utf-8") as f:
            content = f.read()
        if es_generado(tgt, content, cfg):
            generados.append(tgt)
            continue
        rows = []
        for src in sorted(sources):
            tipos = ", ".join(f"`{t}`" for t in sorted(sources[src]))
            rel = os.path.relpath(src, os.path.dirname(tgt))
            rows.append(f"- {tipos} ← [{title(src)}]({rel})")
        block = f"## Referido por\n\n{marca}\n\n" + "\n".join(rows) + "\n"
        new = upsert(content, block)
        if new != content:
            changed.append(tgt)
            if not args.check:
                with open(tgt, "w", encoding="utf-8") as f:
                    f.write(new)

    targets = {os.path.normpath(t) for t in rev}            # limpieza de espejos huérfanos
    for f in md_files(cfg):
        if os.path.normpath(f) in targets:
            continue
        with open(f, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if GEN_RE.search(content) and not es_generado(f, content, cfg):
            new = strip_referidos(content)
            if new != content:
                changed.append(f)
                if not args.check:
                    with open(f, "w", encoding="utf-8") as fh:
                        fh.write(new)

    n_edges = sum(len(ts) for s in rev.values() for ts in s.values())
    verb = "a actualizar" if args.check else "actualizados"
    print(f"aristas: {n_edges} · nodos con backlinks: {len(rev)} · archivos {verb}: {len(changed)}")
    for c in changed:
        print(f"  ~ {os.path.relpath(c, repo)}")
    if generados:
        print(f"sin espejo (la copia del núcleo o archivos que escribe otro programa): {len(generados)}")
        for g in generados:
            print(f"  · {os.path.relpath(g, repo)}")
    if dangling:
        print(f"LINKS ROTOS ({len(dangling)}):")
        for src, tipo, rel in dangling:
            print(f"  ✗ {os.path.relpath(src, repo)}: `{tipo}` -> {rel}")
    if errores_vocab:
        print(f"VOCABULARIO ({len(errores_vocab)}):")
        for e in errores_vocab:
            print(f"  ! {e}")
    sin_declarar = {}
    if declarados is not None:
        sin_declarar = {t: v for t, v in usados.items() if t not in declarados}
    if sin_declarar:
        total = sum(len(v) for v in sin_declarar.values())
        print(f"TIPOS SIN DECLARAR ({len(sin_declarar)} tipos, {total} aristas) — dales entrada "
              f"en un diccionario local con `más-general`, o cámbialos por una palabra del núcleo:")
        for t, srcs in sorted(sin_declarar.items(), key=lambda kv: -len(kv[1])):
            ej = os.path.relpath(srcs[0], repo)
            print(f"  ? `{t}` · {len(srcs)} uso(s) · p.ej. {ej}")
    if args.check and (changed or dangling or sin_declarar or errores_vocab):
        sys.exit(1)


if __name__ == "__main__":
    main()
