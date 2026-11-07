# Validación de entregables

Fecha de control: 6 de noviembre de 2026, zona horaria America/Mexico_City.

## Resultado estructural

- Presentación: 12 diapositivas, formato 16:9 y notas en las 12.
- Informe: 19 páginas en la exportación PDF, 14 encabezados de primer nivel, 11 tablas y 11 figuras.
- Diagramas obligatorios: contexto, contenedores, capas, componentes, despliegue, ingesta, consulta normal, caché, bloqueo y agente.
- Ambos archivos editables abrieron y fueron exportados por Microsoft Office sin advertencias de corrupción.

## Resultado visual

Se renderizaron todas las diapositivas y páginas. La revisión de las hojas de contacto no mostró recortes, desbordamientos importantes ni imágenes faltantes. Las tablas comparativas tienen contraste alto y los diagramas del informe conservan leyendas y fuentes.

## Consistencia y trazabilidad

- Recall@5: 0.925 para Nomic y BGE-M3.
- Hit@5: 0.950 para Nomic y BGE-M3.
- MRR: 0.808 para Nomic y 0.825 para BGE-M3.
- Precisión de cita: 0.634 para Llama y 0.708 para Qwen; ambos se etiquetan como provisionales.
- Nomic permanece seleccionado por tiempo y tamaño, sin ocultar la mejora marginal de BGE-M3 en Recall@1 y MRR.
- La observación 13.3 s → 20 ms se presenta como ensayo, no como promedio experimental.

Las fuentes de cada cifra están en `source/evidence.md`.

## Revisión final del alumno

- Completar los datos personales de portada.
- Confirmar licencia o permiso del corpus.
- Actualizar la revisión humana si se completa antes de entregar.
- Ensayar el guion con los modelos descargados y el índice preparado.
- Volver a exportar PDF si se modifica el Word o el PowerPoint.
