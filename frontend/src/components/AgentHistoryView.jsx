import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Compass, Telescope, ListChecks, Clock, Lightbulb, Quote, Link2, Sparkles,
  Trash2, CheckCircle2, XCircle, Loader2,
} from 'lucide-react'
import { agentsApi } from '../api'
import { useAgentPanel } from '../context/AgentPanelContext'

const AGENT_META = {
  research: { label: 'Research Agent', icon: Telescope },
  planner: { label: 'Planner Agent', icon: Compass },
  recommendation: { label: 'Recommendation Agent', icon: ListChecks },
  timeline: { label: 'Timeline Agent', icon: Clock },
  innovation: { label: 'Innovation Agent', icon: Lightbulb },
  citation: { label: 'Citation Agent', icon: Quote },
  summarize_reference: { label: 'Link Summarizer', icon: Link2 },
}

const STATUS_ICON = { done: CheckCircle2, failed: XCircle, running: Loader2 }

export default function AgentHistoryView() {
  const { reopenRun } = useAgentPanel()
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
  }, [])

  async function load() {
    setLoading(true)
    try {
      const { data } = await agentsApi.listRuns()
      setRuns(data)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(e, runId) {
    e.stopPropagation()
    await agentsApi.deleteRun(runId)
    setRuns((prev) => prev.filter((r) => r.id !== runId))
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-5">
        <h1 className="font-display text-xl font-semibold text-ink">Agent History</h1>
        <p className="mt-1 text-sm text-ink-muted">Every past agent run — click one to reopen it in the side panel.</p>
      </div>

      {loading && <p className="text-sm text-ink-faint">Loading...</p>}
      {!loading && runs.length === 0 && (
        <p className="py-10 text-center text-sm text-ink-faint">No agent runs yet — try one from the sidebar.</p>
      )}

      <div className="space-y-2">
        <AnimatePresence initial={false}>
          {runs.map((run) => {
            const meta = AGENT_META[run.agent_type] || { label: run.agent_type, icon: Sparkles }
            const Icon = meta.icon
            const StatusIcon = STATUS_ICON[run.status] || Loader2
            return (
              <motion.button
                key={run.id}
                layout
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onClick={() => reopenRun(run)}
                className="glass-card flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:border-teal/40"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal/10">
                  <Icon size={16} className="text-teal-bright" strokeWidth={1.75} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-ink">{meta.label}</p>
                  <p className="truncate text-xs text-ink-faint">{run.question || '(no question)'}</p>
                </div>
                <span
                  className={`flex items-center gap-1 text-xs ${
                    run.status === 'done' ? 'text-teal-bright' : run.status === 'failed' ? 'text-coral-glow' : 'text-ink-faint'
                  }`}
                >
                  <StatusIcon size={13} className={run.status === 'running' ? 'animate-spin' : ''} />
                </span>
                <button
                  onClick={(e) => handleDelete(e, run.id)}
                  className="icon-btn h-8 w-8 hover:text-coral"
                  aria-label="Delete run"
                >
                  <Trash2 size={14} strokeWidth={1.75} />
                </button>
              </motion.button>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}
