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

### D-10 · Errores de parsing que se aceptan
- **Contexto:** quedan tres errores menores:
  - 2 cambios que Docling no extrae: Base Stats en 26.19 y un cooldown en 26.21.
  - Las armas de Aphelios quedan como entidades propias en 26.19.
  - "Scoreboard Cleanup" queda dentro de ITEMS en 26.20.
- **Decisión:** dejarlos y documentarlos.
- **Por qué:** corregirlos requiere reglas ad hoc para un solo caso. Ninguno afecta las queries que se planean, y sirven como ejemplos para el análisis de errores. Si alguna query de evaluación depende de ellos, se corrigen.
- **Quién decidió:** Claude. Pendiente de confirmación de Santiago.
