import { useState } from 'react'
import Sidebar from '../components/Sidebar'
import Topbar from '../components/Topbar'
import AgentPanel from '../components/AgentPanel'
import WorkspaceGrid from '../components/WorkspaceGrid'
import DocumentsView from '../components/DocumentsView'
import ChatWindow from '../components/ChatWindow'
import AgentLauncherView from '../components/AgentLauncherView'
import FeatureView from '../components/FeatureView'
import VoiceView from '../components/VoiceView'
import AgentHistoryView from '../components/AgentHistoryView'
import SettingsView from '../components/SettingsView'
import BillingView from '../components/BillingView'
import AdminView from '../components/AdminView'

const AGENT_TYPE_MAP = {
  'agent-planner': 'planner',
  'agent-research': 'research',
  'agent-citation': 'citation',
  'agent-recommendation': 'recommendation',
  'agent-timeline': 'timeline',
  'agent-innovation': 'innovation',
}

export default function Dashboard() {
  const [activeView, setActiveView] = useState('workspace')

  function renderView() {
    if (activeView === 'workspace') return <WorkspaceGrid onNavigate={setActiveView} />
    if (activeView === 'documents') return <DocumentsView />
    if (activeView === 'chat') return <ChatWindow />
    if (activeView === 'history') return <AgentHistoryView />
    if (activeView === 'settings') return <SettingsView />
    if (activeView === 'billing') return <BillingView />
    if (activeView === 'admin') return <AdminView />
    if (activeView === 'tool-voice') return <VoiceView />
    if (AGENT_TYPE_MAP[activeView]) return <AgentLauncherView agentType={AGENT_TYPE_MAP[activeView]} />
    if (activeView.startsWith('tool-')) return <FeatureView toolId={activeView} />
    return <WorkspaceGrid onNavigate={setActiveView} />
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar activeView={activeView} onNavigate={setActiveView} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto px-6 py-8">{renderView()}</main>
      </div>
      <AgentPanel />
    </div>
  )
}
