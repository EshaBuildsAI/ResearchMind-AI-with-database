import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { agentsApi, WS_BASE_URL } from '../api'
import { getAccessToken } from '../api/client'

const AgentPanelContext = createContext(null)

export function AgentPanelProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [currentRun, setCurrentRun] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const wsRef = useRef(null)

  const closeSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  /** Live-streaming run: kicks off the agent in the background, then opens a
   * WebSocket to watch each step arrive in real time (instead of waiting for
   * the whole run to finish before showing anything). */
  const runAgent = useCallback(async (agentType, question, documentIds) => {
    closeSocket()
    setIsOpen(true)
    setIsRunning(true)
    setError(null)
    setCurrentRun({ agent_type: agentType, question, status: 'running', steps: [], result_text: null, result: null })

    try {
      const { data } = await agentsApi.startStreaming(agentType, question, documentIds)
      const runId = data.run_id

      return await new Promise((resolve, reject) => {
        const token = getAccessToken()
        const ws = new WebSocket(`${WS_BASE_URL}/ws/agents/${runId}?token=${encodeURIComponent(token || '')}`)
        wsRef.current = ws

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data)
          if (msg.type === 'ping') return

          if (msg.type === 'step') {
            setCurrentRun((prev) => {
              if (!prev) return prev
              const steps = [...(prev.steps || [])]
              steps[msg.step_index] = {
                step_index: msg.step_index, name: msg.name, label: msg.label,
                status: msg.status, detail: msg.detail,
              }
              return { ...prev, steps }
            })
          } else if (msg.type === 'run_finished') {
            setIsRunning(false)
            setCurrentRun((prev) => {
              const finished = {
                ...prev, status: msg.status, result_text: msg.result_text, result: msg.result,
                error_message: msg.error, id: runId,
              }
              setHistory((h) => [finished, ...h].slice(0, 20))
              return finished
            })
            if (msg.status === 'failed') setError(msg.error || 'The agent run failed.')
            ws.close()
            resolve()
          }
        }

        ws.onerror = () => {
          setIsRunning(false)
          setError('Lost connection to the agent stream.')
          reject(new Error('WebSocket error'))
        }
      })
    } catch (err) {
      setIsRunning(false)
      setError(err.response?.data?.detail || 'The agent run failed. Please try again.')
      setCurrentRun((prev) => (prev ? { ...prev, status: 'failed' } : prev))
      throw err
    }
  }, [closeSocket])

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
    closeSocket()
    setCurrentRun(run)
    setError(null)
    setIsOpen(true)
  }, [closeSocket])

  const deleteCurrentRun = useCallback(async () => {
    closeSocket()
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
  }, [currentRun, closeSocket])

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
