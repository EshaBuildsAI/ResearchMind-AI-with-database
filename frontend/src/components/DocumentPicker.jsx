import { useRef, useState } from 'react'
import { FileText, ChevronDown, Check, UploadCloud, Loader2 } from 'lucide-react'
import { useDocuments } from '../context/DocumentsContext'

/**
 * Props:
 *  - selectedIds: string[]
 *  - onChange: (newIds: string[]) => void
 *  - multiDoc: boolean — allow selecting more than one document
 *  - label: string
 */
export default function DocumentPicker({ selectedIds, onChange, multiDoc = false, label = 'Document' }) {
  const { documents, upload } = useDocuments()
  const [open, setOpen] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const readyDocs = documents.filter((d) => d.status === 'ready')
  const selectedDocs = documents.filter((d) => selectedIds.includes(d.id))

  function toggleDoc(docId) {
    if (multiDoc) {
      onChange(selectedIds.includes(docId) ? selectedIds.filter((id) => id !== docId) : [...selectedIds, docId])
    } else {
      onChange(selectedIds.includes(docId) ? [] : [docId])
      setOpen(false)
    }
  }

  async function handleUploadNew(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setUploading(true)
    try {
      const doc = await upload(file)
      // Auto-attach the freshly uploaded document once it's picked up —
      // it starts as 'uploaded'/'processing', so select it immediately;
      // the caller's document list will show its status updating live.
      onChange(multiDoc ? [...selectedIds, doc.id] : [doc.id])
      setOpen(false)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div className="relative">
      <label className="mb-1.5 block text-xs font-medium text-ink-muted">{label}</label>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="input-field flex items-center justify-between text-left"
      >
        <span className="flex items-center gap-2 truncate">
          <FileText size={14} className="shrink-0 text-ink-faint" />
          {selectedDocs.length === 0
            ? 'No document selected'
            : selectedDocs.length === 1
              ? selectedDocs[0].filename
              : `${selectedDocs.length} documents selected`}
        </span>
        <ChevronDown size={14} className="shrink-0 text-ink-faint" />
      </button>

      {open && (
        <div className="glass-card absolute left-0 top-full z-20 mt-1.5 max-h-64 w-full overflow-y-auto p-1.5">
          {!multiDoc && selectedIds.length > 0 && (
            <button
              type="button"
              onClick={() => {
                onChange([])
                setOpen(false)
              }}
              className="flex w-full items-center rounded-lg px-3 py-2 text-left text-xs text-ink-muted hover:bg-surface-light hover:text-ink"
            >
              None — clear selection
            </button>
          )}

          {readyDocs.map((doc) => (
            <button
              key={doc.id}
              type="button"
              onClick={() => toggleDoc(doc.id)}
              className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs ${
                selectedIds.includes(doc.id) ? 'bg-teal/10 text-teal-bright' : 'text-ink-muted hover:bg-surface-light hover:text-ink'
              }`}
            >
              {multiDoc && (
                <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                  selectedIds.includes(doc.id) ? 'border-teal bg-teal text-void' : 'border-surface-border'
                }`}>
                  {selectedIds.includes(doc.id) && <Check size={11} />}
                </span>
              )}
              <FileText size={13} className="shrink-0" />
              <span className="truncate">{doc.filename}</span>
            </button>
          ))}

          <div className="my-1.5 border-t border-surface-border" />

          <input
            ref={inputRef}
            type="file"
            className="hidden"
            accept=".pdf,.docx,.pptx,.xlsx,.txt"
            onChange={handleUploadNew}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-medium text-teal-bright hover:bg-teal/10"
          >
            {uploading ? <Loader2 size={13} className="animate-spin" /> : <UploadCloud size={13} />}
            {uploading ? 'Uploading...' : 'Upload a new document'}
          </button>

          {multiDoc && readyDocs.length > 0 && (
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="mt-1 w-full rounded-lg bg-teal/10 px-3 py-2 text-center text-xs font-medium text-teal-bright"
            >
              Done
            </button>
          )}
        </div>
      )}

      {error && <p className="mt-1.5 text-xs text-coral-glow">{error}</p>}
    </div>
  )
}