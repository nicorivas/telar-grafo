"""bin/grafo con un repositorio de ejemplo: la orden, la consulta y el repositorio de cada documento."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GRAFO = Path(__file__).resolve().parent.parent / "bin" / "grafo"

IDEA = """# Una idea

> La idea en una línea.

## Conexiones

- `informa` [Otra idea](otra.md) · §2 · porque la sostiene
- `profundiza` [El mapa](mapa.md) · porque detalla una fila del mapa
"""

MAPA = """# El mapa

> Todas las ideas, en una tabla.
"""

OTRA = """# Otra idea

> La otra, también en una línea.
"""


def correr(*args, entrada=None, cwd=None, entorno=None):
    return subprocess.run([sys.executable, str(GRAFO), *args], input=entrada, capture_output=True, text=True,
                          cwd=cwd, env={**os.environ, **(entorno or {})})


class ElGrafo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve() / "ideas"
        self.repo.mkdir()
        (self.repo / "idea.md").write_text(IDEA)
        (self.repo / "otra.md").write_text(OTRA)
        (self.repo / "mapa.md").write_text(MAPA)
        self.cache = Path(self.tmp.name) / "cache"
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        for k, v in (("user.email", "t@t"), ("user.name", "t")):
            subprocess.run(["git", "-C", str(self.repo), "config", k, v], check=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "ideas"], check=True)
        self.entorno = {"TELAR_RAIZ": str(self.repo), "XDG_CACHE_HOME": str(self.cache),
                        "TELAR_REPOS": json.dumps([{"nombre": "ideas", "ruta": str(self.repo), "perfil": ""}])}

    def consultar(self, verbo, params):
        r = correr(verbo, entrada=json.dumps(params), entorno={**self.entorno, "TELAR_CONSULTA": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_vecinos_como_consulta(self):
        d = self.consultar("vecinos", {"ruta": "otra.md"})
        self.assertEqual(d["repo"], {"nombre": "ideas", "ruta": str(self.repo)})
        [a] = d["entrantes"]
        self.assertEqual((a["tipo"], a["origen"], a["titulo_origen"], a["locus"], a["porque"]),
                         ("informa", "idea.md", "Una idea", "§2", "porque la sostiene"))
        self.assertEqual(a["origen_abs"], str(self.repo / "idea.md"))
        self.assertEqual(self.consultar("vecinos", {"ruta": "idea.md"})["salientes"][0]["destino"], "otra.md")

    def test_todo_el_grafo(self):
        d = self.consultar("todo", {})
        self.assertEqual(sorted(n["ruta"] for n in d["nodos"]), ["idea.md", "mapa.md", "otra.md"])
        self.assertEqual(len(d["aristas"]), 2)

    def test_como_orden_en_la_terminal(self):
        r = correr("vecinos", "idea.md", cwd=self.repo, entorno=self.entorno)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("`informa` otra.md", r.stdout)

    def test_buscar_por_titulo_y_resumen(self):
        d = self.consultar("buscar", {"termino": "idea"})
        self.assertEqual([x["ruta"] for x in d["documentos"]][:2], ["idea.md", "otra.md"])
        self.assertEqual(d["documentos"][0]["conexiones"], 2)
        self.assertEqual(self.consultar("buscar", {"termino": "tabla"})["documentos"][0]["ruta"], "mapa.md")
        self.assertEqual(self.consultar("buscar", {"termino": "nada parecido"})["total"], 0)

    def test_cerca_a_dos_pasos(self):
        d = self.consultar("cerca", {"ruta": "otra.md"})
        por_ruta = {x["ruta"]: x for x in d["documentos"]}
        self.assertEqual((por_ruta["idea.md"]["distancia"], por_ruta["mapa.md"]["distancia"]), (1, 2))
        self.assertEqual(por_ruta["mapa.md"]["camino"], "←informa →profundiza")
        self.assertNotIn("mapa.md", {x["ruta"] for x in self.consultar("cerca", {"ruta": "otra.md", "saltos": 1})["documentos"]})

    def test_resumen_sube_y_baja(self):
        self.assertEqual([x["ruta"] for x in self.consultar("resumen", {"ruta": "idea.md"})["lo_resume"]], ["mapa.md"])
        self.assertEqual([x["ruta"] for x in self.consultar("resumen", {"ruta": "mapa.md"})["lo_detalla"]], ["idea.md"])

    def test_el_cache_se_renueva_cuando_cambia_un_documento(self):
        self.assertEqual(len(self.consultar("vecinos", {"ruta": "otra.md"})["entrantes"]), 1)
        self.assertTrue(any(self.cache.rglob("*.json")))
        (self.repo / "mapa.md").write_text(MAPA + "\n## Conexiones\n\n- `informa` [Otra](otra.md) · porque también\n")
        self.assertEqual(len(self.consultar("vecinos", {"ruta": "otra.md"})["entrantes"]), 2)

    def test_lo_que_no_existe(self):
        r = correr("vecinos", entrada=json.dumps({"ruta": "nada.md"}), entorno={**self.entorno, "TELAR_CONSULTA": "1"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no existe", r.stderr)
        # como consulta, un 404 que telar entiende (un objeto doc que ya no está)
        self.assertEqual(json.loads(r.stdout), {"error": "no existe: nada.md", "codigo": 404})

    def test_vecinos_es_el_ver_de_un_doc(self):
        d = self.consultar("vecinos", {"id": "idea.md"})
        self.assertEqual((d["titulo"], d["estado"], d["resumen"]), ("Una idea", "2 conexiones", "La idea en una línea."))
        self.assertEqual(d["campos"], {"ruta": "idea.md", "ruta_abs": str(self.repo / "idea.md"), "repo": "ideas",
                                       "conexiones": 2})
        self.assertEqual(d["enlaces"], ["archivo:idea.md", "doc:otra.md", "doc:mapa.md"], "su archivo y con qué se conecta")
        self.assertEqual(self.consultar("vecinos", {"id": "otra.md"})["estado"], "1 conexión")


class LosNodos(unittest.TestCase):
    """`nodos` (el `listar` del objeto doc): los documentos de todos los repositorios de telar, una vez cada uno."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = Path(self.tmp.name).resolve() / "casa"
        self.anidado = self.raiz / "taller"
        for repo, archivos in ((self.raiz, {"notas/idea.md": IDEA.replace("(otra.md)", "(../taller/otra.md)"),
                                            "notas/mapa.md": MAPA}),
                               (self.anidado, {"otra.md": OTRA + "\n## Conexiones\n\n- `informa` [Plan](plan.md) · porque sí\n",
                                               "plan.md": "# El plan\n\n> Lo que sigue.\n"})):
            for ruta, texto in archivos.items():
                (repo / ruta).parent.mkdir(parents=True, exist_ok=True)
                (repo / ruta).write_text(texto)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            for k, v in (("user.email", "t@t"), ("user.name", "t")):
                subprocess.run(["git", "-C", str(repo), "config", k, v], check=True)
        # el de afuera no recorre el anidado (como un repositorio que tiene otro adentro): lo trae solo como destino
        (self.raiz / ".grafo.toml").write_text('raices = ["notas"]\n')
        (self.raiz / ".gitignore").write_text("taller/\n")
        for repo in (self.anidado, self.raiz):
            subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "x"], check=True)
        self.repos = [{"nombre": "casa", "ruta": str(self.raiz), "perfil": ""},
                      {"nombre": "taller", "ruta": str(self.anidado), "perfil": ""}]
        self.cache = Path(self.tmp.name) / "cache"

    def nodos(self, repos=None, raiz=None):
        entorno = {"TELAR_RAIZ": str(raiz or self.raiz), "XDG_CACHE_HOME": str(self.cache), "TELAR_CONSULTA": "1",
                   "TELAR_REPOS": json.dumps(self.repos if repos is None else repos)}
        r = correr("nodos", entrada=json.dumps({"tipo": "doc"}), entorno=entorno)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_todos_una_vez_con_su_repositorio_mas_hondo(self):
        d = self.nodos()
        self.assertEqual(d["fallas"], [])
        por_id = {o["id"]: o for o in d["objetos"]}
        self.assertEqual(sorted(por_id), ["notas/idea.md", "notas/mapa.md", "taller/otra.md", "taller/plan.md"],
                         "otra.md sale en los dos grafos y va una vez; los id, desde la raíz de telar")
        otra = por_id["taller/otra.md"]
        self.assertEqual(otra["campos"], {"ruta": "otra.md", "ruta_abs": str(self.anidado / "otra.md"), "repo": "taller",
                                          "conexiones": 1}, "con el suyo, el más hondo: su ruta es la de ese repositorio")
        idea = por_id["notas/idea.md"]
        self.assertEqual((idea["titulo"], idea["resumen"], idea["estado"]), ("Una idea", "La idea en una línea.", "2 conexiones"))
        self.assertEqual(d["objetos"][0]["id"], "notas/idea.md", "los más conectados primero")

    def test_el_mismo_orden_da_lo_mismo_al_reves(self):
        self.assertEqual(self.nodos(), self.nodos(list(reversed(self.repos))), "el más hondo gana, en cualquier orden")

    def test_lo_que_no_se_pudo_leer_se_dice(self):
        d = self.nodos([*self.repos, {"nombre": "lejos", "ruta": str(self.raiz / "no-esta"), "perfil": ""}])
        self.assertEqual(len(d["objetos"]), 4)
        self.assertEqual(len(d["fallas"]), 1)
        self.assertIn("lejos", d["fallas"][0])

    def test_fuera_de_la_raiz_el_id_es_la_ruta_absoluta(self):
        ids = {o["id"] for o in self.nodos([self.repos[1]], raiz=self.raiz / "notas")["objetos"]}
        self.assertEqual(ids, {str(self.anidado / "otra.md"), str(self.anidado / "plan.md")})

    def test_por_un_enlace_simbolico(self):
        # una raíz del grafo que es un enlace a otra carpeta: el grafo nombra sus documentos por el enlace
        (self.raiz / "atajo").symlink_to(self.raiz / "notas")
        (self.raiz / ".grafo.toml").write_text('raices = ["atajo"]\n')
        d = self.nodos([self.repos[0]])
        self.assertIn("atajo/idea.md", {o["id"] for o in d["objetos"]})
        entorno = {"TELAR_RAIZ": str(self.raiz), "XDG_CACHE_HOME": str(self.cache), "TELAR_CONSULTA": "1",
                   "TELAR_REPOS": json.dumps([self.repos[0]])}
        r = correr("vecinos", entrada=json.dumps({"id": "atajo/idea.md"}), entorno=entorno)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(json.loads(r.stdout)["salientes"]), 2, "sus conexiones, aunque la carpeta real sea otra")

    def test_en_la_terminal(self):
        r = correr("nodos", cwd=self.raiz, entorno={"TELAR_RAIZ": str(self.raiz), "XDG_CACHE_HOME": str(self.cache),
                                                     "TELAR_REPOS": json.dumps(self.repos)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("4 documento(s) en el grafo", r.stdout)
        self.assertIn("notas/idea.md · Una idea · 2 conexiones", r.stdout)


if __name__ == "__main__":
    unittest.main()
