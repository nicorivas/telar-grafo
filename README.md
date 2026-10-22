# telar-grafo

The knowledge graph of your repositories, as a module of [telar](https://github.com/nicorivas/telar).

A repository of notes, ideas or documentation gets easier to explore when its documents say how they
relate to each other. Here each document declares its connections in a `## Conexiones` section, one per
line, with a type and the reason:

```
- `informa` [Otra idea](ideas/otra.md) · §2 · why this one relates to that one
```

The connection is written once, on the side it comes from. With this module, telar reads those lines
and lets you walk them: what goes out of a document and what comes into it, from the terminal, from
the document viewer of telar's page (a panel next to the file, each connection a link), and from your
other machines over telar's bus.

## Install

You need a telar with modules that bring commands and queries (its `main` after 0.2.0, or the next release)
and Python 3.11+. Nothing else.

```sh
telar modulos instalar https://github.com/nicorivas/telar-grafo
```

telar clones it, shows what it brings and asks before installing. Install it on every machine whose
repositories you want to read: the page asks the machine where the document lives.

```sh
telar modulos actualizar grafo    # pull the latest
telar modulos quitar grafo
```

## Use

```sh
telar grafo vecinos docs/una-idea.md    # what goes out of that document and what comes into it
telar grafo todo                        # the whole graph of the repository you are in, as JSON
telar grafo revisar                     # broken links and undeclared types; writes nothing
```

`vecinos` and `todo` are also queries, which is how telar's page uses them:

```
GET /api/modulos/grafo/vecinos?ruta=docs/una-idea.md[&maquina=server]
```

The answer is `{nodo, salientes, entrantes, repo}`. Each connection is `{origen, tipo, destino,
titulo_destino, locus, porque, estado}` (`estado`: `ok`, `roto` when the target does not exist,
`externo` when it leaves the repository), with `origen_abs` and `destino_abs` to open it, and
`titulo_origen` on the ones that come in.

## Your repository's graph

A document belongs to the deepest of telar's `[repos]` that contains it, or else to the git repository
it is in. How that repository's graph is shaped goes in a `.grafo.toml` at its root:

```toml
nucleo  = "metodo/grafo/nucleo.md"   # the core vocabulary; by default, the one in this module
locales = ["grafo.local.md"]         # the repository's own relation types
raices  = ["docs"]                   # folders to walk; by default, the whole repository
excluir = ["borradores"]             # folder names or paths to skip
```

Without one, the whole repository is read with the core vocabulary.

## How it is made

- `modulo.toml` is what telar reads: the module's commands, and which of them are queries.
- `bin/grafo` is the module: it finds the repository of each document and calls the reader.
- `nucleo/` is the reader and the core of the graph method of Open Brinca (`grafo.py`, `nucleo.md`):
  the syntax of a connection, the base relation types, and the script that reads them, validates them and
  derives each document's `## Referido por` block. It is copied as it is, never edited here
  (`nucleo/DE-DONDE.md` says from which commit).

To work on it, install it from your clone without copying it:

```sh
telar modulos instalar --enlazar ~/code/telar-grafo
python3 -m unittest discover -s pruebas
```

## License

MIT. The files in `nucleo/` keep their own notice (MIT, © 2026 Brinca).
