## Context

El repositorio no contiene todavía aplicación ni especificaciones principales. Incluye dos referencias verificadas: una enciclopedia de 243 páginas con texto extraíble, fotografías y algunas páginas predominantemente gráficas, y una guía académica que organiza un producto de IA en diez capas cerradas y tres abiertas. La solución se ejecutará inicialmente en una Mac Apple Silicon con 16 GB, dentro de una red local y sin servicios comerciales de inferencia.

El sistema debe resolver dos flujos con perfiles diferentes: consultas interactivas y trabajos de ingesta potencialmente largos. Ambos compartirán contratos de dominio, persistencia, inferencia y observabilidad, pero la ingesta no debe bloquear el servicio de consultas. Los documentos pueden contener instrucciones maliciosas, afirmaciones históricas o recomendaciones desactualizadas; todo contenido recuperado se considera evidencia no confiable y atribuible a su fuente.

Los actores son el usuario que consulta y el administrador local que modifica la biblioteca. En el MVP no habrá un proveedor de identidad ni RBAC general, pero las mutaciones administrativas estarán protegidas porque el backend será accesible desde una red local.

## Goals / Non-Goals

**Goals:**

- Entregar una aplicación web y API local para consultas textuales fundamentadas sobre múltiples PDF.
- Mantener referencias estables a documento, versión y página, y abstenerse cuando la evidencia sea insuficiente.
- Incorporar y reemplazar documentos incrementalmente sin dejar un índice parcialmente publicado.
- Mantener separadas presentación, casos de uso, inferencia y persistencia mediante puertos reemplazables.
- Hacer observables y reproducibles la consulta, ingesta y evaluación.
- Operar con concurrencia conservadora y sin dependencia de APIs externas.
- Dejar puntos de extensión para recuperación híbrida y multimodalidad sin implementarlas como requisitos iniciales.

**Non-Goals:**

- Analizar fotografías, identificar razas o recuperar imágenes por similitud.
- Ofrecer diagnósticos veterinarios o presentar contenido histórico como recomendación vigente.
- Implementar una PWA, operación completa sin conexión del navegador o inferencia en el teléfono.
- Crear microservicios, alta disponibilidad distribuida, sincronización entre instalaciones o identidad empresarial.
- Entrenar o ajustar modelos para incorporar documentos.
- Garantizar objetivos de latencia antes de ejecutar benchmarks en el hardware objetivo.

## Decisions

### 1. Monolito modular con dos procesos de ejecución

El backend se implementará como monolito modular con una API FastAPI y un trabajador local independiente. El código se organizará en dominio, aplicación, puertos e infraestructura. La API coordinará consultas y registrará trabajos; el trabajador reclamará trabajos persistentes de ingesta con concurrencia inicial de uno.

Esta forma mantiene límites equivalentes a las 13 capas sin desplegar trece servicios. Un worker en proceso separado evita que extracción, OCR o embeddings bloqueen consultas y permite reinicios. Se descartan microservicios y un broker externo por complejidad operativa; las tareas en memoria de FastAPI se descartan porque se pierden ante reinicios.

### 2. Las 13 capas son límites lógicos, no unidades de despliegue

Presentación hablará sólo con servicios de aplicación. Orquestación ejecutará en orden barrera de entrada, caché exacta, router, construcción de contexto, gateway y barrera de salida. Las acciones administrativas pasarán por autorización y confirmación. Datos se expondrá mediante repositorios. Observabilidad, retroalimentación y evaluación serán servicios transversales que no introducirán dependencias desde dominio hacia infraestructura.

Una prueba de arquitectura verificará dependencias permitidas. Se evita adoptar inicialmente un framework de agentes u orquestación; el flujo explícito facilita depuración, evaluación y sustitución de componentes.

### 3. SQLite es la autoridad; archivos e índices son derivados o referenciados

SQLite almacenará documentos, versiones, páginas, fragmentos, trabajos, snapshots, conversaciones, respuestas, citas, feedback y metadatos de trazas. Los PDF y artefactos grandes se almacenarán bajo identificadores internos en un directorio administrado. El índice vectorial contendrá vectores y metadatos mínimos, pero no decidirá qué versión está activa.

La consulta capturará al inicio un `snapshot_id` activo desde SQLite y lo conservará durante toda la operación. Los IDs de fragmento y los hashes de contenido permitirán reconciliar los tres almacenes. Esta decisión ofrece transacciones locales y recuperación sencilla; guardar PDF como BLOB o usar el índice vectorial como fuente de verdad se descarta.

### 4. Ingesta por página con OCR selectivo y estructura conservada

Cada archivo se validará por firma, MIME, tamaño, integridad y hash. La extracción será página por página. Se aplicará OCR sólo cuando métricas como cobertura, densidad o calidad del texto indiquen que la extracción directa no es suficiente. Se conservarán página física, etiqueta impresa cuando se detecte, encabezados, ruta de sección y método de extracción.

Los fragmentos respetarán límites de sección y página; si abarcan más de una página registrarán todas las páginas cubiertas. El algoritmo y su versión formarán parte de la identidad del índice. Usar OCR completo por defecto se descarta por latencia y degradación potencial de páginas con texto válido.

### 5. Versiones candidatas y publicación atómica por snapshot

Una nueva versión se procesa como candidata. Sus fragmentos se escriben en una generación de índice no visible, se validan conteos, referencias, dimensiones y recuperabilidad, y sólo después una transacción de SQLite cambia el snapshot y versión activos. Tras la publicación se invalidan cachés dependientes. Si cualquier etapa falla, la candidata queda en error y la versión anterior sigue disponible.

Agregar o modificar un documento recalculará sólo su contenido y producirá un snapshot que reutiliza miembros vigentes de otros documentos. Cambiar modelo/dimensión de embeddings, normalización o una regla incompatible de fragmentación requerirá una generación completa.

### 6. RAG semántico con filtros y puertos para fusión híbrida

El MVP implementará recuperación semántica y filtros por documento, versión, categoría, raza y sección cuando existan metadatos. El puerto `Retriever` devolverá evidencia con puntuaciones, procedencia y motivos de inclusión, permitiendo añadir posteriormente un recuperador léxico y una estrategia de fusión sin alterar la orquestación.

El umbral, `top_k`, diversidad y presupuesto de contexto se configurarán y versionarán. No se asumirá que una puntuación vectorial aislada demuestra suficiencia; la decisión de abstención considerará cobertura y evidencia utilizable.

### 7. Inferencia encapsulada por aliases lógicos

Puertos independientes representarán generación textual y embeddings. Adaptadores de Ollama implementarán timeouts, comprobación de disponibilidad, versión de modelo, mediciones y errores tipados. El router usará aliases como `text-default` y `embedding-default`, nunca nombres físicos.

El modelo textual y el de embeddings se seleccionarán mediante un benchmark reproducible en español antes de congelar configuración. Llama 3.2 3B y EmbeddingGemma son candidatos, no decisiones normativas. No se implementará respaldo a una API externa porque contradiría la operación local.

### 8. Respuesta estructurada y verificación determinista de citas

El modelo producirá una estructura con respuesta, afirmaciones y referencias a IDs de evidencia entregados. La barrera de salida rechazará citas inexistentes, versiones inactivas o referencias fuera del conjunto recuperado. Si no puede construir una respuesta verificable devolverá un estado de abstención, no un error 500.

Las discrepancias se conservarán como posiciones separadas y atribuidas. Las respuestas sobre salud, alimentación o adiestramiento indicarán el carácter documental e histórico de la fuente cuando corresponda. No se confiará únicamente en que el prompt obligue al modelo a citar.

### 9. API REST versionada, SSE opcional y frontend sin acceso a infraestructura

React con TypeScript consumirá rutas `/api/v1` para consultas, documentos, trabajos, citas, conversaciones, feedback, salud y métricas. El frontend nunca recibirá credenciales ni direcciones de Ollama o del índice. El progreso podrá consultarse por polling; SSE podrá añadirse sin cambiar el modelo de trabajo.

Los errores tendrán `code`, `message`, `details`, `trace_id` y `retryable`. Los estados de dominio se expresarán en el cuerpo; una abstención válida responderá satisfactoriamente.

### 10. Administración local protegida sin plataforma de identidad

El backend se ligará por defecto a loopback y la exposición a LAN será configuración explícita. Las rutas mutables requerirán una sesión o secreto administrativo almacenado de forma segura. Las eliminaciones requerirán un token de confirmación de corta duración asociado al recurso y operación. Ollama y el índice permanecerán en loopback.

Esto evita introducir OAuth o RBAC completo, pero reconoce que una LAN no constituye autenticación. Las consultas de lectura podrán configurarse como abiertas dentro de la red.

### 11. Eliminación lógica primero y conservación de evidencia histórica

Desactivar un documento lo excluye de nuevos snapshots sin borrar artefactos. Eliminar requiere confirmación, retira el documento de nuevas consultas y programa limpieza física. Las respuestas históricas conservarán una instantánea mínima de la cita —identidad bibliográfica, página y extracto permitido— y marcarán la fuente como retirada; no dependerán de que el vector siga presente.

La política de retención y la autorización de conservar extractos deberán documentarse en configuración. No se eliminarán silenciosamente conversaciones al retirar una fuente.

### 12. Cachés versionadas y limitadas al MVP

Se implementarán caché de extracción, OCR y embeddings por hash, además de una caché exacta opcional de respuestas. Las claves incluirán snapshot, filtros, versiones de prompt, modelo y configuración de recuperación. Incorporar, desactivar o reemplazar fuentes invalidará las entradas afectadas.

La caché semántica se excluye porque podría cruzar filtros o snapshots y devolver una respuesta incorrecta. Las cachés son optimizaciones reconstruibles, no fuentes de verdad.

### 13. Observabilidad respetuosa de privacidad y evaluación por capas

Cada consulta e ingesta emitirá una traza estructurada con identificadores, versiones, ruta, etapas, tiempos, fragmentos, estado y errores. El texto completo de consultas y los archivos no se registrarán por defecto. La retención será configurable.

La evaluación separará recuperación, generación, citas, abstención y operación. Un dataset versionado tendrá preguntas, evidencia esperada y rúbricas revisadas manualmente. Los modelos no serán los únicos jueces de sus propias respuestas. E1 sin RAG y E2 semántico pertenecen al MVP; E3 híbrido se habilitará cuando exista el recuperador léxico.

### 14. Copias de seguridad y recuperación coherentes

Una copia local incluirá snapshot consistente de SQLite, PDF activos y manifiesto de artefactos. Los índices vectoriales y léxicos podrán incluirse para recuperación rápida, pero deberán poder reconstruirse desde archivos y metadatos. La restauración validará hashes y ejecutará reconciliación antes de habilitar consultas.

## Risks / Trade-offs

- [Un LLM pequeño puede incumplir el formato o citar mal] → Usar salida estructurada, verificación determinista, reintento limitado y benchmark de candidatos.
- [La extracción directa puede perder texto visual] → Medir calidad por página, OCR selectivo y revisión de muestras representativas.
- [SQLite, archivos e índice pueden divergir] → Publicación por snapshots, hashes, reconciliador y artefactos reconstruibles.
- [La indexación compite por memoria con consultas] → Worker con concurrencia uno, lotes limitados y política de pausa bajo presión.
- [Una puntuación semántica alta no garantiza respaldo] → Umbrales calibrados, evaluación de cobertura y abstención posterior.
- [La caché puede servir conocimiento obsoleto] → Claves versionadas e invalidación después de publicación.
- [Un documento puede contener prompt injection] → Tratar contenido como datos no confiables, delimitar contexto y no otorgar herramientas al generador.
- [La protección administrativa simple no cubre despliegue público] → Limitar a loopback/LAN y documentar que acceso por internet queda fuera de alcance.
- [Conservar extractos de fuentes retiradas tiene implicaciones legales] → Política configurable, minimización y validación de derechos de uso.
- [Ocho capacidades amplían el MVP] → Implementar cortes verticales y priorizar integridad, consulta y citas antes de UI avanzada.

## Migration Plan

1. Crear esquema y directorios locales vacíos; no existe información de aplicación que migrar.
2. Implementar y probar adaptadores falsos, contratos de dominio y persistencia antes de conectar modelos reales.
3. Ingerir la enciclopedia como primera versión candidata y validar páginas, fragmentos y citas sin publicarla.
4. Publicar el primer snapshot sólo después de superar validaciones y un conjunto mínimo de evaluación.
5. Habilitar consultas locales y después, de forma explícita, acceso por LAN.
6. Añadir la biblioteca administrativa y operaciones destructivas tras validar copias y restauración.

Para rollback, se mantiene el snapshot anterior y se cambia transaccionalmente el puntero activo. Las migraciones de esquema deberán ser aditivas o incluir respaldo previo. Los índices incompatibles se reconstruyen en una nueva generación, nunca se actualizan destructivamente en sitio.

## Open Questions

- ¿Qué LLM textual, cuantización y contexto ofrecen el mejor equilibrio en español en la Mac objetivo?
- ¿Qué modelo, dimensionalidad y prefijos de tarea producen mejor Recall@K sobre la enciclopedia?
- ¿ChromaDB embebido satisface filtros, snapshots y operación local o conviene otro índice tras el spike?
- ¿Cuáles son los límites iniciales de tamaño, páginas y duración de un trabajo?
- ¿Cuál es la política legal y temporal para conservar extractos de documentos eliminados?
- ¿La comparación estructurada de razas entra en el primer corte de UI o después de validar extracción de atributos?
- ¿Qué umbral de calidad dispara OCR y cómo se valida para páginas con diseños complejos?
