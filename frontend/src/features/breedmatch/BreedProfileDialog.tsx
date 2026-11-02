import { useCallback, useState } from 'react'
import { useApi } from '../../api/hooks'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Modal } from '../../components/Modal'
import { useAsync } from '../../hooks'
import { pageLabel } from '../../labels'

/** Book text and photo for one breed; every paragraph shows the page it comes from. */
export function BreedProfileDialog({ breed, onClose }: { breed: string; onClose: () => void }) {
  const api = useApi()
  const load = useCallback(() => api.breedProfile(breed), [api, breed])
  const profile = useAsync(load)
  const [photoFailed, setPhotoFailed] = useState(false)
  const data = profile.data
  return (
    <Modal title={breed} onClose={onClose}>
      {profile.loading && <p aria-live="polite">Cargando ficha…</p>}
      {profile.error !== null && <ErrorNotice error={profile.error} onRetry={profile.reload} />}
      {data && (
        <div className="breed-profile">
          {data.photo_url && !photoFailed ? (
            <figure className="breed-photo">
              <img
                src={data.photo_url}
                alt={data.photo_caption ?? breed}
                onError={() => setPhotoFailed(true)}
              />
              <figcaption className="small muted">
                {data.photo_caption} · fotografía de la enciclopedia, pág. {data.photo_page}
              </figcaption>
            </figure>
          ) : (
            <p className="small muted">La biblioteca no incluye una fotografía identificada de esta raza.</p>
          )}
          {data.sections.map((section) => (
            <section key={section.heading} className="profile-section">
              <h3 className="section-label">{section.heading}</h3>
              <p>{section.text}</p>
              <p className="small muted">
                <cite>{section.citation.title}</cite>,{' '}
                {pageLabel(section.citation.physical_page, section.citation.printed_page_label)}
              </p>
            </section>
          ))}
        </div>
      )}
    </Modal>
  )
}
