import { motion } from 'framer-motion'
import {
  Compass, Telescope, Quote, ListChecks, Clock, Lightbulb, FileText, HelpCircle,
  Layers, BookOpen, SearchCode, Presentation, GraduationCap, Mic, MessageSquare, FileStack,
} from 'lucide-react'
import { useDocuments } from '../context/DocumentsContext'

const CARDS = [
  { id: 'chat', label: 'Chat with AI', desc: 'Ask questions about your document', icon: MessageSquare, accent: 'teal' },
  { id: 'agent-planner', label: 'Planner Agent', desc: 'Ask anything — it routes to the right tool', icon: Compass, accent: 'coral' },
  { id: 'tool-summary', label: 'Smart Summary', desc: 'Get a structured summary', icon: FileText, accent: 'teal' },
  { id: 'tool-literature', label: 'Literature Review', desc: 'Auto-generate a review section', icon: BookOpen, accent: 'teal' },
  { id: 'tool-flashcards', label: 'Flashcards', desc: 'Study key concepts and terms', icon: Layers, accent: 'coral' },
  { id: 'tool-quiz', label: 'AI Quiz', desc: 'Test your understanding', icon: HelpCircle, accent: 'teal' },
  { id: 'tool-presentation', label: 'Presentation Studio', desc: 'Turn research into slides', icon: Presentation, accent: 'coral' },
  { id: 'tool-gap', label: 'Research Gap Finder', desc: 'Find missing topics & limitations', icon: SearchCode, accent: 'teal' },
  { id: 'agent-research', label: 'Research Agent', desc: 'Doc + web search, cited answers', icon: Telescope, accent: 'coral' },
  { id: 'agent-citation', label: 'Citation Agent', desc: 'Answers with page number & confidence', icon: Quote, accent: 'teal' },
  { id: 'agent-recommendation', label: 'Recommendation Agent', desc: 'Papers & techniques to explore next', icon: ListChecks, accent: 'coral' },
  { id: 'agent-timeline', label: 'Timeline Agent', desc: 'How this topic evolved over time', icon: Clock, accent: 'teal' },
  { id: 'agent-innovation', label: 'Innovation Agent', desc: 'Novel project ideas from gaps + trends', icon: Lightbulb, accent: 'coral' },
  { id: 'tool-proposal', label: 'Proposal Agent', desc: 'Draft a BS/MS final year proposal', icon: GraduationCap, accent: 'teal' },
  { id: 'tool-voice', label: 'Voice Assistant', desc: 'Ask a question, get a spoken answer', icon: Mic, accent: 'coral' },
  { id: 'documents', label: 'Documents', desc: 'Manage your uploaded files', icon: FileStack, accent: 'teal' },
]

export default function WorkspaceGrid({ onNavigate }) {
  const { selected, documents } = useDocuments()

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-semibold text-ink">
          Welcome back{selected ? '' : ''}
        </h1>
        <p className="mt-1.5 text-sm text-ink-muted">
          {selected
            ? <>Working on <span className="text-teal-bright">{selected.filename}</span></>
            : documents.length > 0
              ? 'Select a document from the top bar to get started'
              : 'Upload a document to unlock the full workspace'}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map((card, i) => {
          const Icon = card.icon
          return (
            <motion.button
              key={card.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03, duration: 0.35 }}
              onClick={() => onNavigate(card.id)}
              className="glass-card group flex flex-col items-start gap-3 p-4 text-left transition-all hover:border-teal/40 hover:-translate-y-0.5"
            >
              <div
                className={`flex h-9 w-9 items-center justify-center rounded-xl transition-colors ${
                  card.accent === 'teal' ? 'bg-teal/10 text-teal-bright' : 'bg-coral/10 text-coral-glow'
                }`}
              >
                <Icon size={17} strokeWidth={1.75} />
              </div>
              <div>
                <p className="text-sm font-medium text-ink">{card.label}</p>
                <p className="mt-0.5 text-xs text-ink-muted">{card.desc}</p>
              </div>
            </motion.button>
          )
        })}
      </div>
    </div>
  )
}
