import {
  LayoutGrid, MessageSquare, FileStack, Compass, Telescope, ListChecks,
  Clock, Lightbulb, Quote, FileText, HelpCircle, Layers, BookOpen,
  SearchCode, Presentation, GraduationCap, Mic, BrainCircuit,
} from 'lucide-react'

const ICON_SIZE = 17
const ICON_STROKE = 1.75

const NAV_MAIN = [
  { id: 'workspace', label: 'Workspace', icon: LayoutGrid },
  { id: 'documents', label: 'Documents', icon: FileStack },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
]

const NAV_AGENTS = [
  { id: 'agent-planner', label: 'Planner Agent', icon: Compass, agentType: 'planner' },
  { id: 'agent-research', label: 'Research Agent', icon: Telescope, agentType: 'research' },
  { id: 'agent-citation', label: 'Citation Agent', icon: Quote, agentType: 'citation' },
  { id: 'agent-recommendation', label: 'Recommendations', icon: ListChecks, agentType: 'recommendation' },
  { id: 'agent-timeline', label: 'Timeline Agent', icon: Clock, agentType: 'timeline' },
  { id: 'agent-innovation', label: 'Innovation Agent', icon: Lightbulb, agentType: 'innovation' },
]

const NAV_TOOLS = [
  { id: 'tool-summary', label: 'Smart Summary', icon: FileText },
  { id: 'tool-quiz', label: 'AI Quiz', icon: HelpCircle },
  { id: 'tool-flashcards', label: 'Flashcards', icon: Layers },
  { id: 'tool-literature', label: 'Literature Review', icon: BookOpen },
  { id: 'tool-gap', label: 'Research Gap Finder', icon: SearchCode },
  { id: 'tool-presentation', label: 'Presentation Studio', icon: Presentation },
  { id: 'tool-proposal', label: 'Proposal Generator', icon: GraduationCap },
  { id: 'tool-voice', label: 'Voice Assistant', icon: Mic },
]

function NavItem({ item, active, onClick }) {
  const Icon = item.icon
  return (
    <button
      onClick={onClick}
      className={`group flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] transition-colors ${
        active
          ? 'bg-teal/10 text-teal-bright'
          : 'text-ink-muted hover:bg-surface-light hover:text-ink'
      }`}
    >
      <Icon size={ICON_SIZE} strokeWidth={ICON_STROKE} className="shrink-0" />
      <span className="truncate">{item.label}</span>
    </button>
  )
}

function SectionLabel({ children }) {
  return (
    <p className="mb-1.5 mt-5 px-2.5 text-[10px] font-semibold uppercase tracking-wider text-ink-faint">
      {children}
    </p>
  )
}

export default function Sidebar({ activeView, onNavigate }) {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-surface-border bg-surface/40 backdrop-blur-md md:flex">
      <div className="flex items-center gap-2 px-4 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-teal to-teal-dim">
          <BrainCircuit size={16} className="text-void" />
        </div>
        <span className="font-display text-sm font-semibold text-ink">ResearchMind</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        {NAV_MAIN.map((item) => (
          <NavItem key={item.id} item={item} active={activeView === item.id} onClick={() => onNavigate(item.id)} />
        ))}

        <SectionLabel>AI Agents</SectionLabel>
        {NAV_AGENTS.map((item) => (
          <NavItem key={item.id} item={item} active={activeView === item.id} onClick={() => onNavigate(item.id)} />
        ))}

        <SectionLabel>AI Tools</SectionLabel>
        {NAV_TOOLS.map((item) => (
          <NavItem key={item.id} item={item} active={activeView === item.id} onClick={() => onNavigate(item.id)} />
        ))}
      </nav>
    </aside>
  )
}

export { NAV_MAIN, NAV_AGENTS, NAV_TOOLS }
