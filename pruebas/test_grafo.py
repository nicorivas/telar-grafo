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
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.entorno = {"TELAR_RAIZ": str(self.repo),
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
        self.assertEqual(sorted(n["ruta"] for n in d["nodos"]), ["idea.md", "otra.md"])
        self.assertEqual(len(d["aristas"]), 1)

    def test_como_orden_en_la_terminal(self):
        r = correr("vecinos", "idea.md", cwd=self.repo, entorno=self.entorno)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("`informa` otra.md", r.stdout)

    def test_lo_que_no_existe(self):
        r = correr("vecinos", entrada=json.dumps({"ruta": "nada.md"}), entorno={**self.entorno, "TELAR_CONSULTA": "1"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no existe", r.stderr)


if __name__ == "__main__":
    unittest.main()
