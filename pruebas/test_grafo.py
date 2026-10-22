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


if __name__ == "__main__":
    unittest.main()
