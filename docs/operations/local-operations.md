# Operación local de K9 Expert

Guía para instalar, configurar y operar K9 Expert en una Mac con Apple Silicon dentro de una red local. Todo se ejecuta en la máquina: no hay servicios de inferencia externos.

## 1. Requisitos

- macOS en Apple Silicon. Probado en un M3 Pro de 18 GB; la huella medida es de ~4 GB (`docs/evaluation/baseline-2026-11-01.md`).
- Python 3.13, Node.js 20 o superior y [Ollama](https://ollama.com).
- Opcional: Tesseract con datos de español (`brew install tesseract tesseract-lang`). Sin él, las páginas que requieren OCR conservan su texto directo y quedan marcadas como `ocr_unavailable`.

## 2. Instalación

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
npm --prefix frontend ci
```

## 3. Modelos

```bash
ollama pull llama3.2:3b               # alias simple y fallback (también text-default del chat heredado)
ollama pull qwen3.5:2b                # alias complex
ollama pull nomic-embed-text:latest   # alias embedding-default (768 dimensiones)
```

El enrutador (`[router]`) elige el alias `simple` o `complex` por la complejidad de cada consulta; el gateway resuelve el modelo concreto, aplica `generation_timeout_seconds`, `generation_max_retries` y el respaldo `fallback`, y envía `think=false` para que los modelos con razonamiento devuelvan sólo JSON. Antes de una demostración sin red ejecute `scripts/preflight.py` (ver README).

Ollama debe escuchar sólo en `127.0.0.1:11434`, que es su valor por defecto. Nunca lo expongas a la LAN. El frontend no conoce su dirección.

Cambiar el modelo o la dimensión de embeddings hace incompatible el snapshot activo: la siguiente publicación falla con `full_reindex_required`. En ese caso hay que reconstruir el índice completo partiendo de un directorio de datos vacío (ver §7).

La versión `page-section-v3-classified` añade metadatos auditables de raza, grupo, función y sección. El enriquecimiento se construye en una generación candidata: el snapshot anterior permanece activo hasta que conteo, dimensiones, vocabulario, metadatos y recuperación de humo sean válidos. Un fallo descarta la candidata. Para volver a la generación anterior use el endpoint de rollback de §6; no edite la colección Chroma activa. El cambio de modelo, dimensión o versión de chunking requiere reindexación completa y nunca mezcla vectores incompatibles.

## 4. Configuración

| Fuente | Contenido |
|---|---|
| `config/k9.defaults.toml` | Servidor, modelos, recuperación, umbral de suficiencia, retención y telemetría. Para otro archivo, usa `K9_CONFIG=/ruta/k9.toml`. |
| `K9_DATA_DIR` | Directorio de datos. Por defecto `data/`, que contiene SQLite, PDF gestionados, índices, cachés y copias. |
| `K9_ADMIN_SECRET` | Secreto administrativo. **Sólo por variable de entorno**; nunca se lee de archivos. Sin él, todas las rutas administrativas responden 401. |

Valores que conviene conocer:

- `[retrieval] sufficiency_minimum_score = 0.68`: por debajo de esta similitud el sistema se abstiene. Está calibrado de forma provisional; recalíbralo si cambias el modelo de embeddings.
- `[retention]`:
  - `trace_days`: borra las trazas.
  - `feedback_comment_days`: vacía los comentarios de feedback y conserva la valoración útil/no útil.
  - `deleted_source_days`: borra físicamente los PDF de documentos eliminados.

  El trabajador aplica estas retenciones periódicamente.
- `[telemetry] store_protected = false`: las trazas nunca guardan preguntas completas, texto de documentos, rutas ni secretos. Actívalo sólo para diagnóstico. Incluso activado, exportar una pregunta exige `include_protected=true` y queda auditado.

## 5. Ejecución

Se usan tres procesos, cada uno en su terminal:

```bash
export K9_ADMIN_SECRET='…'          # elige un secreto largo
make serve                          # API en 127.0.0.1:8000
make worker                         # trabajador de ingesta (concurrencia 1)
npm --prefix frontend run dev       # interfaz en http://127.0.0.1:5173
```

`make api` arranca la API con recarga automática, para desarrollo.

### Acceso desde el móvil en la LAN

La API debe quedarse en loopback. Expón sólo el servidor web, que reenvía `/api` a `127.0.0.1:8000`:

```bash
npm --prefix frontend run build
npm --prefix frontend run preview -- --host 0.0.0.0 --port 4173
```

Abre `http://<ip-de-la-mac>:4173` desde el teléfono. Ten en cuenta:

- Las rutas administrativas también son alcanzables a través del proxy, por lo que `K9_ADMIN_SECRET` es obligatorio.
- La LAN no es autenticación. No publiques el puerto en Internet: el acceso por Internet queda fuera de alcance.
- Si se necesita la API directamente en la LAN, `make serve` se niega salvo que `[server] host` sea no-loopback, `allow_lan = true` y exista secreto.

## 6. Biblioteca e ingesta

Desde la vista **Administración** de la interfaz (o `POST /api/v1/documents` con la cabecera `X-K9-Admin-Secret`) puedes subir PDF, reemplazar versiones, reindexar, desactivar, reactivar y eliminar.

Cada subida crea un trabajo persistente. El trabajador ejecuta extracción, OCR selectivo, fragmentación, embeddings (sólo de fragmentos nuevos, con caché por hash) y publicación atómica de un snapshot nuevo. Si algo falla, el snapshot anterior sigue activo y la versión candidata queda en `error`.

Para inspeccionar:

- `GET /api/v1/admin/traces?kind=ingestion&job_id=…`: tiempos por etapa, páginas, OCR, fragmentos, embeddings calculados y vectores reutilizados.
- `GET /api/v1/admin/metrics`: estados, abstención, latencia p50/p95, caché, rendimiento de ingesta y disponibilidad de modelos.
- `GET /api/v1/admin/health`: API, trabajador, SQLite, almacenamiento, snapshot, índice y modelos.

Para volver a un snapshot retenido, usa `POST /api/v1/admin/snapshots/{id}/rollback`. Se rechaza si su generación vectorial está incompleta o si contiene una fuente eliminada.

### Primera publicación con puertas de evaluación

Antes de publicar en el directorio servido, valida el corpus en uno de staging:

```bash
PYTHONPATH=backend/src .venv/bin/python scripts/stage_reference_corpus.py --data-dir /tmp/k9-staging
PYTHONPATH=backend/src .venv/bin/python -m k9_expert.evaluation run --experiment E2 --data-dir /tmp/k9-staging
```

Si se cumplen las puertas de `docs/evaluation/baseline-2026-11-01.md`, sube el mismo PDF a la instancia real o copia el directorio de staging como `data/` con los servicios detenidos.

## 7. Copias de seguridad y restauración

- **Crear:** `POST /api/v1/admin/backups` con `{"include_indexes": true}` para una restauración rápida. Sin índices también funciona, porque se reconstruyen desde SQLite y los PDF. La copia queda en `data/backups/<id>/` con manifiesto y hashes.
- **Restaurar:**
  1. Obtén el `created_at` de la copia con `GET /api/v1/admin/backups`.
  2. Pide un token: `POST /api/v1/admin/confirmations` con `{"resource_id": "<id>", "operation": "restore", "resource_version": "<created_at>"}`.
  3. Llama a `POST /api/v1/admin/backups/<id>/restore` con `{"confirmation_token": "…"}`.

  La restauración verifica hashes, reconcilia y reconstruye índices antes de reactivar las consultas. Mientras tanto, las consultas responden `unavailable` con el motivo `restore_in_progress`.
- Guarda copias fuera de la Mac: la carpeta `data/backups/` vive en el mismo disco.

## 8. Evaluación

```bash
make eval-e1    # generación sin RAG
make eval-e2    # RAG semántico contra el snapshot activo
```

Cada ejecución escribe `evaluation/runs/<run_id>.json` (manifiesto reproducible, métricas por caso y agregadas) y `<run_id>.review.csv`. Para la rúbrica humana, sigue `docs/evaluation/human-rubric-v1.md` e importa la hoja con `python -m k9_expert.evaluation score`.

## 9. Pruebas

```bash
make test lint typecheck                 # backend: unidad, arquitectura, migración, seguridad, copia/restauración, pipeline
make web-check web-test web-e2e          # frontend: lint, build, unidad y navegador (escritorio, iPhone, Android)
```

## 10. Diagnóstico de problemas

| Síntoma | Causa probable | Acción |
|---|---|---|
| Consultas `unavailable` / `model_unavailable` | Ollama detenido o modelo no descargado | `ollama ps`, `ollama pull …`; ver `inference` en `/admin/health` |
| Consultas `unavailable` / `no_active_snapshot` | Nada publicado todavía | Sube un PDF y revisa el trabajo |
| Trabajo en `error` con `full_reindex_required` | Cambió el modelo o la dimensión de embeddings | Restablece la configuración o reconstruye desde un directorio vacío |
| Trabajo en `error` con `model_unavailable` | Ollama cayó durante los embeddings | Arranca Ollama y reindexa el documento; la versión anterior siguió activa |
| Muchas abstenciones `weak_evidence` / `out_of_domain` | Umbral demasiado alto para otro modelo de embeddings | Recalibra `sufficiency_minimum_score` con E2 |
| Respuestas `unverified` / `invalid_citations` | El modelo citó evidencia no entregada | Esperado ocasionalmente; si es frecuente, evalúa otro modelo |
| `worker_heartbeat_stale` en salud | El trabajador no está corriendo | `make worker` |
| La UI del móvil no carga | `preview` sin `--host 0.0.0.0` o firewall de macOS | Revisa ambos; la API debe seguir en loopback |

## 11. Limitaciones conocidas

- **Puerta de citas no superada.** La precisión de cita sigue por debajo del 0.80 exigido (ver `docs/evaluation/model-selection-2026-11-02.md` y `docs/evaluation/acceptance-gates-v1.md`).
- **Fuentes en conflicto.** `llama3.2:3b` no señala discrepancias entre fuentes de forma fiable, aunque el sistema las verifica y las muestra si el modelo las declara.
- **Umbral de suficiencia.** Está calibrado con 15 preguntas y tiene un margen estrecho.
- **OCR.** Sin Tesseract instalado.
- **Páginas impresas.** No se detectan etiquetas de página impresa; las citas usan la página física del PDF.
- **Metadatos.** La clasificación por raza, grupo, función y apartado cubre 438 de 786 fragmentos del corpus de referencia; los fragmentos sin clasificación no entran en los filtros por raza (preferimos omitir a clasificar mal).
- **Coincidencia de BreedMatch.** Es por subcadena normalizada con detección simple de negación; un término ambiguo («muestra» también es verbo) puede producir coincidencias falsas. El informe muestra la cita para que el usuario la verifique.
- **Sin modelo de usuarios.** Un único secreto administrativo; las consultas son abiertas dentro de la red.
- **Contenido histórico.** Las respuestas son documentales e históricas; no sustituyen consejo veterinario actual.
