import { useState, useRef } from 'react'
import { Mic, Square, Loader2, Volume2, AlertCircle, User, Bot, Telescope, MessageCircle } from 'lucide-react'
import { voiceApi } from '../api'
import { useDocuments } from '../context/DocumentsContext'

export default function VoiceView() {
  const { selected } = useDocuments()
  const [recording, setRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [researchMode, setResearchMode] = useState(false)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  async function startRecording() {
    setError('')
    setResult(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.onstop = () => handleStop(stream)
      recorder.start()
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch {
      setError("Couldn't access your microphone. Check browser permissions.")
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  async function handleStop(stream) {
    stream.getTracks().forEach((t) => t.stop())
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
    setLoading(true)
    try {
      const { data } = await voiceApi.ask(blob, selected?.id, true, researchMode)
      setResult(data)
      if (data.audio_base64) {
        const audioBlob = base64ToBlob(data.audio_base64, 'audio/mpeg')
        setAudioUrl(URL.createObjectURL(audioBlob))
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Voice request failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function base64ToBlob(base64, mimeType) {
    const bytes = atob(base64)
    const arr = new Uint8Array(bytes.length)
    for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i)
    return new Blob([arr], { type: mimeType })
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="glass-card p-8 text-center">
        <h1 className="font-display text-lg font-semibold text-ink">Voice Assistant</h1>
        <p className="mt-1.5 text-sm text-ink-muted">
          Record a question about {selected ? selected.filename : 'your research'} — or ask anything at all —
          and get a spoken answer.
        </p>

        {/* Mode toggle — same doc+web-search power as the Research Agent, spoken instead of typed */}
        <div className="mx-auto mt-5 flex w-fit rounded-xl border border-surface-border bg-surface-light p-1">
          <button
            onClick={() => setResearchMode(false)}
            disabled={recording || loading}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              !researchMode ? 'bg-teal text-void' : 'text-ink-muted'
            }`}
          >
            <MessageCircle size={13} /> Quick answer
          </button>
          <button
            onClick={() => setResearchMode(true)}
            disabled={recording || loading}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              researchMode ? 'bg-teal text-void' : 'text-ink-muted'
            }`}
          >
            <Telescope size={13} /> Research mode
          </button>
        </div>
        <p className="mt-2 text-[11px] text-ink-faint">
          {researchMode
            ? 'Also searches arXiv + Semantic Scholar before answering, like the Research Agent.'
            : 'Answers from the attached document (if any) or general knowledge.'}
        </p>

        <div className="mt-6 flex flex-col items-center gap-4">
          <button
            onClick={recording ? stopRecording : startRecording}
            disabled={loading}
            className={`flex h-16 w-16 items-center justify-center rounded-full transition-all ${
              recording
                ? 'bg-coral shadow-glow-coral animate-pulse-glow'
                : 'bg-teal shadow-glow hover:bg-teal-bright'
            }`}
          >
            {loading ? (
              <Loader2 size={22} className="animate-spin text-void" />
            ) : recording ? (
              <Square size={20} className="text-void" fill="currentColor" />
            ) : (
              <Mic size={22} className="text-void" strokeWidth={1.75} />
            )}
          </button>
          <p className="text-xs text-ink-faint">
            {loading
              ? researchMode
                ? 'Transcribing, searching, and answering...'
                : 'Transcribing and answering...'
              : recording
                ? 'Recording — tap to stop'
                : 'Tap to record a question'}
          </p>
        </div>

        {error && (
          <div className="mx-auto mt-5 flex max-w-sm items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-left text-xs text-coral-glow">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {result && (
          <div className="mt-6 space-y-3 text-left">
            <div className="flex items-start gap-2 rounded-xl bg-surface-light px-3 py-2.5">
              <User size={14} className="mt-0.5 shrink-0 text-ink-faint" />
              <p className="text-sm text-ink">{result.question}</p>
            </div>
            <div className="flex items-start gap-2 rounded-xl border border-teal/20 bg-teal/5 px-3 py-2.5">
              <Bot size={14} className="mt-0.5 shrink-0 text-teal-bright" />
              <p className="text-sm text-ink">{result.answer}</p>
            </div>
            {audioUrl && (
              <div className="flex items-center gap-2 rounded-xl bg-surface-light px-3 py-2">
                <Volume2 size={14} className="text-teal-bright" />
                <audio controls src={audioUrl} className="h-8 flex-1" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}