import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Archive, Download, Eye, ImagePlus, Loader2, Upload } from 'lucide-react'

import { api, ApiError } from '@/services/api'
import type { MediaAttachment } from '@/types'

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('Não foi possível ler o ficheiro selecionado.'))
    reader.readAsDataURL(file)
  })
}

function readableSize(value: number) {
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${value} B`
}

export function MediaAttachmentPanel({ entityType, entityId, canManage, title = 'Fotos e anexos' }: { entityType: string; entityId: string; canManage: boolean; title?: string }) {
  const [items, setItems] = useState<MediaAttachment[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      setItems(await api.mediaAttachments(entityType, entityId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível carregar anexos.')
    }
  }, [entityType, entityId])

  useEffect(() => {
    void load()
    return () => {
      setPreview(current => {
        if (current?.url) URL.revokeObjectURL(current.url)
        return null
      })
    }
  }, [load])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const file = form.get('file')
    if (!(file instanceof File) || !file.size) {
      setError('Selecione uma fotografia ou documento.')
      return
    }
    setBusy(true)
    try {
      setError(null)
      await api.createMediaAttachment(entityType, entityId, {
        title: String(form.get('title') || file.name),
        category: String(form.get('category') || 'photo'),
        caption: String(form.get('caption') || ''),
        file_name: file.name,
        file_data_url: await fileToDataUrl(file),
      })
      event.currentTarget.reset()
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível guardar o anexo.')
    } finally {
      setBusy(false)
    }
  }

  async function openPreview(item: MediaAttachment) {
    try {
      setError(null)
      const url = await api.previewMediaAttachment(item.id)
      setPreview(current => {
        if (current?.url) URL.revokeObjectURL(current.url)
        return { title: item.title, url }
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível pré-visualizar o anexo.')
    }
  }

  async function archiveItem(item: MediaAttachment) {
    setBusy(true)
    try {
      setError(null)
      await api.archiveMediaAttachment(item.id)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Não foi possível arquivar o anexo.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="media-panel">
      <header>
        <span><ImagePlus /></span>
        <div>
          <h3>{title}</h3>
          <p>{items.length} anexo{items.length === 1 ? '' : 's'} registado{items.length === 1 ? '' : 's'} nesta entidade.</p>
        </div>
      </header>
      {error && <div className="media-error">{error}</div>}
      {canManage && (
        <form onSubmit={submit}>
          <label><span>Título</span><input name="title" placeholder="Ex.: Foto frontal, BI, relatório assinado" /></label>
          <label><span>Categoria</span><select name="category" defaultValue="photo"><option value="photo">Fotografia</option><option value="document">Documento</option><option value="evidence">Evidência</option><option value="signature">Assinatura</option><option value="other">Outro</option></select></label>
          <label><span>Legenda</span><input name="caption" placeholder="Descrição curta do anexo" /></label>
          <label><span>Ficheiro</span><input name="file" type="file" accept="image/png,image/jpeg,image/webp,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required /></label>
          <button className="module-primary-button" disabled={busy}>{busy ? <Loader2 /> : <Upload />} Guardar anexo</button>
        </form>
      )}
      <div className="media-list">
        {items.map(item => (
          <article key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <small>{item.file_name} · {readableSize(item.file_size)} · {item.category}</small>
              <code>{item.checksum_sha256.slice(0, 16)}</code>
            </div>
            <footer>
              <button type="button" onClick={() => void openPreview(item)}><Eye /> Ver</button>
              <button type="button" onClick={() => void api.downloadMediaAttachment(item.id, item.file_name)}><Download /> Baixar</button>
              {canManage && <button type="button" onClick={() => void archiveItem(item)}><Archive /> Arquivar</button>}
            </footer>
          </article>
        ))}
        {!items.length && <p className="media-empty">Sem anexos ainda.</p>}
      </div>
      {preview && (
        <div className="media-preview" role="dialog" aria-modal="true" aria-label={`Pré-visualização ${preview.title}`}>
          <button type="button" onClick={() => setPreview(current => { if (current?.url) URL.revokeObjectURL(current.url); return null })} aria-label="Fechar pré-visualização" />
          <section>
            <header><strong>{preview.title}</strong><button type="button" onClick={() => setPreview(current => { if (current?.url) URL.revokeObjectURL(current.url); return null })}>Fechar</button></header>
            <iframe src={preview.url} title={preview.title} />
          </section>
        </div>
      )}
    </section>
  )
}
