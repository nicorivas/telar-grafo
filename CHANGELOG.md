# Changelog

## Unreleased

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
