# K9 Expert · Interfaz web

Interfaz de K9 BreedMatch, hecha con React 19, TypeScript y Vite. Para la instalación completa y el resto del sistema vea el [README principal](../README.md).

El navegador sólo habla con la API de la aplicación: Vite reenvía `/api` a `127.0.0.1:8000`, y la interfaz nunca conoce la dirección de Ollama ni abre SQLite. Muestra por tanto el almacén de datos de la API que esté en ese puerto.

## Requisitos

Node.js 22 (≥ 22.13) o 24. Para ver datos reales, la API debe estar en marcha (`make serve`, desde la raíz).

## Comandos

Se ejecutan desde `frontend/`:

```bash
npm ci                                 # instalar dependencias
npm run dev                            # desarrollo en http://127.0.0.1:5173
npm run build                          # comprobar tipos y generar dist/
npm run preview                        # servir dist/ en local
npm run lint                           # Oxlint
npm test                               # pruebas unitarias (Vitest y Testing Library)
npx playwright install chromium        # sólo la primera vez, para las pruebas de navegador
npm run test:e2e                       # Playwright: escritorio, iPhone y Android, con comprobaciones WCAG
```

Las pruebas unitarias y de navegador simulan la API, así que no necesitan el backend. Playwright levanta su propio servidor en el puerto 5174.

Para abrir la interfaz desde un móvil en la LAN vea `docs/operations/local-operations.md` §5.

## Vistas

La navegación usa el hash de la URL, sin biblioteca de rutas. Se definen en `src/App.tsx`:

| Ruta | Vista | Código |
|---|---|---|
| `#/analizar` (inicial) | Análisis de razas: asistente guiado y análisis documental avanzado | `src/features/breedmatch/` |
| `#/consultar` | Chat documental con citas | `src/features/chat/` |
| `#/biblioteca` | Documentos del corpus | `src/features/library/` |
| `#/administracion` | Operaciones con secreto administrativo | `src/features/admin/` |
| `#/sistema` | Estado de los componentes | `src/features/system/` |

## Estructura

```text
src/
  api/          cliente HTTP, tipos y hooks de la API
  components/   componentes compartidos
  features/     una carpeta por vista, más citations/ (citas y evidencia)
  test/         configuración y datos simulados de las pruebas
  labels.ts     textos en español de estados y resultados
e2e/            pruebas de Playwright y API simulada
```

## Configuración

| Variable | Efecto |
|---|---|
| `VITE_K9_GUIDED_RECOMMENDATION=false` | Oculta el asistente guiado y deja sólo el análisis avanzado. Vea `docs/operations/local-operations.md` §12. |
