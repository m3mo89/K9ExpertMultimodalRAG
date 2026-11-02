import { useEffect, useRef, useState, type MouseEvent } from 'react'
import { AdminView } from './features/admin/AdminView'
import { BreedMatchView } from './features/breedmatch/BreedMatchView'
import { ChatView } from './features/chat/ChatView'
import { LibraryView } from './features/library/LibraryView'
import { SystemView } from './features/system/SystemView'

// BreedMatch is the primary product flow; chat, library and administration are secondary.
const routes = [
  { path: 'analizar', label: 'Análisis de razas', View: BreedMatchView },
  { path: 'consultar', label: 'Consultar', View: ChatView },
  { path: 'biblioteca', label: 'Biblioteca', View: LibraryView },
  { path: 'administracion', label: 'Administración', View: AdminView },
  { path: 'sistema', label: 'Sistema', View: SystemView },
] as const

type RoutePath = (typeof routes)[number]['path']

function currentRoute(): RoutePath {
  const path = window.location.hash.replace(/^#\/?/, '')
  return routes.find((route) => route.path === path)?.path ?? 'analizar'
}

export default function App() {
  const [route, setRoute] = useState<RoutePath>(currentRoute)

  useEffect(() => {
    const onHashChange = () => setRoute(currentRoute())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const active = routes.find((item) => item.path === route) ?? routes[0]
  const main = useRef<HTMLElement>(null)
  const focusedRoute = useRef(route)

  useEffect(() => {
    document.title = `${active.label} · K9 Expert`
    // Move focus to the new view after navigation, but leave the initial load untouched.
    if (focusedRoute.current !== active.path) {
      focusedRoute.current = active.path
      main.current?.focus({ preventScroll: true })
    }
  }, [active])

  // The hash is the router, so the skip link moves focus instead of changing the hash.
  const skipToContent = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault()
    main.current?.focus()
  }

  return (
    <div className="shell">
      <a className="skip-link" href="#main" onClick={skipToContent}>
        Saltar al contenido
      </a>
      <header className="topbar">
        <span className="brand" aria-label="K9 Expert">
          <span className="brand-mark" aria-hidden="true">
            K9
          </span>
          <span className="brand-name">Expert</span>
        </span>
        <nav aria-label="Principal">
          <ul className="nav-list">
            {routes.map((item) => (
              <li key={item.path}>
                <a
                  href={`#/${item.path}`}
                  className="nav-link"
                  aria-current={item.path === route ? 'page' : undefined}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main" ref={main} tabIndex={-1} className="main">
        <active.View />
      </main>
    </div>
  )
}
