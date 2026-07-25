import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Send, Sparkles, FileSearch, BrainCircuit, AlertCircle, X, Plus, ChevronDown, FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { chatApi } from '../api'
import { useDocuments } from '../context/DocumentsContext'

export default function ChatWindow() {
  const { documents, selected } = useDocuments()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [attachedId, setAttachedId] = useState(selected?.id || null)
  const [pickerOpen, setPickerOpen] = useState(false)
  const bottomRef = useRef(null)
  const pickerRef = useRef(null)

  const attachedDoc = documents.find((d) => d.id === attachedId) || null
  const readyDocs = documents.filter((d) => d.status === 'ready')

  // Keep the chat's attached document in sync when the topbar selection changes
  useEffect(() => {
    setAttachedId(selected?.id || null)
  }, [selected?.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    function onClickOutside(e) {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) setPickerOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  async function handleSend(e) {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)
    try {
      const { data } = await chatApi.ask(question, attachedId)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer, sources: data.sources }])
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="mb-3 flex items-center gap-2">
        <h1 className="font-display text-xl font-semibold text-ink">Chat</h1>
      </div>

      {/* Always-visible attach strip — this is how people discover that a
          document is optional: attach one to ask about it, or leave it off
          and ask anything, like a normal AI assistant. */}
      <div className="mb-4 flex items-center gap-2">
        {attachedDoc ? (
          <span className="chip border-teal/30 bg-teal/10 text-teal-bright">
            <FileSearch size={11} />
            {attachedDoc.filename}
            <button
              onClick={() => setAttachedId(null)}
              className="ml-1 rounded-full p-0.5 hover:bg-teal/20"
              aria-label="Detach document"
            >
              <X size={11} />
            </button>
          </span>
        ) : (
          <div className="relative" ref={pickerRef}>
            <button
              onClick={() => setPickerOpen((v) => !v)}
              className="chip border-dashed border-surface-border text-ink-faint hover:border-teal/40 hover:text-teal-bright transition-colors"
            >
              <Plus size={11} /> Attach a document
              <ChevronDown size={11} />
            </button>
            {pickerOpen && (
              <div className="glass-card absolute left-0 top-full z-20 mt-1.5 max-h-56 w-64 overflow-y-auto p-1.5">
                {readyDocs.length === 0 && (
                  <p className="px-3 py-2 text-xs text-ink-faint">No ready documents yet.</p>
                )}
                {readyDocs.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => {
                      setAttachedId(doc.id)
                      setPickerOpen(false)
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs text-ink-muted hover:bg-surface-light hover:text-ink"
                  >
                    <FileText size={13} className="shrink-0" />
                    <span className="truncate">{doc.filename}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {!attachedDoc && <span className="text-xs text-ink-faint">or just ask anything below</span>}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-ink-faint">
            <BrainCircuit size={28} strokeWidth={1.5} />
            <p className="text-sm">
              {attachedDoc
                ? `Ask anything about ${attachedDoc.filename}`
                : 'Ask me anything — attach a document above for questions about it specifically'}
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                msg.role === 'user'
                  ? 'bg-teal text-void font-medium'
                  : 'glass-card text-ink'
              }`}
            >
              {msg.role === 'assistant' ? (
                <div className="space-y-1.5 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
              {msg.sources?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 border-t border-surface-border pt-2">
                  {msg.sources.slice(0, 3).map((s, j) => (
                    <span key={j} className="chip border-surface-border bg-surface-light text-ink-faint">
                      <Sparkles size={10} /> Excerpt {j + 1}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="glass-card flex items-center gap-1.5 px-4 py-3">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-teal-bright"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSend} className="flex items-center gap-2 border-t border-surface-border pt-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={attachedDoc ? 'Ask about this document...' : 'Ask me anything...'}
          className="input-field flex-1"
        />
        <button type="submit" disabled={loading || !input.trim()} className="btn-primary shrink-0 px-3.5">
          <Send size={16} />
        </button>
      </form>
    </div>
  )
}