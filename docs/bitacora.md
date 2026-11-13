# Bitácora del proyecto

Registro de las decisiones tomadas y los problemas encontrados durante el proyecto, con su solución y el porqué. Se actualiza cada vez que aparece un problema o se toma una decisión. Las entradas más recientes van al final de cada sección.

**Formato de cada entrada:**
- **Contexto:** qué pasó o qué había que decidir.
- **Opciones:** las alternativas consideradas (en decisiones).
- **Solución / decisión:** qué se hizo.
- **Por qué:** la razón para elegir esa opción sobre las demás.
- **Quién decidió:** Santiago, Claude, o ambos.

Las entradas de una misma fase van numeradas (D = decisión, P = problema).

**Nombres de los chunkings:** en las primeras entradas se usan las letras de la discusión original. **"D" es el chunking por habilidad** (el principal: un chunk por habilidad, bloque de stats o nota del diseñador, con encabezado de contexto; archivo `chunks_D.jsonl`). **"A" es el chunking de tamaño fijo** (la línea base: ventanas de 512 tokens con overlap de 50; archivo `chunks_A.jsonl`). Desde la Fase 7 se usan solo los nombres descriptivos.

---

## Fase 0 · Configuración del repositorio (12 nov 2026)

### P-01 · Atribución automática en los commits
- **Contexto:** el primer commit se creó con una línea `Co-Authored-By` que atribuía el trabajo al asistente.
- **Solución:** se reescribió el historial para quitar la línea y se forzó el push. No se agregará atribución en commits, código ni documentos.
- **Por qué:** fue una petición explícita de Santiago.
- **Quién decidió:** Santiago.

### P-02 · Nombre de autor del trabajo en los commits
- **Contexto:** la configuración global de git usa el nombre "SantiPoler", que es de la cuenta del trabajo. El repo sí está en la cuenta personal (RovleZMex), y GitHub asocia los commits a ella por el correo.
- **Solución:** se configuró `user.name = "Santiago Robles"` solo para este repo, sin tocar la configuración global. Los dos primeros commits conservan "SantiPoler" porque corregirlos requiere un force push que el sistema de permisos bloqueó.
- **Por qué:** cambiar la configuración global afectaría los repos del trabajo.
- **Quién decidió:** Claude, a pedido de Santiago.

---

## Fase 1 · Corpus (12 nov 2026)

### D-01 · Temática: notas de parche de League of Legends
- **Contexto:** el enunciado deja libre la temática. Se evaluó la wiki de LoL.
- **Opciones:** páginas de campeones de la wiki; notas de parche recientes.
- **Decisión:** notas de parche.
- **Por qué:** el riesgo principal de un corpus de LoL es que el LLM ya conoce el juego y puede responder de memoria. Las notas recientes contienen valores que ningún modelo vio en su entrenamiento, así que una respuesta correcta solo puede venir del retrieval. Esto hace que la evaluación sea válida, incluidas las queries trampa.
- **Quién decidió:** Santiago propuso usar parches recientes; Claude buscó las fuentes.

### D-02 · Fuente: notas oficiales de Riot (no la wiki)
- **Opciones:** `leagueoflegends.com` (notas oficiales) o `wiki.leagueoflegends.com` (páginas por parche, con API MediaWiki).
- **Decisión:** notas oficiales.
- **Por qué:** es la fuente primaria y tiene una estructura homogénea entre parches. Impresas a PDF presentan retos reales de parsing (imágenes, listas anidadas, formato "antes ⇒ después"). En la wiki el problema principal serían las plantillas de MediaWiki, que es un reto menos representativo.
- **Quién decidió:** ambos.

### D-03 · 8 documentos: parches 26.15 a 26.22
- **Opciones:** 8 parches (26.15–26.22) o 10 (26.13–26.22).
- **Decisión:** 8.
- **Por qué:** el enunciado pide entre 5 y 10, y con 8 hay menos material que anotar. Abarcan del 29 jul al 4 nov 2026, todos posteriores al entrenamiento de los modelos.
- **Quién decidió:** Santiago.

### D-04 · Formato: imprimir las páginas a PDF con Playwright
- **Contexto:** las notas solo existen como páginas web.
- **Decisión:** imprimir cada página a PDF con Chromium (Playwright) y guardar también el HTML.
- **Por qué:** el enunciado pide parsear PDF. El HTML sirve como referencia independiente para medir cuánto se pierde al parsear el PDF.
- **Quién decidió:** Claude.

### D-05 · No versionar los PDF y HTML crudos
- **Decisión:** `data/raw/` está en `.gitignore`. El script `scripts/descargar_corpus.py` los regenera.
- **Por qué:** pesan unos 55 MB y son contenido con derechos de Riot. El texto procesado sí se versiona, porque es pequeño y el repo es privado.
- **Quién decidió:** Claude.

### P-03 · Playwright no encontraba el navegador
- **Contexto:** la versión de Playwright instalada en el entorno virtual (1.65.1) pedía un Chromium que no estaba descargado.
- **Solución:** `playwright install chromium` dentro del entorno virtual.
- **Por qué:** cada versión de Playwright trae fijada su propia versión de navegador; usar otra no funciona.

### P-04 · La barra de navegación tapaba texto en el PDF
- **Contexto:** la barra fija de Riot se imprimía encima de cada página del PDF y ocultaba contenido. Por ejemplo, "R - The Box" de Thresh en 26.22 quedaba debajo de la barra. Además, las tarjetas de cambios se partían entre páginas y Docling desordenaba la lectura: los valores de Thresh terminaban pegados a Zaahen.
- **Opciones:** corregirlo después, en el parser; o corregirlo en la descarga.
- **Solución:** antes de imprimir, ocultar todos los elementos `position: fixed/sticky` y aplicar `break-inside: avoid` a las tarjetas (`.patch-change-block`).
- **Por qué:** el texto tapado no se puede recuperar después. Hay que arreglarlo en el origen. Es un ajuste de impresión, no una alteración del contenido.
- **Quién decidió:** Claude, tras revisar visualmente la página 7 del PDF.

---

## Fase 2 · Parsing (12 nov 2026)

### D-06 · Idioma de las queries: inglés
- **Opciones:** inglés o español.
- **Decisión:** inglés.
- **Por qué:** es el mismo idioma que el corpus. Así la comparación de retrievers no se contamina con el problema de la traducción, y BM25 funciona porque las palabras coinciden. La presentación puede ir en español.
- **Quién decidió:** Santiago.

### D-07 · Parser: Docling
- **Opciones:** PyMuPDF (rápido, con tamaños de letra), Docling (modelo de layout, más lento) o parsear el HTML.
- **Decisión:** Docling.
- **Por qué:** es el parser más completo para entender la estructura del documento, y la diferencia de velocidad no importa con 8 documentos. Claude había propuesto PyMuPDF.
- **Quién decidió:** Santiago.

### P-05 · OCR de Docling generaba basura y era lento
- **Contexto:** con OCR activado, Docling intentaba leer los íconos de habilidades y producía caracteres como "曲". Tardaba ~150 s por documento.
- **Solución:** `PdfPipelineOptions(do_ocr=False)`.
- **Por qué:** el PDF se genera desde el navegador y ya trae capa de texto, así que el OCR no aporta nada. Sin OCR tarda ~10 s por documento.

### P-06 · Docling omitía encabezados de habilidad
- **Contexto:** Docling agrupa a veces el ícono de una habilidad con su título como un solo elemento `picture`, por ejemplo "E - Singularity" de Aurelion Sol en 26.22. `export_to_markdown()` no exporta el texto que está dentro de imágenes.
- **Solución:** no usar el Markdown de Docling. Se guarda su JSON completo y se recorre con `iterate_items(traverse_pictures=True)`.
- **Por qué:** el texto sí está en la estructura de Docling; solo lo pierde la exportación.

### D-08 · Reconstruir la jerarquía con reglas propias
- **Contexto:** Docling etiqueta el mismo tipo de encabezado a veces como `section_header` y a veces como `text`, y pone todos los encabezados al mismo nivel.
- **Decisión:** separar el proceso en dos pasos. `convertir_docling.py` guarda el JSON de Docling y `parsear_corpus.py` aplica las reglas del dominio:
  - Sección: texto en mayúsculas.
  - Entidad: enlace a `/champions/` o `/how-to-play/`, o una línea corta seguida de la cita del diseñador.
  - Habilidad: patrón "Q - Nombre".
- **Por qué:** las señales del dominio son más estables que las etiquetas de Docling. Separar los pasos permite ajustar las reglas sin volver a correr Docling.
- **Quién decidió:** Claude.

### P-07 · Docling unió dos líneas: "Q - Decimate Jinx"
- **Contexto:** en 26.21, el título de la habilidad de Darius quedó pegado al nombre de la siguiente campeona, y Jinx desaparecía como entidad.
- **Solución:** si una línea de habilidad termina en un nombre de campeón y la sigue una cita del diseñador, se separa en dos. Los nombres salen de la lista oficial de Data Dragon (`data/campeones.json`, versión 16.22.1).
- **Por qué:** con una lista cerrada de nombres no hay ambigüedad. Una heurística sobre mayúsculas habría fallado con nombres de varias palabras.

### P-08 · Encabezados repetidos dentro de los modos de juego
- **Contexto:** "CHAMPIONS", "AUGMENTS" y "BUGFIXES" aparecen en mayúsculas también dentro de Classic, ARAM: Mayhem y Arena. Se tomaban como secciones nuevas y se perdía a qué modo pertenecían. Los augments con "!" ("RISE!", "BEES!!!") también se tomaban como secciones.
- **Solución:** dentro de un modo, esos encabezados se tratan como grupos y los que llevan "!" como entidades. Un encabezado en mayúsculas que ya apareció antes también se trata como grupo.
- **Por qué:** para responder bien una pregunta sobre ARAM o Arena, el chunk tiene que llevar el modo en sus metadatos.

### P-09 · Pie de página en el corpus
- **Contexto:** al final aparecían artículos relacionados, la app de Riot y las preferencias de cookies.
- **Solución:** cortar en el primer encabezado "GAME UPDATES <fecha>".
- **Por qué:** en todos los parches es el primer elemento del pie de página.

### D-09 · Validar el parsing contra el HTML
- **Decisión:** usar los encabezados `h3` del HTML como referencia de qué campeones e items debe detectar el parser, y contar los "⇒" del PDF contra los del JSON.
- **Resultado:** 140/140 entidades y 931/933 cambios.
- **Por qué:** da una métrica objetiva del parsing para la presentación, en lugar de revisar a ojo.

### D-10 · Qué hacer con los tres errores restantes del parsing
- **Contexto:** después de D-09 quedaban tres errores. En una primera versión se propuso dejarlos todos documentados como "menores". Al revisarlos en contexto, uno resultó grave:
  - **Cambios perdidos (grave).** Docling no entregó 2 de los 933 cambios, y cada uno era *el único cambio* de su campeón: Draven en 26.19 (Attack Damage 62 ⇒ 64) y Darius en 26.21 (Q - Decimate, cooldown). Ambos quedaban solo con la cita del diseñador, sin ningún número, así que no se podría responder ninguna pregunta sobre ellos.
  - **Armas de Aphelios (moderado).** Calibrum, Severum, etc. quedaban como entidades separadas en 26.19. Un chunk de "Calibrum" no diría que pertenece a Aphelios.
  - **"Scoreboard Cleanup" (leve).** Queda dentro de ITEMS en 26.20. Solo cambia la etiqueta de sección; el contenido está bien.
- **Decisión:** corregir los dos primeros y dejar documentado el tercero (ver P-10 y P-12).
- **Por qué:** los dos primeros afectan lo que el sistema puede responder. El tercero no.
- **Quién decidió:** Claude propuso; Santiago aprobó.
- **Lección:** clasificar un error como "menor" por su número (2 de 933) fue un error. Hay que mirar qué información se pierde, no cuántas líneas.

### P-10 · Recuperar los cambios que Docling omite
- **Contexto:** ver D-10. El texto sí está en la capa de texto del PDF, pero Docling no lo entrega.
- **Opciones:** reglas para esos dos casos; cambiar de parser; o una verificación general contra la capa de texto.
- **Solución:** paso `recuperar_cambios()` en `parsear_corpus.py`. Para cada campeón que tiene cita del diseñador pero ningún "⇒", busca en el texto del PDF (pypdfium2) el tramo entre el final de su cita y el inicio de la cita de la siguiente entidad, y extrae de ahí los cambios. Los bloques recuperados quedan marcados con `"recuperado": "pdf-texto"`.
- **Por qué:** es una regla general, no un parche para dos casos, y aprovecha que el PDF tiene dos representaciones del mismo contenido. Docling sigue siendo el parser principal (D-07), y la capa de texto actúa solo como red de seguridad.

### P-11 · La recuperación generó falsos positivos
- **Contexto:** la primera versión de P-10 se aplicaba a cualquier entidad con cita y sin "⇒". Las entidades narrativas (como "Council Vote" o "Art") cumplen esa condición sin que les falte nada. Además, cuando no encontraba bien la cita siguiente, el tramo abarcaba miles de caracteres. El resultado fueron 70 "recuperaciones" falsas que duplicaban contenido de Arena.
- **Solución:** dos restricciones.
  - Solo se recupera para nombres que están en la lista oficial de campeones.
  - Solo si el tramo mide 600 caracteres o menos. Los casos reales miden menos de 100.
- **Por qué:** la recuperación debe ser conservadora. Es preferible no recuperar algo a meter texto equivocado en el corpus. Con las restricciones recupera exactamente los 2 casos reales.

### P-12 · Armas de Aphelios como subsecciones
- **Solución:** lista cerrada `ARMAS_APHELIOS` (Calibrum, Severum, Gravitum, Infernum, Crescendum). Si aparecen dentro de la entidad Aphelios, se tratan como subsección, igual que una habilidad.
- **Por qué:** son 5 nombres fijos del juego, así que una lista es más confiable que una heurística.

### D-11 · Resultado final del parsing
- **Validación:** 140/140 entidades y 933/933 cambios "⇒".
- **Error conocido que se acepta:** "Scoreboard Cleanup" dentro de ITEMS (26.20).
- **Observación pendiente:** en 26.19, la parte final de Arena (augments, "Guests of Honor") es la zona con la estructura más irregular. Los bugfixes generales quedan colgados de la última entidad ("Thresh"), porque Docling no entregó el encabezado "BUGFIXES & QOL CHANGES". El texto está completo, solo cambia la etiqueta. Se revisará si alguna query lo necesita.

---

## Fase 3 · Chunking (12 nov 2026)

Las opciones y sus tradeoffs se discutieron en un documento aparte, con ejemplos reales del corpus: A tamaño fijo, B recursivo, C por entidad, D por habilidad, E semántico, F jerárquico.

### D-12 · Chunking principal: un chunk por habilidad o bloque de stats (opción D)
- **Opciones:** C (un chunk por entidad: 564 chunks, mediana de 82 tokens) o D (un chunk por habilidad o Base Stats: 1,037 chunks, mediana de 38 tokens).
- **Decisión:** D.
- **Por qué:** es el más intuitivo y su granularidad encaja con las preguntas puntuales que esperamos, como "¿cuánto cooldown tiene ahora la Q de Darius?". Claude había propuesto C.
- **Riesgos conocidos, a mitigar en la implementación:**
  - La cita del diseñador no pertenece a ninguna habilidad, así que hay que decidir dónde va.
  - Hay chunks muy pequeños: 238 tienen menos de 20 tokens.
  - Una pregunta general ("¿qué cambió en Mel?") necesita varios chunks, lo que limita el Recall@k con k pequeño.
- **Quién decidió:** Santiago.

### D-13 · Línea base: tamaño fijo de 512 tokens con overlap de 50 (opción A)
- **Decisión:** se implementa también A para comparar contra D.
- **Por qué:** permite demostrar con números, y no solo argumentar, si el chunking estructural mejora la recuperación.
- **Consecuencia:** el ground truth se anota con unidades independientes del chunking. Un chunk de A cuenta como relevante si contiene el texto de la unidad correcta.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-14 · Encabezado de contexto en cada chunk
- **Decisión:** anteponer la ruta a cada chunk de D antes de calcular su embedding, por ejemplo `Patch 26.21 › CHAMPIONS › Darius › Q - Decimate`.
- **Por qué:** el mismo campeón aparece en varios parches con texto casi idéntico (Locke está en 6), y el número de parche no está en el texto. Con el encabezado, BM25 y el retriever denso pueden distinguir el parche. Además, el encabezado le da contexto semántico a los chunks de una sola línea.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-15 · La cita del diseñador va en un chunk propio ("Developer note")
- **Contexto:** con chunking por habilidad (D-12), la cita del diseñador no pertenece a ninguna habilidad. Riot la pone al inicio de cada campeón. Hay 320 citas, con una mediana de 56 tokens.
- **Opciones:**
  - **(a)** Chunk propio.
  - **(b)** Copiarla en cada chunk de habilidad del campeón.
  - **(c)** Ponerla solo en el primer chunk de habilidad.
- **Decisión:** (a). Encabezado del tipo `Patch 26.22 › CHAMPIONS › Locke › Developer note`.
- **Por qué:** cada tipo de chunk tiene un solo propósito: las preguntas de "por qué" van a la nota y las de números a la habilidad. Con (b), la cita (56 tokens) dominaría el embedding de chunks de ~15 tokens, y los chunks de un mismo campeón quedarían casi idénticos. (c) es arbitraria.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-16 · Contenido sin habilidad: un chunk por entidad
- **Contexto:** 258 unidades no tienen habilidad: stats de items, descripciones de augments, textos de modos de juego.
- **Decisión:** el chunk es la entidad completa, por ejemplo `Patch 26.21 › ITEMS › Hubris`. Si tampoco hay entidad (listas de bugfixes, introducciones de sección), el chunk es la sección o el grupo.
- **Por qué:** es la extensión natural de D-12: se usa el nivel más fino que tiene el contenido.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-17 · Unidades largas: partir en trozos de máximo 250 tokens
- **Contexto:** 15 unidades pasan de 300 tokens, sobre todo listas de bugfixes (la mayor tiene 568).
- **Decisión:** partirlas en trozos de máximo 250 tokens, cortando entre líneas y repitiendo el encabezado de contexto en cada trozo. Los trozos llevan sufijo `#1`, `#2`…
- **Por qué:** mantiene los chunks en el mismo orden de magnitud que el resto, y el encabezado repetido evita que el trozo 2 pierda el contexto.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### P-13 · Docling unió listas enteras en un solo párrafo
- **Contexto:** al aplicar D-17 aparecieron chunks de hasta 581 tokens formados por una sola línea. En algunas secciones de modos de juego, Docling juntó varios elementos de una lista en un párrafo:
  - todos los bugfixes de Classic en 26.17;
  - el campeón "NEW Fiora" mezclado con el texto de Classic en 26.18;
  - varios augments en uno ("Gold Arcane Axiom" en 26.21).
- **Solución:** en el chunking, si una línea sola excede el máximo, se parte por oraciones. Queda un solo chunk de 278 tokens (una oración muy larga en 26.15), que se acepta.
- **Por qué:** resuelve el tamaño sin tocar el parsing. **Limitación conocida:** en esos casos la jerarquía sigue mal, porque Fiora (26.18) y los augments unidos (26.21) no son entidades propias. Afecta solo secciones de Classic y ARAM: Mayhem. Si una query de evaluación depende de ellos, se corrige en el parser.

### D-18 · Ground truth independiente del chunking (`unit_ids`)
- **Contexto:** para comparar A contra D con Precision@k y Recall@k, el ground truth no puede apuntar a IDs de chunk, porque cada chunking tiene los suyos.
- **Decisión:** se define la **unidad de contenido** como parche/sección/grupo/entidad/subsección, por ejemplo `26.21/CHAMPIONS/Darius/Q - Decimate`. Cada chunk guarda en `unit_ids` las unidades que contiene: en D, exactamente una; en A, todas las que aparecen en la ventana (8 de mediana). El ground truth se anota en unidades, y un chunk es relevante si contiene alguna unidad correcta.
- **Por qué:** un solo ground truth sirve para cualquier chunking.

### P-14 · El mapeo de A perdía unidades con líneas largas
- **Contexto:** al principio, una unidad contaba como contenida en un chunk de A solo si alguna de sus líneas aparecía completa. Las líneas largas que la ventana corta a la mitad no aparecen completas en ningún chunk, así que 11 unidades quedaban sin chunk.
- **Solución:** contar la unidad si el inicio o el final (60 caracteres) de alguna de sus líneas aparece en el chunk.
- **Resultado:** las 1,124 unidades quedan cubiertas en A.

### D-19 · Resultado del chunking
| | Chunks | Tokens (mediana) | Mín – máx |
|---|---|---|---|
| D (habilidad + encabezado) | 1,149 | 57 | 15 – 278 |
| A (fijo 512/50) | 151 | 512 | 83 – 512 |

Tipos de chunk en D:

| Tipo | Chunks |
|---|---|
| Habilidad o stats | 564 |
| Nota del diseñador | 304 |
| Entidad sin habilidad | 184 |
| Sección | 97 |

---

## Fase 4 · Indexado (12 nov 2026)

Las opciones se discutieron en un documento aparte: 4 modelos de embeddings y 6 bases vectoriales, con precios y benchmarks verificados en noviembre de 2026.

### D-20 · Modelo de embeddings: Qwen3-Embedding-0.6B, local
- **Opciones:** Qwen3-Embedding-0.6B (local), OpenAI text-embedding-3-small (API), Voyage 4 (API), BGE-M3 (local).
- **Decisión:** Qwen3-Embedding-0.6B en la Mac (MPS), con 1,024 dimensiones y vectores normalizados.
- **Por qué:**
  - Es el modelo abierto de referencia en 2026 (MTEB English v2: 70.7 para el tamaño 0.6B).
  - Es gratuito, privado y reproducible.
  - Su contexto de 32 k tokens evita truncar los chunks de 512 de la línea base A, que con modelos de 256 o 512 tokens quedaría en desventaja.
  - El costo no fue factor: embeddear todo con una API costaría menos de 1 centavo.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-21 · Base vectorial: Chroma
- **Opciones:** NumPy/FAISS, Chroma, Qdrant, LanceDB, pgvector, Pinecone.
- **Decisión:** Chroma persistente en disco (`data/index/chroma/`), con dos colecciones (`chunks_D` y `chunks_A`) y distancia coseno.
- **Por qué:** con unos 1,300 vectores cualquier opción es instantánea, y Chroma tiene la API más simple. Claude había propuesto Qdrant por su camino a producción; la diferencia a esta escala es chica.
- **Quién decidió:** Santiago.

### D-22 · BM25 en Python y fusión RRF propia
- **Decisión:** BM25 con `rank_bm25`, y la fusión de rankings (Reciprocal Rank Fusion) escrita en el proyecto. Se implementa en la fase de retrievers.
- **Por qué:** la lógica clave del retriever híbrido queda visible en unas pocas líneas para la presentación, en lugar de quedar escondida dentro de la base de datos.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-23 · Instrucción de query: la que trae el modelo por defecto
- **Contexto:** Qwen3-Embedding es asimétrico: las queries llevan una instrucción antepuesta y los documentos no. El prompt por defecto es genérico ("Given a web search query, retrieve relevant passages that answer the query"). Qwen recomienda instrucciones específicas de la tarea.
- **Decisión:** usar la instrucción por defecto. Las funciones `embeddear_queries` y `embeddear_documentos` viven en `src/embeddings.py`, para que nunca se embeddee una query sin instrucción por error, que bajaría la calidad sin dar ningún error.
- **Por qué:** ajustar la instrucción sin ground truth sería afinar a ciegas. Queda como experimento posible una vez que tengamos las métricas.
- **Quién decidió:** Claude.

### P-15 · Chroma no acepta `None` ni listas como metadatos
- **Solución:** `None` se guarda como cadena vacía, y `unit_ids` como texto JSON. Se decodifican al leer.

### Observación · Prueba rápida del retriever denso (no es la evaluación formal)
Se probaron 3 preguntas a mano:
- **Darius 26.21:** D acierta con buen margen (0.77 contra 0.69).
- **"¿Por qué nerfearon a Thresh?":** D recupera primero la nota del diseñador, como se esperaba con D-15.
- **Locke en 26.22:** D acierta por un margen mínimo (0.68 contra 0.67 del 26.21 y 0.66 del 26.15). A pone primero un chunk de otro parche.

Es la primera evidencia del problema anticipado en D-14: el retriever denso casi no distingue parches, ni siquiera con el número en el encabezado. Es la motivación concreta del retriever híbrido.

**Rendimiento:** embeddear D tardó 67 s y A 46 s en la Mac M4. La primera descarga del modelo (~1.2 GB) tardó unos 3 minutos.

---

## Fase 5 · Retrievers (12 nov 2026)

### D-24 · Constante de RRF: 60
- **Decisión:** `k = 60` en Reciprocal Rank Fusion: `score = Σ 1 / (60 + rank)`.
- **Por qué:** es el valor estándar del artículo original de RRF (Cormack et al., 2009), y funciona bien sin ajuste. Queda como punto de partida.
- **Quién decidió:** Santiago.

### D-25 · Top-k = 10
- **Decisión:** cada retriever devuelve 10 chunks.
- **Por qué:** con el chunking por habilidad (D-12), una pregunta general como "¿qué cambió en Mel?" necesita varios chunks, y k = 10 deja margen para el Recall. Se puede reportar Precision@k y Recall@k también para k menores a partir del mismo ranking.
- **Quién decidió:** Santiago.

### Observación · Visualización del índice
- **Contexto:** Santiago preguntó cómo "ver" Chroma y los embeddings. Chroma local no trae interfaz visual.
- **Solución:** `scripts/visualizar_embeddings.py` proyecta los 1,300 vectores a 2D con UMAP (coseno, `random_state=42`) y genera un visor interactivo (`docs/visor_embeddings.html`, con Plotly). Tiene color por parche, sección o tipo, búsqueda por texto y las preguntas de prueba marcadas como estrellas.
- **Lo que muestra:**
  - Los 19 chunks de Locke de 6 parches quedan amontonados: dispersión de 0.21 contra 2.32 del corpus completo. Confirma visualmente que el retriever denso casi no distingue parches (D-14).
  - Las notas del diseñador tienden a agruparse (43 % de sus vecinos son notas, contra 26 % al azar).
- **Error propio corregido:** en la primera versión del visor afirmé que las notas "formaban su propia región". Lo medí y era exagerado, así que corregí el texto antes de publicarlo.

### Experimento · Tokenización para BM25 (exploratorio, 4 preguntas)
- **Contexto:** se compararon 5 tokenizadores sobre los 1,149 chunks de D:
  1. espacios;
  2. regex `\w+`;
  3. clásico (regex + stopwords + Porter);
  4. de dominio (posesivos, apóstrofos, parche como un token, nombres de campeón sin stemming);
  - 4b. de dominio sin cifras.
- **Hallazgos:**
  - **Espacios** deja la puntuación pegada (`26.21?`, `darius's`) y el chunk de Darius cae al lugar 128.
  - **Regex** parte `26.21` en `26` + `21`, y `vel'koz` en `vel` + `koz`.
  - **Stemming de Porter** convierte "Locke" en `lock`, que choca con "locked out" y "lock down" en 4 chunks ajenos. Motiva proteger los nombres de campeón.
  - **Ninguna variante ubica a Locke en 26.22 en primer lugar,** ni siquiera la 4, que tiene el token `26.22`. La causa es la normalización por longitud de BM25: el chunk de 26.22 tiene diez cifras y mide 33 tokens, contra 20 del de 26.21. Las cifras alargan el chunk sin aportar al match.
  - **La variante 4b** (sin cifras) arregla Locke pero baja a Vel'Koz al lugar 2. Bajar `b` a 0.3 no ayudó.
- **Conclusión:** con 4 preguntas no se puede elegir entre 2, 3, 4 y 4b; difieren en casos que estas preguntas no tocan. Se decide con el ground truth.
- **Error propio corregido:** en el primer intento de la variante 4b, el filtro de cifras también borraba el `26.22` del encabezado, que es justo el token que había que conservar. Se detectó al imprimir los tokens, antes de sacar conclusiones.

### D-26 · Tokenizador de dominio para BM25
- **Opciones:** espacios, regex `\w+`, clásico (regex + stopwords + Porter), de dominio.
- **Decisión:** de dominio (`src/tokenizador.py`):
  - minúsculas;
  - posesivos fuera;
  - apóstrofos internos unidos (`velkoz`);
  - números con punto como un solo token (`26.21`);
  - tokens de una letra conservados (Q, W, E, R);
  - stopwords fuera;
  - stemming de Porter, salvo los nombres de campeón de Data Dragon.
- **Por qué:** es el único que resuelve los casos difíciles del corpus por diseño y no por casualidad (ver el experimento de tokenización).
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-27 · "Quitar cifras" como interruptor, a decidir con el ground truth
- **Decisión:** `tokenizar(texto, quitar_cifras=...)` y `BM25Retriever(..., quitar_cifras=...)`. Con el interruptor activado se descartan las cifras salvo el número de parche. Se medirán las dos variantes.
- **Por qué:** en el experimento, quitar cifras arregló a Locke pero empeoró a Vel'Koz. Con 4 preguntas no hay base para decidir.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-28 · El híbrido fusiona los rankings completos
- **Contexto:** RRF suele aplicarse sobre los top-N de cada retriever, lo que agrega otro parámetro (N).
- **Decisión:** fusionar los rankings completos (los 1,149 chunks de D o los 151 de A).
- **Por qué:** con un corpus de este tamaño cuesta lo mismo (~0.06 s por query), y evita un parámetro arbitrario. Con 500 documentos habría que limitar N, lo cual es un punto para la sección de producción.
- **Quién decidió:** Claude.

### Implementación · Los retrievers (`src/retrievers.py`)
- `DenseRetriever`, `BM25Retriever` y `HybridRetriever` comparten la interfaz `buscar(query, k=10) -> list[Resultado]`, con id, score, `unit_ids` y texto. Cada uno se instancia sobre "D" o "A", lo que da 4 combinaciones para la evaluación (más 2 si se mide el interruptor de cifras).
- **Prueba rápida, ilustrativa:** en D, el híbrido pone el chunk correcto en el lugar 1 en las 4 preguntas, incluido Locke 26.22, donde BM25 solo lo dejaba en el lugar 2. En A, el denso falla 2 de 4 dentro del top-10. Latencia por query: Dense ≈ 0.4 s (incluye el embedding de la query en MPS), BM25 < 0.01 s, Hybrid ≈ 0.06 s una vez cargado el modelo.

---

## Fase 6 · Ground truth (12 nov 2026)

### D-29 · Proceso del ground truth: Claude propone, Santiago elige y corrige
- **Decisión:** Claude propone 16 candidatas (13 normales y 3 trampa) con respuesta ideal y unidades correctas. Santiago elige 10 (mínimo 2 trampa), corrige lo necesario y confirma las unidades. La revisión se hace en una página web con almacenamiento: lo que Santiago cambia queda guardado, y Claude lo lee de ahí para escribir `eval/ground_truth.json`.
- **Por qué:** el enunciado pide definir el ground truth "manualmente". La revisión final y la elección son de Santiago. Proponer candidatas ahorra tiempo y asegura variedad de tipos.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### Diseño de las candidatas (`eval/candidatas.json`)
Cada candidata pone a prueba algo distinto del sistema:

| Tipo | Qué prueba |
|---|---|
| Cambio numérico puntual (Darius Q, 26.21) | Lo básico. Además es un cambio recuperado de la capa de texto (P-10). |
| Mismo campeón en varios parches (Locke Q, 26.22) | Si el retriever distingue el parche. |
| "Por qué" + "qué" (Thresh, 26.22) | La nota del diseñador junto con los cambios numéricos. |
| Sin parche en la pregunta (Draven) | El sistema tiene que encontrar el parche por sí solo. |
| Pregunta general (Mel, 26.22) | 7 unidades: Recall@10 con chunking por habilidad (riesgo anotado en D-12). |
| Comparación entre parches (Locke W, 26.21 y 26.22) | Recuperar dos chunks de parches distintos. |
| Item (Doran's Bow) | Contenido fuera de campeones. |
| Modos de juego (Classic, ARAM: Mayhem, Arena) | Secciones con la estructura más irregular. |
| Sistemas y eventos (replays, TFT, Hall of Legends) | Contenido que no es de balance. |

Hay 3 trampas, todas de tipos distintos:
- **Parche que no existe:** 26.23.
- **Campeón sin cambios:** Teemo en la Grieta en 26.22. Solo aparece en Arena.
- **Dato que las notas no dan:** win rate de Locke. Hay contexto relacionado, pero no el dato.

**Verificación:** todas las unidades citadas existen en el índice. Al redactar la candidata de Classic 26.21, la primera idea era "Hecarim y Lucian"; revisando la nota de la sección resultaron ser cuatro campeones nuevos (también Mordekaiser y Yorick).

### D-30 · Ground truth final: 12 preguntas (10 normales y 2 trampa)
- **Contexto:** de las 16 candidatas, Santiago eligió 12. El enunciado dice "un set de 10 queries".
- **Decisión:** quedarse con las 12 (`eval/ground_truth.json`, ids `q01` a `q12`).
  - **Fuera:** RISE! (ARAM: Mayhem), límite de replays, Hall of Legends y la trampa de Teemo.
  - **Trampas que quedan:** el parche 26.23 (no existe) y el win rate de Locke (las notas no lo dan).
- **Por qué:** 12 cumple el mínimo y da algo más de señal para comparar retrievers. La desviación de la letra del enunciado es hacia arriba.
- **Quién decidió:** Santiago.

### D-31 · Preguntas sin el nombre de la habilidad
- **Contexto:** Santiago cambió dos preguntas:
  - *"What changes did Locke's Q - Ritual Nails receive in patch 26.22?"* → *"What changes did Locke's Q get in patch 26.22?"*
  - *"How did Locke's W - Soul Ignition change…"* → *"How did Locke's W change…"*
- **Por qué (Santiago):** es más realista; un usuario escribe "la Q", no el nombre de la habilidad.
- **Consecuencia para la evaluación:** las dos preguntas se vuelven más difíciles. BM25 pierde los términos "Ritual Nails" y "Soul Ignition", y el único vínculo léxico entre "Q" y el chunk es el encabezado de contexto (`… › Locke › Q - Ritual Nails`). La q02 combina además el problema de distinguir el parche (Locke Q cambió en 26.15, 26.21 y 26.22): es la pregunta que más debería separar a Dense de Hybrid.
- **Corrección menor:** al editarla, a la q02 le faltaba el verbo. Se corrigió a "get" con la aprobación de Santiago.
- **Quién decidió:** Santiago.

---

## Fase 7 · Evaluación del retrieval (12 nov 2026)

### D-32 · El Recall@k se calcula sobre unidades, no sobre chunks
- **Contexto:** un chunk de tamaño fijo contiene unas 8 unidades y uno por habilidad exactamente una. Si se contaran chunks, el denominador dependería del chunking (Mel 26.22 son 7 chunks por habilidad y 2 de tamaño fijo) y los dos chunkings no serían comparables.
- **Decisión:** `Recall@k = unidades relevantes cubiertas por los top-k / unidades relevantes de la pregunta`.
- **Por qué:** los dos chunkings se miden contra lo mismo (las unidades del ground truth), y la métrica responde lo que importa: si la información necesaria le llegó al LLM.
- **Ejemplo real (q05, Mel 26.22, 7 unidades):**
  - Por habilidad · Hybrid cubre 5/7 (0.71).
  - Tamaño fijo · Hybrid cubre 4/7 (0.57).
  - Por habilidad · Dense cubre 3/7 (0.43). La primera medición había dado 2/7 por un problema de la búsqueda aproximada de Chroma (P-16).
- **Quién decidió:** Santiago, sobre la propuesta de Claude, después de pedir que se le explicara qué es una unidad.

### D-33 · Precision@k estándar, con el sesgo a favor del tamaño fijo explicado
- **Decisión:** `Precision@k = chunks relevantes en los top-k / k`. Un chunk es relevante si contiene al menos una unidad correcta.
- **Sesgos que se explican al presentar:**
  - **A favor del tamaño fijo:** un chunk de 8 unidades cuenta como relevante aunque 7 no lo sean.
  - **Techo bajo del chunking por habilidad con k grande:** con 1 unidad relevante, P@10 no pasa de 0.10.
- **Por qué:** una "precisión por tokens" corregiría el primer sesgo, pero complica la explicación.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-34 · Las preguntas trampa no entran en las métricas de retrieval
- **Decisión:** P@k, R@k y MRR se calculan sobre las 10 preguntas normales. Las 2 trampas (q11, q12) se evalúan en la generación: ¿el modelo se niega o inventa?
- **Por qué:** sin unidades relevantes, el Recall es 0/0 y la Precision siempre 0. Solo bajarían todos los promedios por igual.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### D-35 · k = 1, 3, 5 y 10; seis configuraciones; MRR como extra
- **Configuraciones:**
  - Por habilidad · Dense
  - Por habilidad · Hybrid (la comparación principal)
  - Tamaño fijo · Dense
  - Tamaño fijo · Hybrid
  - Por habilidad · BM25 solo (referencia)
  - Por habilidad · Hybrid sin cifras (el interruptor de D-27)
- **MRR:** promedio de 1 / posición del primer chunk relevante.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

### P-16 · La búsqueda aproximada de Chroma omitía chunks
- **Contexto:** al repetir el ejemplo de Mel, "Por habilidad · Dense" cubrió 3/7 unidades; horas antes había dado 2/7 con la misma pregunta y el mismo índice. Se comparó la búsqueda de Chroma (HNSW, aproximada) contra una búsqueda exacta sobre los mismos vectores. Con la configuración por defecto (`ef_search = 10`), el top-10 de Chroma difería del exacto en 5 de 12 preguntas, y en 2 le faltaba un chunk. Aun con `ef_search = 200` seguía faltando un chunk en 3 preguntas, con diferencias de similitud reales (0.554 contra 0.557), no empates. No se pudo explicar del todo la diferencia entre las dos corridas.
- **Opciones:** subir más `ef_search`; reconstruir el índice con otros parámetros; o búsqueda exacta.
- **Solución:** el retriever denso lee los vectores, textos y metadatos de Chroma una vez, y busca de forma exacta (producto punto contra todos los vectores normalizados). Chroma sigue siendo el almacén de vectores (D-21); solo se deja de usar su búsqueda aproximada.
- **Por qué:** con 1,149 vectores, la búsqueda exacta es una multiplicación de matrices de menos de un milisegundo, y hace la evaluación reproducible: tres corridas seguidas dan resultados idénticos. La búsqueda aproximada solo se justifica a gran escala, lo cual es un punto para la sección de producción (con 500 documentos, unos 70 mil chunks, sí se usaría HNSW con `ef_search` ajustado y medido contra la búsqueda exacta).
- **Lección:** una métrica que cambia entre corridas sin cambios en los datos es un bug, no ruido. Se detectó porque el ejemplo del documento de métricas no coincidía con la evaluación.

### Resultados del retrieval (`eval/resultados/`)
10 preguntas normales, búsqueda exacta, resultados reproducibles.

| Configuración | P@1 | P@5 | R@5 | R@10 | MRR |
|---|---|---|---|---|---|
| Por habilidad · Dense | 0.60 | 0.32 | 0.66 | 0.76 | 0.70 |
| **Por habilidad · Hybrid** | 0.60 | 0.38 | **0.83** | **0.84** | **0.75** |
| Tamaño fijo · Dense | 0.30 | 0.14 | 0.51 | 0.61 | 0.41 |
| Tamaño fijo · Hybrid | 0.40 | 0.14 | 0.57 | 0.61 | 0.49 |
| Por habilidad · BM25 solo | 0.60 | 0.32 | 0.76 | 0.82 | 0.72 |
| Por habilidad · Hybrid sin cifras | 0.60 | 0.38 | 0.83 | 0.84 | 0.75 |

**Hallazgos:**
- **Hybrid supera a Dense con el chunking por habilidad.** La ganancia sale de 3 preguntas: q05 Mel (0.43 → 0.71), q09 Bel'Veth en Arena (0.50 → 1.00) y q02 Locke Q, donde la respuesta sube del lugar 8 al 4.
- **El chunking por habilidad supera al de tamaño fijo.** El de tamaño fijo no trae ningún chunk relevante en q02, q08 ni q09.
- **BM25 solo es casi tan bueno como el híbrido** (0.82). El corpus es muy léxico: nombres propios y números de parche.
- **"Sin cifras"** empata en R@10 y MRR, mejora R@3 (0.59 → 0.69) y sube la q02 al lugar 2.

**Errores principales:**
- **q06 (Locke W en dos parches):** ninguna configuración trae la W de 26.21. El número de parche pesa poco, y la pregunta ya no tiene el nombre de la habilidad (D-31).
- **q08 (campeones nuevos en Classic):** R@10 de 0.20 o menos en todas. La pregunta dice "added" y las notas dicen "is back" o "four more ghosts". Además, hay notas de Classic muy parecidas en 26.16, 26.17 y 26.18.
- **q02 (Locke Q):** el ruido sí habla de Locke, pero de otro parche o modo: el sonido de su Q en 26.16 y su daño en ARAM en 26.20.
- **q05 (Mel):** una pregunta general se parece a la nota del diseñador más que a los chunks de números, así que Dense trae solo 3 de 7 unidades.

### D-36 · Retriever para la generación: Por habilidad · Hybrid sin cifras
- **Opciones:** Hybrid estándar o Hybrid sin cifras. Las dos tienen el mismo Recall@10 (0.84) y el mismo MRR (0.75).
- **Decisión:** Hybrid sin cifras: BM25 ignora los valores numéricos al tokenizar, salvo el número de parche. El texto que recibe el LLM y el retriever denso no cambian.
- **Por qué:** empata o gana en todas las métricas promedio. Mejora el Recall@3 (0.59 → 0.69) y sube la q02 (Locke Q) del lugar 4 al 2, el caso que motivó el ajuste (los valores alargaban el chunk correcto y BM25 lo penalizaba por longitud).
- **Riesgo conocido:** una pregunta que busque por un valor ("which ability went from 6s to 5s?") pierde el apoyo léxico. Ninguna pregunta del ground truth es de ese tipo.
- **Quién decidió:** Santiago, sobre la propuesta de Claude, después de pedir que se le explicara qué se quitaba y dónde.

### D-37 · Las preguntas con errores de retrieval se quedan como errores documentados
- **Contexto:** tres preguntas fallan o salen débiles en todas las configuraciones: q06 (la W de Locke en dos parches), q08 (campeones nuevos en Classic) y q02 (Locke Q, con ruido de otros parches).
- **Decisión:** no ajustar el sistema para arreglarlas. Quedan explicadas en el análisis de errores.
- **Por qué:** ajustar el sistema después de ver el ground truth (por ejemplo, filtrando por el parche que menciona la pregunta) inflaría los resultados. Los errores bien explicados son justo lo que pide el enunciado.
- **Quién decidió:** Santiago, sobre la propuesta de Claude.

---

## Fase 8 · Generación (12 nov 2026)

### D-38 · LLM de generación: Claude Haiku 5.5 vía la API de Anthropic
- **Decisión:** `claude-haiku-5-5`, con la API key de Santiago. La key se guarda en `.env`, que está en `.gitignore` y nunca se sube.
- **Datos (noviembre 2026):** USD 0.10 por millón de tokens de entrada y 0.50 de salida. 12 preguntas con ~10 chunks de contexto cuestan menos de un centavo.
- **Por qué:** modelo rápido y barato, suficiente para responder a partir de un contexto dado.
- **Quién decidió:** Santiago.

### D-39 · Juez de RAGAS: Claude Sonnet 5.5
- **Decisión:** las métricas de RAGAS (faithfulness, answer relevancy, context precision/recall, answer correctness) las calcula `claude-sonnet-5-5` como juez.
- **Por qué:** que Haiku, el modelo que genera, se califique a sí mismo es una evaluación débil. Un juez más capaz es la práctica habitual, y con 12 preguntas el costo es de centavos.
- **Quién decidió:** Santiago.

### D-40 · Entregables: presentación y repositorio
- **Contexto:** el enunciado dice "La presentación deberá cubrir los 4 aspectos" (arquitectura con código clave, documentos y procesamiento, evaluación y resultados, visión de producción). No pide notebooks.
- **Decisión:** el entregable es la presentación más este repositorio. Al final se hará una demo sencilla (un notebook o una página) para correr el sistema el día de la presentación.
- **Quién decidió:** Santiago.

### D-41 · Prompt de generación
- **Decisión** (`src/generacion.py`):
  - **Solo el contexto:** prohibido usar lo que el modelo sabe del juego.
  - **Parche siempre indicado** en cada dato de la respuesta.
  - **Números exactos,** con su antes ⇒ después.
  - **Negativa con frase fija:** "The provided patch notes do not contain this information."
  - **Respuesta parcial explícita:** si falta una parte, dice cuál.
  - **Citas `[n]`** al chunk usado. Se quitan antes de RAGAS.
  - **Idioma:** inglés, como el ground truth.
  - **Effort:** `medium`.
- **Por qué:**
  - La frase fija permite medir automáticamente el rechazo de las trampas.
  - La regla de respuesta parcial cubre el caso conocido de la q06, cuyo retriever no trae la W de 26.21.
  - La prohibición de conocimiento previo evita que Haiku rellene huecos con valores de parches viejos que conoce.
- **Quién decidió:** Santiago aprobó la propuesta de Claude sin cambios.

### Resultados de la generación (`eval/resultados/generacion.json`)
Retriever: por habilidad · Hybrid sin cifras, top-10. 12 preguntas, USD 0.004 en total, de 1.0 a 4.0 s por pregunta.
- **Trampas:** las 2 rechazadas con la frase exacta.
- **Información parcial reconocida en las 3 preguntas donde el retriever falló:**
  - **q06:** da la W de 26.22 y dice que no encontró la de 26.21.
  - **q05:** responde 5 de 7 partes y dice que faltan la Q y la W.
  - **q08:** nombra a Lucian, infiere que hubo más campeones de las Shadow Isles sin inventar nombres, y no cuenta a Mordekaiser porque su fragmento no dice que sea nuevo.
- **q02:** usa solo el chunk de 26.22 y descarta los de Locke de otros parches que venían en el contexto.
- **Observación:** cuando el retriever falla, el modelo lo dice en vez de alucinar. Falta confirmarlo con la faithfulness de RAGAS.

---

## Fase 9 · Evaluación de la generación con RAGAS (12 nov 2026)

### D-42 · Métricas de RAGAS y tratamiento de las trampas
- **Métricas:** sobre las 10 preguntas normales, con Claude Sonnet 5.5 como juez (D-39) y Qwen3-Embedding-0.6B como embeddings:
  - **faithfulness:** si la respuesta está respaldada por los chunks.
  - **answer_relevancy:** si contesta la pregunta.
  - **context_precision:** si los chunks relevantes salieron arriba, comparando con la respuesta ideal.
  - **context_recall:** si los chunks traen todo lo que dice la respuesta ideal.
  - **answer_correctness:** si coincide con la respuesta ideal.
- **Trampas (q11, q12):** se miden con la tasa de rechazo correcto, detectada por la frase fija del prompt (D-41). También se revisa que ninguna pregunta normal se rechace por error.
- **Por qué:** las métricas que comparan contra el contexto o contra una respuesta ideal no aplican bien a una respuesta que es solo la negativa.
- **Quién decidió:** Santiago aprobó la propuesta de Claude.

### P-17 · RAGAS 0.4.3 incompatible con las versiones actuales de LangChain y del SDK de Anthropic
- **Problemas, en el orden en que aparecieron:**
  1. `ragas` importa `langchain_community.chat_models.vertexai`, que `langchain-community` 0.4.2 ya no trae. **Solución:** fijar `langchain-community==0.4.1`.
  2. RAGAS se conecta a Anthropic a través de `instructor`, que envía `temperature`. El SDK actual de Anthropic (2.8) ya no acepta ese parámetro, porque la API lo retiró. Además, `instructor` obtiene salidas estructuradas forzando una herramienta, y Sonnet 5.5 rechaza ese modo.
- **Solución del segundo punto:** un adaptador propio (`src/juez.py`), una subclase de la interfaz de LLM de RAGAS que llama a Sonnet con las salidas estructuradas nativas de la API (`messages.parse` con el modelo Pydantic que pide cada métrica). Otra subclase conecta los embeddings de Qwen3.
- **Por qué:** evita depender de dos capas de librerías desfasadas, y son unas 40 líneas fáciles de mostrar. Se verificó con una pregunta antes de correr la evaluación completa.

### Resultados de RAGAS (`eval/resultados/ragas.json`)
Juez: Claude Sonnet 5.5, 190 llamadas, USD 1.14.

| Métrica | Promedio |
|---|---|
| faithfulness | **0.971** |
| answer_relevancy | 0.921 |
| context_precision | 0.758 |
| context_recall | 0.816 |
| answer_correctness | 0.680 |

- **Trampas:** 2 de 2 rechazadas. Ningún rechazo indebido en las preguntas normales.
- **Faithfulness casi perfecta:** Haiku no inventó datos del juego. Los dos descuentos se revisaron afirmación por afirmación:
  - **q02 (0.89):** error real pero menor. Haiku dijo que el chunk "26.22 › OVERVIEW" mencionaba a Locke, y ese chunk no lo menciona (la mención está en otro chunk, la nota del diseñador de la introducción). Es un error al describir un fragmento, no un dato inventado.
  - **q08 (0.82):** limitación de la métrica. Las afirmaciones descontadas son sobre lo que *falta* ("falta la parte de los otros campeones", "no puedo listar a Mordekaiser"). El juez no puede verificarlas contra el contexto y las marca como no respaldadas, aunque son la conducta correcta pedida por la regla 5 del prompt.
- **Answer correctness baja donde falló el retriever:** q06 0.29 (falta la W de 26.21), q08 0.36 (solo Lucian), q05 0.51 (5 de 7 partes). Haiku respondió con honestidad lo que tenía, pero la respuesta queda incompleta frente a la ideal. Confirma que el cuello de botella es el retrieval, no la generación.
- **La métrica también castiga lo que sobra:** answer_correctness baja en respuestas correctas que agregan aclaraciones sobre lo que no está (q02 0.64). Es una propiedad de la métrica a mencionar en la presentación.

---

## Fase 10 · Presentación (12 nov 2026)

### D-43 · Cuellos de botella al escalar a 500 documentos: parsing y retrieval
- **Postura:** hay dos cuellos de botella principales.
  - **Parsing:** Docling necesitó varias adaptaciones a mano en solo 8 documentos (P-04 a P-13): la barra que tapaba texto, los encabezados dentro de imágenes, las líneas unidas, las listas fusionadas y los cambios omitidos. Con 500 documentos (~1.5 h de Docling a ~10 s cada uno) no es viable revisar cada salida, y los errores silenciosos llegarían al índice.
  - **Retrieval:** el problema principal que se midió fue distinguir documentos muy parecidos (el mismo campeón en varios parches). Con 500 documentos hay muchos más casi duplicados, y la evaluación mostró que el retrieval es lo que limita la respuesta final (faithfulness 0.97 contra answer correctness 0.68).
- **Quién decidió:** Santiago, a partir de los candidatos propuestos por Claude.

### D-44 · Estilo de la presentación
- **Decisión:** estilo académico, pulcro y limpio, sin tono de venta, con el logo de la Universidad de Sonora.
- **Quién decidió:** Santiago.

### Presentación (`docs/presentacion/`, publicada como deck)
- **Estructura:** 22 diapositivas que siguen los 4 aspectos del enunciado:
  - **Arquitectura:** corpus, pipeline, herramientas y dos diapositivas de código clave (la fusión RRF y las reglas del prompt).
  - **Documentos y procesamiento:** retos de parsing, validación y chunking.
  - **Evaluación:** ground truth, métricas, tabla de retrievers, Recall@10 por pregunta, análisis de errores, RAGAS y el hallazgo principal.
  - **Producción:** deployment, elección del LLM y escalamiento.
  - Cierran conclusiones y una diapositiva final.
- **Estilo (D-44):**
  - Académico, con fondo marfil y el azul del escudo.
  - El dorado solo como filete, nunca como color de texto.
  - Source Serif 4 para títulos, IBM Plex Sans para texto y JetBrains Mono para código.
- **Logo:** el escudo azul oficial, tomado de identidadbuho.unison.mx (la página de identidad institucional de la Unison). Va a la **izquierda**, como pide el manual de identidad institucional; en la primera versión estaba a la derecha y se corrigió.
- **Pendientes de Santiago (marcados entre corchetes en la portada):** nombre del programa de maestría, profesor y fecha de presentación.
- Todas las cifras salen de `eval/resultados/` y de la bitácora. Cada diapositiva tiene notas del orador.

### Rediseño de la presentación
- **Contexto:** Santiago pidió más "taste" y quitar el olor a texto generado ("AI slop").
- **Cambios:**
  - **Sistema visual:** un solo fondo claro y una única diapositiva oscura. Sin barras decorativas ni tarjetas para todo. La sección va en el pie.
  - **Escala tipográfica fija:** 24 / 26 / 28 / 32 / 56 px.
  - **Gráficas en lugar de solo tablas:** una diapositiva nueva con la comparación de configuraciones, y barras para RAGAS y para el Recall@10 por pregunta.
  - **Títulos:** todos enuncian el hallazgo, y el detalle pasó a las notas del orador. Quedan 23 diapositivas.
- **Verificación:**
  - Ninguna cifra visible es nueva: se compararon todos los números del texto contra la versión anterior.
  - Se mantienen el código real, el logo a la izquierda, los datos entre corchetes de la portada y los nombres descriptivos de los chunkings.
- **Corrección posterior:** el rediseño había convertido la diapositiva de escalamiento en "lo que más pesa es distinguir documentos casi idénticos", poniendo el retrieval por encima del parsing. Eso contradecía D-43 (dos cuellos de botella al mismo nivel), así que se restauró: título "A 500 documentos, el parsing y el retrieval son los dos cuellos de botella", parsing primero, y la conclusión 4 ajustada en el mismo sentido.

### D-45 · Repositorio público, con el texto procesado incluido
- **Opciones:**
  - público tal cual;
  - público sin `data/processed/`, `data/chunks/` y `eval/resultados/` (regenerables con los scripts);
  - privado con acceso al profesor.
- **Decisión:** público tal cual. Los PDF y HTML originales de Riot siguen fuera del repo (D-05). Se verificó antes que `.env` (con la API key) nunca se subió y que ningún commit lleva atribución.
- **Por qué:** es texto de notas públicas usado con fines académicos, y así cualquiera puede revisar y correr la evaluación sin regenerar el pipeline.
- **Quién decidió:** Santiago.

### D-46 · Demo: app local con Streamlit
- **Opciones:** app local, app hospedada (Hugging Face Spaces o Streamlit Cloud) o página estática con resultados precalculados.
- **Decisión:** solo la app local (`app.py`), en la Mac de Santiago el día de la presentación.
  - **Qué hace:** acepta una pregunta libre o una del ground truth. Muestra la respuesta de Haiku 5.5 (con el retriever por habilidad · Hybrid sin cifras) con sus citas, tiempo y tokens, y los chunks de Dense y de Hybrid lado a lado.
- **La API key:** queda en `.env` local, ignorado por git. El repo trae `.env.example` con la variable vacía. Sin clave, la app muestra el retrieval y avisa que no puede generar la respuesta.
- **Por qué:** es la opción más simple y la clave nunca sale de la máquina. Una app hospedada expondría la clave al gasto de cualquiera con el enlace.
- **Verificación:** prueba automática con el probador de Streamlit (pregunta de Locke Q) y captura de la app real con la pregunta de Thresh; las dos sin errores.
- **Quién decidió:** Santiago.
