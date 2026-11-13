# Bitácora del proyecto

Registro de las decisiones tomadas y los problemas encontrados durante el proyecto, con su solución y el porqué. Se actualiza cada vez que aparece un problema o se toma una decisión. Las entradas más recientes van al final de cada sección.

**Formato de cada entrada:**
- **Contexto:** qué pasó o qué había que decidir.
- **Opciones:** las alternativas consideradas (en decisiones).
- **Solución / decisión:** qué se hizo.
- **Por qué:** la razón para elegir esa opción sobre las demás.
- **Quién decidió:** Santiago, Claude, o ambos.

Las entradas de una misma fase van numeradas (D = decisión, P = problema).

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
