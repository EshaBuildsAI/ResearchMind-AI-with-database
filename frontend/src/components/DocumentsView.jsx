import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { UploadCloud, FileText, Trash2, CheckCircle2, Loader2, XCircle, Clock } from 'lucide-react'
import { useDocuments } from '../context/DocumentsContext'

const STATUS_CONFIG = {
  uploaded: { icon: Clock, label: 'Queued', className: 'text-ink-muted border-ink-faint/30 bg-surface-light' },
  processing: { icon: Loader2, label: 'Processing', className: 'text-teal-bright border-teal/30 bg-teal/10', spin: true },
  ready: { icon: CheckCircle2, label: 'Ready', className: 'text-teal-bright border-teal/40 bg-teal/10' },
  failed: { icon: XCircle, label: 'Failed', className: 'text-coral-glow border-coral/40 bg-coral/10' },
}

export default function DocumentsView() {
  const { documents, upload, remove, selectedId, setSelectedId } = useDocuments()
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const inputRef = useRef(null)

  const handleFiles = useCallback(
    async (files) => {
      const file = files?.[0]
      if (!file) return
      setUploadError('')
      setUploading(true)
      try {
        await upload(file)
      } catch (err) {
        setUploadError(err.response?.data?.detail || 'Upload failed. Please try again.')
      } finally {
        setUploading(false)
      }
    },
    [upload]
  )

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-xl font-semibold text-ink">Documents</h1>
        <p className="mt-1 text-sm text-ink-muted">Upload PDF, DOCX, PPTX, XLSX, or TXT — up to 50MB.</p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragActive(false)
          handleFiles(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        className={`glass-card flex cursor-pointer flex-col items-center justify-center gap-3 border-dashed py-14 text-center transition-colors ${
          dragActive ? 'border-teal bg-teal/5' : 'hover:border-teal/40'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.pptx,.xlsx,.txt"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal/10">
          {uploading ? (
            <Loader2 size={22} className="animate-spin text-teal-bright" />
          ) : (
            <UploadCloud size={22} className="text-teal-bright" strokeWidth={1.75} />
          )}
        </div>
        <p className="text-sm text-ink">
          {uploading ? 'Uploading...' : (
            <>
              <span className="font-medium text-teal-bright">Click to upload</span> or drag and drop
            </>
          )}
        </p>
        <p className="text-xs text-ink-faint">PDF · DOCX · PPTX · XLSX · TXT</p>
      </div>

      {uploadError && (
        <div className="rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
          {uploadError}
        </div>
      )}

      <div className="space-y-2">
        <AnimatePresence initial={false}>
          {documents.map((doc) => {
            const config = STATUS_CONFIG[doc.status] || STATUS_CONFIG.uploaded
            const StatusIcon = config.icon
            const isSelected = doc.id === selectedId
            return (
              <motion.div
                key={doc.id}
                layout
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onClick={() => setSelectedId(doc.id)}
                className={`glass-card flex cursor-pointer items-center gap-3 px-4 py-3 transition-colors ${
                  isSelected ? 'border-teal/50' : 'hover:border-surface-border'
                }`}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-light">
                  <FileText size={16} className="text-ink-muted" strokeWidth={1.75} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-ink">{doc.filename}</p>
                  {doc.status === 'failed' && doc.error_message && (
                    <p className="truncate text-xs text-coral-glow/80">{doc.error_message}</p>
                  )}
                  {doc.status === 'ready' && (
                    <p className="text-xs text-ink-faint">{doc.chunk_count} chunks indexed</p>
                  )}
                </div>
                <span className={`chip ${config.className}`}>
                  <StatusIcon size={11} className={config.spin ? 'animate-spin' : ''} />
                  {config.label}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    remove(doc.id)
                  }}
                  className="icon-btn h-8 w-8 hover:text-coral"
                  aria-label="Delete document"
                >
                  <Trash2 size={15} strokeWidth={1.75} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {documents.length === 0 && (
          <p className="py-8 text-center text-sm text-ink-faint">No documents yet — upload one to get started.</p>
        )}
      </div>
    </div>
  )
}
