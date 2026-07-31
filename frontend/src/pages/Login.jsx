import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  BrainCircuit, Lock, User, ArrowRight, AlertCircle, ShieldCheck,
  MessageSquare, Telescope, HelpCircle, Quote, Mic, Presentation,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const PILLS = [
  { icon: MessageSquare, label: 'Chat' },
  { icon: Telescope, label: 'Research Agent' },
  { icon: HelpCircle, label: 'Quiz & Flashcards' },
  { icon: Quote, label: 'Citations' },
  { icon: Mic, label: 'Voice Assistant' },
  { icon: Presentation, label: 'Presentations' },
]

export default function Login() {
  const { login, completeLogin2fa } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingToken, setPendingToken] = useState(null)
  const [code, setCode] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const result = await login(identifier, password)
      if (result.requiresTwoFactor) {
        setPendingToken(result.pendingToken)
      } else {
        navigate('/')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  async function handle2faSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await completeLogin2fa(pendingToken, code)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-teal/20 blur-[100px]" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-coral/15 blur-[100px]" />

      <div className="relative mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center gap-12 px-6 py-12 lg:flex-row lg:items-center lg:gap-20">
        {/* Left: product showcase — hidden on small screens to keep mobile focused on the form */}
        <div className="hidden max-w-lg lg:block">
          <div className="mb-6 flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-teal to-teal-dim">
              <BrainCircuit size={18} className="text-void" />
            </div>
            <span className="font-display text-sm font-semibold text-ink">ResearchMind AI</span>
          </div>
          <h1 className="font-display text-5xl font-semibold leading-tight text-ink">
            One document.
            <br />
            Every answer.
          </h1>
          <p className="mt-5 max-w-md text-base text-ink-muted">
            Upload once, and let AI summarize, cite, quiz, and answer — in your language, with real sources.
          </p>
          <div className="mt-8 flex flex-wrap gap-2">
            {PILLS.map((p) => (
              <span key={p.label} className="chip border-surface-border bg-surface-light text-ink-muted">
                <p.icon size={13} strokeWidth={1.75} /> {p.label}
              </span>
            ))}
          </div>
        </div>

        {/* Right: login form */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="glass-card relative w-full max-w-md p-8"
        >
          <div className="mb-8 flex flex-col items-center text-center lg:hidden">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal to-teal-dim shadow-glow">
              <BrainCircuit size={24} className="text-void" strokeWidth={2} />
            </div>
            <h1 className="font-display text-xl font-semibold text-ink">ResearchMind AI</h1>
          </div>

          <div className="mb-6 hidden text-center lg:block">
            {pendingToken ? (
              <div className="mb-2 flex justify-center">
                <ShieldCheck size={22} className="text-teal-bright" />
              </div>
            ) : null}
            <h2 className="font-display text-xl font-semibold text-ink">
              {pendingToken ? 'Two-factor verification' : 'Welcome back'}
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              {pendingToken ? 'Enter the 6-digit code from your authenticator app' : 'Log in to keep exploring your research.'}
            </p>
          </div>

          {pendingToken ? (
            <form onSubmit={handle2faSubmit} className="space-y-4">
              <input
                type="text"
                inputMode="numeric"
                placeholder="123456"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="input-field text-center text-lg tracking-[0.3em]"
                maxLength={6}
                required
                autoFocus
              />
              {error && (
                <div className="flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? 'Verifying...' : 'Verify'}
              </button>
              <button
                type="button"
                onClick={() => { setPendingToken(null); setCode(''); setError('') }}
                className="w-full text-center text-xs text-ink-faint hover:text-ink-muted"
              >
                Back to login
              </button>
            </form>
          ) : (
            <>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <input
                    type="text"
                    placeholder="Username or email"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    className="input-field pl-10"
                    required
                    autoFocus
                  />
                </div>
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
                  <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input-field pl-10"
                    required
                  />
                </div>

                <div className="flex justify-end">
                  <Link to="/forgot-password" className="text-xs text-ink-faint hover:text-teal-bright">
                    Forgot password?
                  </Link>
                </div>

                {error && (
                  <div className="flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
                    <AlertCircle size={14} className="mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading ? 'Signing in...' : 'Sign in'}
                  {!loading && <ArrowRight size={15} />}
                </button>
              </form>

              <p className="mt-6 text-center text-sm text-ink-muted">
                New here?{' '}
                <Link to="/register" className="font-medium text-teal-bright hover:underline">
                  Create an account
                </Link>
              </p>
            </>
          )}
        </motion.div>
      </div>
    </div>
  )
}