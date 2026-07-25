import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BrainCircuit, Lock, User, ArrowRight, AlertCircle, ShieldCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-teal/20 blur-[100px]" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-coral/15 blur-[100px]" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="glass-card relative w-full max-w-md p-8"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal to-teal-dim shadow-glow">
            {pendingToken ? (
              <ShieldCheck size={24} className="text-void" strokeWidth={2} />
            ) : (
              <BrainCircuit size={24} className="text-void" strokeWidth={2} />
            )}
          </div>
          <h1 className="font-display text-xl font-semibold text-ink">
            {pendingToken ? 'Two-factor verification' : 'ResearchMind AI'}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            {pendingToken ? 'Enter the 6-digit code from your authenticator app' : 'Upload, analyze, and discover research insights'}
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
  )
}
