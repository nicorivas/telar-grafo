# telar-grafo

Un módulo de [telar](https://github.com/nicorivas/telar): el grafo de conocimiento de tus repositorios.
Cada documento puede declarar sus conexiones con otros en una sección `## Conexiones`, una por línea:

```
- `tipo` [Título del destino](ruta/relativa.md) · §X · por qué se relaciona
```

Con el módulo, telar las muestra y las recorre: desde la terminal, desde la página (el visor de
documentos) y desde otra máquina por el bus.

## Instalarlo

```
telar modulos instalar https://github.com/…/telar-grafo
```

## Usarlo

```
telar grafo vecinos docs/una-idea.md    # lo que sale de ese documento y lo que le llega
telar grafo todo                        # el grafo entero del repositorio donde estás, en JSON
telar grafo revisar                     # aristas rotas y tipos sin declarar; no escribe
```

`vecinos` y `todo` también son consultas: la página las pide con `GET /api/modulos/grafo/vecinos?ruta=…`
(y `&maquina=…` para el grafo de otra máquina).

## El grafo de cada repositorio

El lector es `nucleo/grafo.py`, el del método del grafo de Open Brinca, con su núcleo (`nucleo/nucleo.md`:
la sintaxis y el vocabulario base). Cada repositorio dice cómo es el suyo en un `.grafo.toml` en su raíz:

```toml
nucleo  = "metodo/grafo/nucleo.md"   # por defecto, el de este módulo
locales = ["grafo.local.md"]         # las palabras propias del repositorio
raices  = ["docs"]                   # por defecto, todo el repositorio
excluir = ["borradores"]
```

Un documento es del repositorio más hondo de `[repos]` de telar que lo contiene; si no, del repositorio
git donde está.
