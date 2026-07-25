import { useState, useRef, useEffect } from 'react'
import { ChevronDown, LogOut, RotateCcw, Trash2, FileText, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useDocuments } from '../context/DocumentsContext'
import { authApi } from '../api'

export default function Topbar() {
  const { user, logout } = useAuth()
  const { documents, selected, selectedId, setSelectedId } = useDocuments()
  const [menuOpen, setMenuOpen] = useState(false)
  const [docMenuOpen, setDocMenuOpen] = useState(false)
  const menuRef = useRef(null)
  const docMenuRef = useRef(null)

  useEffect(() => {
    function onClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
      if (docMenuRef.current && !docMenuRef.current.contains(e.target)) setDocMenuOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  async function handleLogout() {
    await logout()
  }

  async function handleResetWorkspace() {
    if (!confirm('Reset workspace? This clears all documents, chat, and agent history — your account stays.')) return
    await authApi.resetWorkspace()
    window.location.reload()
  }

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-surface-border bg-surface/40 px-5 backdrop-blur-md">
      <div className="relative" ref={docMenuRef}>
        <button
          onClick={() => setDocMenuOpen((v) => !v)}
          className="flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm text-ink-muted hover:bg-surface-light hover:text-ink transition-colors"
        >
          <FileText size={15} strokeWidth={1.75} />
          <span className="max-w-[220px] truncate">{selected ? selected.filename : 'No document selected'}</span>
          <ChevronDown size={14} />
        </button>
        {docMenuOpen && (
          <div className="glass-card absolute left-0 top-full z-30 mt-1.5 w-72 p-1.5">
            {documents.length === 0 && <p className="px-3 py-2 text-xs text-ink-faint">No documents uploaded yet.</p>}
            {documents.map((doc) => (
              <button
                key={doc.id}
                onClick={() => {
                  setSelectedId(doc.id)
                  setDocMenuOpen(false)
                }}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                  doc.id === selectedId ? 'bg-teal/10 text-teal-bright' : 'text-ink-muted hover:bg-surface-light hover:text-ink'
                }`}
              >
                <FileText size={14} className="shrink-0" />
                <span className="truncate flex-1">{doc.filename}</span>
                <StatusDot status={doc.status} />
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-surface-light transition-colors"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-teal to-coral text-[11px] font-semibold text-void">
            {user?.username?.[0]?.toUpperCase() || <User size={13} />}
          </div>
          <span className="hidden text-sm text-ink sm:inline">{user?.username}</span>
          <ChevronDown size={14} className="text-ink-muted" />
        </button>

        {menuOpen && (
          <div className="glass-card absolute right-0 top-full z-30 mt-1.5 w-52 overflow-hidden p-1.5">
            <button
              onClick={handleResetWorkspace}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs text-ink-muted hover:bg-surface-light hover:text-ink transition-colors"
            >
              <RotateCcw size={14} /> Reset workspace
            </button>
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs text-coral-glow hover:bg-coral/10 transition-colors"
            >
              <LogOut size={14} /> Log out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}

function StatusDot({ status }) {
  const color =
    status === 'ready' ? 'bg-teal-bright' : status === 'failed' ? 'bg-coral' : 'bg-ink-faint animate-pulse'
  return <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
}
