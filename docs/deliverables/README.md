# Entregables académicos de K9 BreedMatch

## Archivos finales

- `final/K9-BreedMatch-Presentacion.pptx`: presentación editable, 12 diapositivas y notas del presentador.
- `final/K9-BreedMatch-Presentacion.pdf`: copia renderizada para revisión y plan B.
- `final/K9-BreedMatch-Informe-Tecnico.docx`: informe editable, 19 páginas en la exportación de control.
- `final/K9-BreedMatch-Informe-Tecnico.pdf`: copia de control lista para lectura.

Los archivos en `preview/` son imágenes de verificación, no entregables principales. Los recursos gráficos reutilizables están en `assets/`. La fuente narrativa y la matriz de evidencia están en `source/`.

## Campos que debe completar el alumno

Antes de entregar, sustituir en PowerPoint y Word:

- `[NOMBRE DEL ALUMNO]`
- `[INSTITUCIÓN]`
- `[NOMBRE DEL DOCENTE]`

Opcionalmente, agregar logotipo institucional y datos de grupo o matrícula. Después de editar el Word, actualizar el PDF final.

## Guion de demostración

1. Ejecutar el preflight y mostrar el estado local.
2. Completar presa, modalidad y terreno.
3. Mostrar recomendación, compatibilidad, cobertura y evidencia.
4. Repetir la petición y mostrar el acierto de caché.
5. Enviar una entrada con inyección y mostrar el bloqueo.
6. Ejecutar un caso que active la reformulación del agente.
7. Registrar retroalimentación y abrir métricas y OpenAPI.

Plan B: conservar el PDF de la presentación y un video o capturas del ensayo. El plan B no sustituye la demostración local evaluada.

## Limitaciones que deben mencionarse

- Ningún LLM superó la puerta G1 de precisión de citas del chat.
- La revisión humana de calidad y la firma de datasets siguen pendientes.
- La recomendación no ha sido validada por especialistas caninos independientes.
- Debe confirmarse el permiso de uso académico del corpus.
- Falta documentar el ensayo final completamente sin conexión.
- BGE-M3 se comparó por recuperación; el umbral de suficiencia de Nomic no es transferible.

## Regeneración

```bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/k9-mpl XDG_CACHE_HOME=/tmp/k9-cache \
  .venv/bin/python scripts/generate_academic_deliverables.py
```

La exportación PDF de control se realizó con Microsoft PowerPoint y Microsoft Word instalados localmente.
