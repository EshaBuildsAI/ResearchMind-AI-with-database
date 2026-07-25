import { createContext, useContext, useState, useCallback } from 'react'
import { agentsApi } from '../api'

const AgentPanelContext = createContext(null)

const AGENT_RUNNERS = {
  research: agentsApi.research,
  planner: agentsApi.planner,
  recommendation: agentsApi.recommendation,
  timeline: agentsApi.timeline,
  innovation: agentsApi.innovation,
  citation: agentsApi.citation,
}

export function AgentPanelProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [currentRun, setCurrentRun] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])

  const runAgent = useCallback(async (agentType, question, documentId) => {
    const runner = AGENT_RUNNERS[agentType]
    if (!runner) throw new Error(`Unknown agent type: ${agentType}`)

    setIsOpen(true)
    setIsRunning(true)
    setError(null)
    setCurrentRun({ agent_type: agentType, question, status: 'running', steps: [] })

    try {
      const { data } = await runner(question, documentId)
      setCurrentRun(data)
      setHistory((prev) => [data, ...prev].slice(0, 20))
      return data
    } catch (err) {
      setError(err.response?.data?.detail || 'The agent run failed. Please try again.')
      setCurrentRun((prev) => (prev ? { ...prev, status: 'failed' } : prev))
      throw err
    } finally {
      setIsRunning(false)
    }
  }, [])

  const summarizeReference = useCallback(async (url, question, documentId) => {
    setIsOpen(true)
    setIsRunning(true)
    setError(null)
    setCurrentRun({ agent_type: 'summarize_reference', question: url, status: 'running', steps: [] })
    try {
      const { data } = await agentsApi.summarizeReference(url, question, documentId)
      setCurrentRun(data)
      setHistory((prev) => [data, ...prev].slice(0, 20))
      return data
    } catch (err) {
      setError(err.response?.data?.detail || "Couldn't summarize that link.")
      setCurrentRun((prev) => (prev ? { ...prev, status: 'failed' } : prev))
      throw err
    } finally {
      setIsRunning(false)
    }
  }, [])

  const reopenRun = useCallback((run) => {
    setCurrentRun(run)
    setError(null)
    setIsOpen(true)
  }, [])

  const deleteCurrentRun = useCallback(async () => {
    if (currentRun?.id) {
      try {
        await agentsApi.deleteRun(currentRun.id)
      } catch {
        // even if the server delete fails, still clear it from view
      }
      setHistory((prev) => prev.filter((r) => r.id !== currentRun.id))
    }
    setCurrentRun(null)
    setError(null)
    setIsOpen(false)
  }, [currentRun])

  const closePanel = useCallback(() => setIsOpen(false), [])

  return (
    <AgentPanelContext.Provider
      value={{
        isOpen, isRunning, currentRun, error, history,
        runAgent, summarizeReference, reopenRun, closePanel, deleteCurrentRun, setIsOpen,
      }}
    >
      {children}
    </AgentPanelContext.Provider>
  )
}

export function useAgentPanel() {
  const ctx = useContext(AgentPanelContext)
  if (!ctx) throw new Error('useAgentPanel must be used within AgentPanelProvider')
  return ctx
}