import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { motion } from 'framer-motion'
import { FileText, HelpCircle, Layers, BookOpen, SearchCode, Presentation as PresentationIcon,
  GraduationCap, AlertCircle, Sparkles, Check, X, RotateCw, Download } from 'lucide-react'
import { featuresApi } from '../api'
import { getAccessToken } from '../api/client'
import DocumentPicker from './DocumentPicker'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const TOOL_INFO = {
  'tool-summary': { title: 'Smart Summary', icon: FileText, desc: 'Get a structured summary — from your document, or just a topic.', placeholder: 'e.g. "Photosynthesis"' },
  'tool-quiz': { title: 'AI Quiz', icon: HelpCircle, desc: 'Auto-generated questions — from your document, or just a topic.', placeholder: 'e.g. "CNN"' },
  'tool-flashcards': { title: 'Flashcards', icon: Layers, desc: 'Study key concepts — from your document, or just a topic.', placeholder: 'e.g. "World War 2"' },
  'tool-literature': { title: 'Literature Review', icon: BookOpen, desc: 'Auto-generate a review section — from your document, or just a topic.', placeholder: 'e.g. "Transformer architectures"' },
  'tool-gap': { title: 'Research Gap Finder', icon: SearchCode, desc: 'Find missing topics & limitations — from your document, or just a topic.', placeholder: 'e.g. "Reinforcement learning"' },
  'tool-presentation': { title: 'Presentation Studio', icon: PresentationIcon, desc: 'A fully designed, downloadable .pptx deck — from your document, or just a topic.', placeholder: 'e.g. "Climate change"' },
  'tool-proposal': { title: 'Proposal Generator', icon: GraduationCap, desc: 'Draft a BS/MS proposal — from your document, or just a topic.', placeholder: 'e.g. "Machine learning in healthcare"' },
}

export default function FeatureView({ toolId }) {
  const info = TOOL_INFO[toolId]
  const [selectedIds, setSelectedIds] = useState([])
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const Icon = info.icon
  const documentId = selectedIds[0] || null

  async function handleGenerate() {
    if (!documentId && !topic.trim()) {
      setError('Select a document, enter a topic, or both.')
      return
    }
    setError('')
    setLoading(true)
    setResult(null)
    try {
      let data
      const t = topic.trim() || undefined
      switch (toolId) {
        case 'tool-summary':
          data = (await featuresApi.summary(documentId, 'medium', t)).data
          break
        case 'tool-quiz':
          data = (await featuresApi.quiz(documentId, 5, t)).data
          break
        case 'tool-flashcards':
          data = (await featuresApi.flashcards(documentId, 10, t)).data
          break
        case 'tool-literature':
          data = (await featuresApi.literatureReview(documentId, t)).data
          break
        case 'tool-gap':
          data = (await featuresApi.researchGap(documentId, t)).data
          break
        case 'tool-presentation':
          data = (await featuresApi.presentation(documentId, 8, t)).data
          break
        case 'tool-proposal':
          data = (await featuresApi.proposal(documentId, 'BS', '', t)).data
          break
      }
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal/10">
          <Icon size={18} className="text-teal-bright" strokeWidth={1.75} />
        </div>
        <div>
          <h1 className="font-display text-lg font-semibold text-ink">{info.title}</h1>
          <p className="text-xs text-ink-muted">{info.desc}</p>
        </div>
      </div>

      {!result && (
        <div className="glass-card space-y-4 p-6">
          <DocumentPicker selectedIds={selectedIds} onChange={setSelectedIds} multiDoc={false} label="Document (optional — or upload a new one)" />

          <div>
            <label className="mb-1.5 block text-xs font-medium text-ink-muted">
              Topic (optional if a document is selected)
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder={info.placeholder}
              className="input-field"
            />
          </div>

          <button onClick={handleGenerate} disabled={loading} className="btn-primary mx-auto">
            <Sparkles size={15} />
            {loading ? 'Generating...' : 'Generate'}
          </button>
          {error && (
            <div className="mx-auto flex max-w-sm items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-left text-xs text-coral-glow">
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <ResultRenderer toolId={toolId} result={result} />
          <button onClick={() => setResult(null)} className="btn-secondary">
            <RotateCw size={14} /> Generate again
          </button>
        </div>
      )}
    </div>
  )
}

function ResultRenderer({ toolId, result }) {
  if (toolId === 'tool-quiz') return <QuizResult questions={result.questions} />
  if (toolId === 'tool-flashcards') return <FlashcardsResult cards={result.cards} />
  if (toolId === 'tool-presentation') return <PresentationResult slides={result.slides} fileId={result.file_id} />

  const text = result.summary || result.literature_review || result.research_gaps || result.proposal
  return (
    <div className="glass-card p-5">
      <div className="space-y-2 text-sm text-ink [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_h1]:font-display [&_h1]:text-base [&_h1]:font-semibold [&_h2]:font-display [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-3">
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    </div>
  )
}

function QuizResult({ questions }) {
  const [answers, setAnswers] = useState({})

  return (
    <div className="space-y-3">
      {questions.map((q, i) => (
        <div key={i} className="glass-card p-4">
          <p className="mb-3 text-sm font-medium text-ink">{i + 1}. {q.question}</p>
          <div className="space-y-1.5">
            {Object.entries(q.options).map(([letter, text]) => {
              const chosen = answers[i]
              const isChosen = chosen === letter
              const isCorrect = letter === q.correct
              let style = 'border-surface-border hover:border-teal/40'
              if (chosen) {
                if (isCorrect) style = 'border-teal bg-teal/10 text-teal-bright'
                else if (isChosen) style = 'border-coral bg-coral/10 text-coral-glow'
              }
              return (
                <button
                  key={letter}
                  onClick={() => setAnswers((prev) => ({ ...prev, [i]: letter }))}
                  disabled={!!chosen}
                  className={`flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs transition-colors ${style}`}
                >
                  <span className="font-mono text-[10px] text-ink-faint">{letter}</span>
                  <span className="flex-1">{text}</span>
                  {chosen && isCorrect && <Check size={13} />}
                  {chosen && isChosen && !isCorrect && <X size={13} />}
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

function FlashcardsResult({ cards }) {
  const [flipped, setFlipped] = useState({})
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {cards.map((card, i) => (
        <motion.button
          key={i}
          onClick={() => setFlipped((prev) => ({ ...prev, [i]: !prev[i] }))}
          className="glass-card flex min-h-[110px] flex-col items-center justify-center p-4 text-center"
          whileTap={{ scale: 0.98 }}
        >
          <p className="text-[10px] uppercase tracking-wide text-ink-faint">
            {flipped[i] ? 'Answer' : 'Term'}
          </p>
          <p className="mt-1.5 text-sm text-ink">{flipped[i] ? card.back : card.front}</p>
        </motion.button>
      ))}
    </div>
  )
}

function PresentationResult({ slides, fileId }) {
  const downloadUrl = fileId
    ? `${API_BASE_URL}/features/presentation/download/${fileId}?token=${encodeURIComponent(getAccessToken() || '')}`
    : null

  return (
    <div className="space-y-3">
      {downloadUrl ? (
        <a href={downloadUrl} className="btn-primary w-full">
          <Download size={15} /> Download designed .pptx
        </a>
      ) : (
        <div className="flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>The slide content generated fine, but the downloadable file couldn't be built. You can still read the outline below.</span>
        </div>
      )}
      {slides.map((slide, i) => (
        <div key={i} className="glass-card p-4">
          <p className="mb-2 text-xs font-medium text-teal-bright">Slide {i + 1}</p>
          <p className="mb-2 text-sm font-medium text-ink">{slide.title}</p>
          <ul className="list-disc space-y-1 pl-4 text-xs text-ink-muted">
            {slide.bullets.map((b, j) => <li key={j}>{b}</li>)}
          </ul>
        </div>
      ))}
    </div>
  )
}