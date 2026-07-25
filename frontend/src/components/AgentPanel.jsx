import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import {
  X, Check, Loader2, CircleDashed, XCircle, FileSearch, Globe, Sparkles,
  ExternalLink, Quote, ListChecks, Clock, Lightbulb, Compass, Telescope, Link2, Trash2,
} from 'lucide-react'
import { useAgentPanel } from '../context/AgentPanelContext'
import { useDocuments } from '../context/DocumentsContext'
import { useState } from 'react'
import { getAccessToken } from '../api/client'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function viewSourceUrl(docId) {
  const token = getAccessToken()
  return `${API_BASE_URL}/documents/${docId}/file?token=${encodeURIComponent(token || '')}`
}

const AGENT_META = {
  research: { label: 'Research Agent', icon: Telescope },
  planner: { label: 'Planner Agent', icon: Compass },
  recommendation: { label: 'Recommendation Agent', icon: ListChecks },
  timeline: { label: 'Timeline Agent', icon: Clock },
  innovation: { label: 'Innovation Agent', icon: Lightbulb },
  citation: { label: 'Citation Agent', icon: Quote },
  summarize_reference: { label: 'Link Summarizer', icon: Link2 },
}

const STEP_ICON = { done: Check, running: Loader2, pending: CircleDashed, failed: XCircle }

function StepStatusIcon({ status }) {
  const Icon = STEP_ICON[status] || CircleDashed
  const colorClass =
    status === 'done' ? 'bg-teal text-void' : status === 'failed' ? 'bg-coral text-void' : 'bg-surface-light text-ink-faint'
  return (
    <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${colorClass}`}>
      <Icon size={12} className={status === 'running' ? 'animate-spin' : ''} strokeWidth={2.5} />
    </div>
  )
}

function PaperCard({ paper, onSummarize }) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-light/60 p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium leading-snug text-ink">{paper.title}</p>
        {paper.url && (
          <a href={paper.url} target="_blank" rel="noreferrer" className="shrink-0 text-ink-faint hover:text-teal-bright">
            <ExternalLink size={13} />
          </a>
        )}
      </div>
      <div className="mt-1.5 flex items-center gap-1.5">
        <span className="chip border-surface-border bg-surface text-[10px] text-ink-faint">{paper.source}</span>
        {paper.year && <span className="text-[10px] text-ink-faint">{paper.year}</span>}
      </div>
      {paper.snippet && <p className="mt-1.5 line-clamp-2 text-[11px] text-ink-muted">{paper.snippet}</p>}
      {paper.url && onSummarize && (
        <button
          onClick={() => onSummarize(paper.url)}
          className="mt-2 flex items-center gap-1 text-[11px] font-medium text-teal-bright hover:underline"
        >
          <Sparkles size={11} /> Summarize this
        </button>
      )}
    </div>
  )
}

function StepDetail({ step, onSummarize }) {
  const detail = step.detail
  if (!detail) return null

  if (Array.isArray(detail.papers) && detail.papers.length > 0) {
    return (
      <div className="mt-2 grid gap-2">
        {detail.papers.map((p, i) => (
          <PaperCard key={i} paper={p} onSummarize={onSummarize} />
        ))}
      </div>
    )
  }
  if (typeof detail.chunks_found === 'number') {
    return <p className="mt-1 text-xs text-ink-faint">{detail.chunks_found} relevant passage(s) found.</p>
  }
  if (Array.isArray(detail.citations)) {
    return (
      <div className="mt-2 space-y-2">
        {detail.citations.map((c, i) => (
          <div key={i} className="rounded-lg border border-surface-border bg-surface-light/60 p-2.5">
            <div className="mb-1 flex items-center gap-2">
              {c.page && <span className="chip border-teal/30 bg-teal/10 text-[10px] text-teal-bright">Page {c.page}</span>}
              {c.confidence != null && <span className="text-[10px] text-ink-faint">{c.confidence}% match</span>}
            </div>
            <p className="line-clamp-2 text-[11px] text-ink-muted">{c.text}</p>
            {c.doc_id && (
              <a
                href={viewSourceUrl(c.doc_id)}
                target="_blank"
                rel="noreferrer"
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-teal-bright hover:underline"
              >
                <ExternalLink size={11} /> View source{c.filename ? ` (${c.filename})` : ''}
              </a>
            )}
          </div>
        ))}
      </div>
    )
  }
  return null
}

function ResultBody({ run }) {
  if (run.result_text) {
    return (
      <div className="space-y-1.5 text-sm text-ink [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4">
        <ReactMarkdown>{run.result_text}</ReactMarkdown>
      </div>
    )
  }
  const result = run.result
  if (!result) return null
  const text = result.recommendations || result.timeline || result.ideas || result.answer || result.gaps
  if (text) {
    return (
      <div className="space-y-1.5 text-sm text-ink [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    )
  }
  return null
}

export default function AgentPanel() {
  const { isOpen, isRunning, currentRun, error, closePanel, summarizeReference, deleteCurrentRun } = useAgentPanel()
  const { selectedId } = useDocuments()
  const [subSummary, setSubSummary] = useState(null)
  const [subLoading, setSubLoading] = useState(false)

  if (!isOpen) return null

  const meta = AGENT_META[currentRun?.agent_type] || { label: 'Agent', icon: Sparkles }
  const Icon = meta.icon

  async function handleSummarize(url) {
    setSubLoading(true)
    setSubSummary(null)
    try {
      const run = await summarizeReference(url, '', selectedId)
      setSubSummary({ url, text: run.result_text })
    } catch {
      setSubSummary({ url, text: "Couldn't summarize that link." })
    } finally {
      setSubLoading(false)
    }
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closePanel}
            className="fixed inset-0 z-40 bg-void/40 backdrop-blur-[2px] md:hidden"
          />
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 250 }}
            className="fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l border-surface-border bg-surface/95 backdrop-blur-xl sm:w-[420px]"
          >
            <div className="flex items-center justify-between border-b border-surface-border px-5 py-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal/10">
                  <Icon size={16} className="text-teal-bright" strokeWidth={1.75} />
                </div>
                <div>
                  <p className="text-sm font-medium text-ink">{meta.label}</p>
                  <p className="line-clamp-1 text-[11px] text-ink-faint">{currentRun?.question}</p>
                </div>
              </div>
              <button onClick={closePanel} className="icon-btn h-8 w-8">
                <X size={16} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4">
              {error && (
                <div className="mb-4 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
                  {error}
                </div>
              )}

              {isRunning && !currentRun?.steps?.length && (
                <div className="flex items-center gap-2 text-xs text-ink-muted">
                  <Loader2 size={14} className="animate-spin text-teal-bright" />
                  Starting agent pipeline...
                </div>
              )}

              {/* Result comes FIRST — the substantive answer, not the links */}
              {currentRun?.status === 'done' && (
                <div className="mb-5">
                  <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
                    <FileSearch size={12} /> Answer
                  </div>
                  <ResultBody run={currentRun} />
                </div>
              )}

              {/* Inline link-summarize result */}
              {(subLoading || subSummary) && (
                <div className="mb-5 rounded-xl border border-teal/30 bg-teal/5 p-3">
                  <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium text-teal-bright">
                    <Globe size={12} /> Link summary
                  </div>
                  {subLoading ? (
                    <div className="flex items-center gap-2 text-xs text-ink-muted">
                      <Loader2 size={13} className="animate-spin" /> Fetching and summarizing...
                    </div>
                  ) : (
                    <p className="text-xs text-ink-muted">{subSummary.text}</p>
                  )}
                </div>
              )}

              {/* Steps + reference/source cards come AFTER the answer */}
              <div className="space-y-0 border-t border-surface-border pt-4">
                <p className="mb-3 text-[11px] font-medium uppercase tracking-wide text-ink-faint">Sources &amp; steps</p>
                {(currentRun?.steps || []).map((step, i) => (
                  <div key={i} className="relative flex gap-3 pb-5 last:pb-0">
                    {i < (currentRun.steps.length - 1) && (
                      <div className="absolute left-[9px] top-5 h-full w-px bg-surface-border" />
                    )}
                    <StepStatusIcon status={step.status} />
                    <div className="flex-1 pt-0.5">
                      <p className="text-xs font-medium text-ink">{step.label}</p>
                      <StepDetail step={step} onSummarize={handleSummarize} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Delete/clear this run — right here, not buried in a history list */}
              {currentRun && !isRunning && (
                <button
                  onClick={deleteCurrentRun}
                  className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-coral/25 px-4 py-2.5 text-xs font-medium text-coral-glow hover:bg-coral/10 transition-colors"
                >
                  <Trash2 size={13} /> Delete this result
                </button>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}