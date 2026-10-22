---
id: grafo-nucleo
tipo: metodo
version: "1.0"
actualizado: 2026-10-21
tags: [grafo, gestion-del-conocimiento]
---

# El grafo de conocimiento: sintaxis y vocabulario

> Cómo se escribe una relación entre dos documentos markdown para que personas y agentes de IA la recorran con `grep`, sin base de datos ni parser. Es el núcleo común del método de Brinca: un repositorio que lo adopta copia este archivo tal cual y declara sus palabras propias en un diccionario local.

Un enlace dice que dos documentos están relacionados. Una arista dice cómo: si uno confirma al otro, lo contradice en parte o corrige una cifra suya. Con eso un agente puede contestar «¿qué se dijo en contra de esta idea?» leyendo una línea por relación, sin interpretar prosa. Por eso una arista se escribe siempre igual: la consistencia ahorra razonamiento.

## Nodos

- Un nodo es un archivo `.md`. Su ID es su ruta relativa dentro del repositorio.
- El tipo de nodo se deduce de la carpeta donde vive. No se etiqueta.
- Una parte de un nodo se cita con `§X`: una sección, un párrafo o una marca de tiempo como `[13:39]`.

## Una arista, una línea

Las aristas de un documento van en su sección `## Conexiones`, una por línea:

```
- `tipo` [Título del destino](ruta/relativa.md) · §X · por qué se relacionan
```

- **`tipo`**, en codespan, es la relación y el ancla de `grep`. Una arista lleva un solo tipo. Los tipos se escriben en minúsculas, sin tildes y con guiones (`deriva-de`), para que sean fáciles de escribir y de buscar.
- **`[Título](ruta)`** es el destino: un enlace que se puede abrir y una ruta que se puede buscar. La ruta es relativa y nunca sale del repositorio, porque una ruta externa solo funciona en la máquina de quien la escribió.
- **`· §X`** es el lugar exacto dentro del destino. Es opcional.
- **`· por qué`** es obligatorio. El matiz va aquí y no en un tipo nuevo. Sin porqué, una arista es solo un enlace.
- La dirección es implícita: *este documento —tipo→ destino*.

Un ejemplo, escrito en la ficha del webinar de Wharton sobre el informe de adopción de IA 2026:

```
## Conexiones

- `sostiene` [Keynote «Against Productivity»](../../eventos/impacta-ia-2026/sesiones/dia1-05-keynote-against-productivity-reaping-rewards-ai-revolution/README.md) · [09:38] · el informe completo trae la cifra en que se apoya la tesis de la keynote: los departamentos que miden al menos un indicador de crecimiento reportan ROI fuerte casi tres veces más que los que solo miden eficiencia (35 % contra 13 %).
```

No es `confirma`: la keynote y el webinar son del mismo autor y del mismo estudio, así que no hay un testigo independiente. Elegir el tipo obliga a hacerse esa pregunta.

Cada arista se escribe una sola vez, del lado del origen. Lo que llega a un documento aparece en su sección `## Referido por`, con el tipo y el enlace pero sin el porqué. Esa sección la genera [`grafo.py`](grafo.py) y nadie la escribe a mano.

## Tres niveles de lectura

El par `profundiza` ⇄ `comprime` hace que el grafo se recorra por nivel de detalle:

| Nivel | Qué es | Se lee para |
|---|---|---|
| Índice | una línea por documento | saber qué hay |
| Resumen | la primera frase del documento | decidir si hace falta el detalle |
| Cuerpo | el documento entero | solo si el resumen dijo que hace falta |

Para gastar poco contexto, quédate en el documento que comprime; para el fondo, sigue `profundiza`.

## Vocabulario

Cada entrada tiene el mismo formato, de menos a más detalle:

- `Glosa:` la definición en una línea. `grep '^Glosa:'` entrega el vocabulario completo, comprimido.
- `Distingue:` en qué se diferencia de la palabra más cercana.
- `Meta:` cómo se relaciona con otras palabras del vocabulario.
- `Cuándo importa:` qué pregunta permite contestar. Solo en algunas.

### Estructura: cómo se arman las cosas

#### `contiene`
Glosa: el destino es parte del origen.
Distingue: no se escribe cuando la carpeta ya lo dice: una sesión guardada dentro de la carpeta de su evento no necesita la arista.
Meta: inverso-de `pertenece-a`.

#### `pertenece-a`
Glosa: el origen es parte del destino.
Meta: inverso-de `contiene`.

#### `deriva-de`
Glosa: el origen nació del destino y no existiría sin él.
Distingue: vs `usa` (usa toma algo prestado; deriva-de debe su existencia al destino) · vs `continua` (deriva-de es procedencia del contenido; `continua` es sucesión en el tiempo).
Meta: inverso-de `origina`.

#### `origina`
Glosa: el destino nació del origen. Se escribe cuando lo natural es mirar desde el documento que dio origen.
Meta: inverso-de `deriva-de`.

#### `usa`
Glosa: el origen se sirve del destino sin depender de él para existir.
Distingue: vs `depende-de` (depende-de cae si el destino cae) · vs `alimenta` (alimenta es la dirección contraria: el origen aporta al destino).
Meta: inverso-de `alimenta`.

#### `alimenta`
Glosa: el origen aporta contenido o insumos al destino, sin que el destino dependa de él para existir.
Meta: inverso-de `usa`.

#### `depende-de`
Glosa: sin el destino, el origen no funciona.
Distingue: vs `restringida-por` (depende-de habilita; restringida-por limita).

#### `restringida-por`
Glosa: el destino acota lo que el origen puede ser o hacer.
Distingue: vs `depende-de` (depende-de habilita; restringida-por limita).
Meta: inverso-de `restringe`.

#### `restringe`
Glosa: el origen acota lo que el destino puede ser o hacer. Es la mirada desde la norma: una ley restringe qué datos puede usar un modelo.
Distingue: vs `sostiene` (sostiene mantiene en pie al destino; restringe le pone un borde).
Meta: inverso-de `restringida-por`.
Cuándo importa: una norma sabe mejor que nadie a quién limita, así que la arista se escribe una vez, desde la norma. El `## Referido por` de cada documento limitado la muestra.

#### `mide`
Glosa: el origen es el instrumento con que se mide el destino. Produce un número comparable en el tiempo.
Distingue: vs `informa` (informa ilumina; mide produce un número) · vs `verifica` (verifica deja un veredicto una vez).

#### `continua`
Glosa: el origen es la siguiente entrega o el siguiente paso de algo que el destino abrió: una serie de webinars, un estudio anual, una cadena de trabajo.
Distingue: vs `deriva-de` (deriva-de es procedencia del contenido; `continua` es sucesión en el tiempo) · vs `sustituye-a` (la entrega anterior sigue siendo el registro válido de su fecha).
Cuándo importa: se escribe hacia atrás, de la entrega nueva a la anterior. Así la cadena se arma sola. Ejemplo: el informe de adopción 2026 de Wharton y GBK `continua` el de 2025.

### Resolución: cuánto detalle

#### `profundiza`
Glosa: el origen es una versión del destino con más detalle, en el mismo tema.
Distingue: vs `aplica` (aplica lleva el destino a otro caso; profundiza se queda en el mismo).
Meta: inverso-de `comprime`.

#### `comprime`
Glosa: el origen resume al destino: el mismo contenido en menos palabras. La ficha de una sesión comprime su transcripción.
Meta: inverso-de `profundiza`.

### Interpretación: qué le hace una afirmación a otra

Estas aristas registran una lectura. Son las que convierten un índice de archivos en algo que se puede recorrer para pensar. Se escriben donde hay una interpretación que registrar, no en todas partes.

#### `informa`
Glosa: contexto relevante que ilumina el destino sin afirmar ni negar. Es el lazo más débil.
Distingue: si hay una posición tomada, usa `confirma`, `tensiona` o `refuta`.
Meta: cerca-de `confirma`.

#### `confirma`
Glosa: el origen corrobora el destino desde otra base: un testigo independiente que llega a lo mismo.
Distingue: vs `sostiene` (sostiene es la base misma; confirma llega desde afuera) · vs `aplica` (aplica usa el destino en un caso; no lo respalda) · vs `analogo-a` (la analogía nombra una misma forma; no aporta evidencia).
Meta: opuesto-de `refuta`.

#### `sostiene`
Glosa: el origen es la base que mantiene en pie al destino: si se quita, el destino cae.
Distingue: vs `confirma` (confirma corrobora y es prescindible; sostiene es carga estructural).
Meta: más-general `confirma`.

#### `revela`
Glosa: el origen expone una propiedad del destino que el destino no dice de sí mismo.
Distingue: vs `informa` (informa aporta contexto; revela afirma un hallazgo sobre el destino).
Meta: más-general `informa`.

#### `complementa`
Glosa: origen y destino cubren mitades distintas de lo mismo; ninguno contiene al otro. Una keynote da el marco y un panel, los casos.
Distingue: es simétrica y afirma un reparto del trabajo.
Meta: más-general `informa`.

#### `analogo-a`
Glosa: origen y destino aplican el mismo principio en dominios distintos y llegaron a él por separado. Es una coincidencia de forma, no un préstamo: ninguno funda ni prueba al otro.
Distingue: vs `confirma` (confirma aporta evidencia; la analogía solo nombra la misma forma) · vs `deriva-de` y `aplica` (ahí uno tomó del otro; en la analogía nadie tomó nada).
Meta: más-general `informa`. Es simétrica.
Cuándo importa: deja encontrar la misma idea dicha en otro campo. Ejemplo: la etapa más lenta fija el ritmo de una línea de producción; el paso más lento fija la velocidad de una reacción química de varios pasos. El nombre viene de la biología, donde dos órganos son análogos cuando cumplen la misma función sin un origen común, como el ala de un ave y la de un insecto.

#### `tensiona`
Glosa: el origen está en tensión productiva con el destino: una grieta, una prueba de esfuerzo, una contradicción parcial. Lo deja en pie y lo afila.
Distingue: vs `refuta` (refuta busca tumbarlo) · vs `reencuadra` (reencuadra mueve el marco; no ataca la verdad).
Meta: opuesto-de `confirma` · cerca-de `refuta`.

#### `reencuadra`
Glosa: el origen cambia la perspectiva desde la que se mira el destino, sin negarlo.
Distingue: vs `tensiona` (tensiona presiona la verdad; reencuadra mueve el marco).
Meta: cerca-de `tensiona`.

#### `refuta`
Glosa: el origen argumenta contra el destino entero y busca invalidarlo.
Distingue: vs `tensiona` (tensiona conserva el destino) · vs `corrige` (corrige arregla una parte y deja el resto en pie).
Meta: opuesto-de `confirma`.

#### `corrige`
Glosa: el origen enmienda una afirmación puntual del destino que estaba equivocada: un dato, una cifra, un nombre.
Distingue: vs `refuta` (refuta va contra el destino entero) · vs `sustituye-a` (sustituye-a dice que algo regía y dejó de regir; corrige dice que estaba equivocado) · vs `tensiona` (tensiona deja la contradicción abierta; corrige dice cuál vale).
Meta: más-general `refuta`.
Cuándo importa: avisa que una cifra del destino no se puede citar. El porqué dice qué se corrige y por cuál valor. Ejemplo: en el webinar de Wharton, el speaker leyó al revés una cifra que la lámina muestra bien: el 58 % de quienes tienen un CAIO recién designado reporta ROI fuerte.

#### `sustituye-a`
Glosa: el origen reemplaza al destino o a una parte de él, que queda obsoleta sin haber sido falsa.
Distingue: vs `corrige` (corrige dice que el destino estaba equivocado) · vs `continua` (en una serie, la entrega anterior sigue valiendo para su fecha) · vs `reencuadra` (reencuadra deja los dos vigentes).
Meta: más-general `reencuadra`.
Cuándo importa: impide que un agente cite como vigente algo que dejó de regir.

#### `aplica`
Glosa: el origen es una aplicación o un caso del destino. La dirección va del caso al fundamento.
Distingue: vs `confirma` (confirma respalda desde afuera; aplica usa el fundamento en un caso).

#### `verifica`
Glosa: el origen pone a prueba al destino y deja el resultado: una revisión, una evaluación, una auditoría.
Distingue: vs `mide` (mide produce un número comparable en el tiempo; verifica deja un veredicto) · vs `confirma` y `tensiona` (esas ya tomaron posición; verifica nombra el examen) · vs `corrige` (corrige ya cambió algo; verifica solo examinó).
Meta: más-general `mide`.
Cuándo importa: deja preguntar qué se puso a prueba y qué no. El resultado va en el porqué.

## Meta-relaciones

Son las relaciones entre palabras del vocabulario. No se definen con otras.

- `más-general`: sube a una palabra más amplia. Toda palabra local la necesita.
- `cerca-de`: casi sinónimo. Exige decir en qué difiere.
- `inverso-de`: la misma relación mirada desde el otro extremo.
- `opuesto-de`: lo contrario.

## Palabras propias de cada repositorio

Cualquier palabra puede ser un tipo si está declarada. Las del núcleo valen en todos los repositorios que lo adoptan y no se redefinen. Cada repositorio declara las suyas en un diccionario local, con el mismo formato y una línea `más-general:` que la aterrice en una palabra ya declarada:

```
### `palabra-nueva`
más-general: `informa`
Glosa: qué afirma el origen sobre el destino, en una línea.
Distingue: vs `informa` (en qué se diferencia).
```

Una palabra nueva se acuña solo si gana su distinción. Si no se puede distinguir de una del núcleo, no es nueva: es la del núcleo con una nota en el porqué. Cuando una palabra local sirve en varios repositorios, se propone para el núcleo.

`grafo.py` comprueba estas reglas en cada corrida: que cada tipo usado esté declarado, que ninguna palabra local redefina una del núcleo y que cada palabra local tenga su `más-general`. Sin esa comprobación el vocabulario se pudre: en un repositorio de Brinca, un tercio de las aristas llegó a usar tipos sin declarar.

## Dónde se escribe una arista

Solo donde la relación no es obvia y aporta. Lo que ya dicen la carpeta o los metadatos del documento, como el evento al que pertenece una sesión o quién habló en ella, no se escribe como arista. La mayoría de los documentos no necesita ninguna. Un grafo que lo conecta todo no dice nada.

## Cómo se recorre

```
qué significa una relación      grep -n -A3 '^#### `TÉRMINO`' metodo/grafo/nucleo.md
el vocabulario, comprimido      grep '^Glosa:' metodo/grafo/nucleo.md
las aristas de un tipo          grep -rn '^- `tensiona` \[' --include='*.md' .
qué apunta a un documento       la sección `## Referido por` del documento
dónde hay aristas               grep -rln '^## Conexiones' --include='*.md' .
regenerar el espejo y validar   python3 metodo/grafo/grafo.py [--check]
```

En otro repositorio, la ruta del núcleo es la de su copia. El ancla `^- \`tipo\` \[` trae solo las aristas escritas a mano: las líneas de `## Referido por` llevan `←` después del tipo.

## Versiones

- **1.0 · 21 de octubre de 2026.** Primera versión pública. Reúne el vocabulario de los diccionarios que Brinca usaba en sus repositorios internos y agrega `analogo-a`.
