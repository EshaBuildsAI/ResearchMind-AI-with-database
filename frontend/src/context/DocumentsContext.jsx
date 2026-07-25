import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { documentsApi } from '../api'

const DocumentsContext = createContext(null)

export function DocumentsProvider({ children }) {
  const [documents, setDocuments] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const pollRef = useRef(null)

  const refresh = useCallback(async () => {
    const { data } = await documentsApi.list()
    setDocuments(data)
    return data
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  // Poll while any document is uploaded/processing so status badges update live.
  useEffect(() => {
    const hasPending = documents.some((d) => d.status === 'uploaded' || d.status === 'processing')
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(refresh, 2500)
    } else if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [documents, refresh])

  const upload = useCallback(
    async (file, onProgress) => {
      const { data } = await documentsApi.upload(file, onProgress)
      setDocuments((prev) => [data, ...prev])
      setSelectedId(data.id)
      return data
    },
    []
  )

  const remove = useCallback(
    async (id) => {
      await documentsApi.delete(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
      setSelectedId((prev) => (prev === id ? null : prev))
    },
    []
  )

  const selected = documents.find((d) => d.id === selectedId) || null

  return (
    <DocumentsContext.Provider
      value={{ documents, selected, selectedId, setSelectedId, loading, upload, remove, refresh }}
    >
      {children}
    </DocumentsContext.Provider>
  )
}

export function useDocuments() {
  const ctx = useContext(DocumentsContext)
  if (!ctx) throw new Error('useDocuments must be used within DocumentsProvider')
  return ctx
}
