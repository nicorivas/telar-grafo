# Changelog

## Unreleased

- Each document in the graph is a telar object, `doc:<path>` (`[objetos.doc]`): `telar objeto doc:docs/x.md`
  shows it with its connections, and `telar objeto doc --listar` lists them all. With a telar whose search takes
  the objects of a module that lists, the documents are one more source of `telar buscar` and of the page's
  «todo» view, and a click opens the viewer.
- `nodos`, also a query: every document of every repository in telar's `[repos]`, once each (a document of a
  nested repository goes with the deepest one), with title, lede, path and how many connections; the most
  connected first.
- `vecinos` also answers with the fields of an object (title, how many connections, lede, path, links to its
  file and its neighbours), takes `id` as well as `ruta`, and a document that does not exist answers 404 as a
  query.
- A document reached through a symbolic link (a root of the graph that links to another folder) finds its
  connections in `vecinos`, `cerca` and `resumen`.
- `buscar`, `cerca` and `resumen`, also as queries: find a way in by title or summary, walk two steps
  around a document, go up or down a level of detail.
- A cache of each repository's graph, valid while its commit and its uncommitted `.md` files stay the same.
- `[contexto]`: every telar agent is told the graph is there and how to explore it.
- The reader and the core are those of commit ef1ea0c: relation types without accents (`continua`, `analogo-a`),
  and files that get no `## Referido por` (`no_escribir`, `detectar_generados` in `.grafo.toml`). Queries
  are unchanged.

## 0.1.0 — 2026-10-21

- First version: `vecinos`, `todo` (both also queries) and `revisar`, over the reader of Open Brinca's graph
  method (commit 6fa867d of its `metodo-grafo` branch).
