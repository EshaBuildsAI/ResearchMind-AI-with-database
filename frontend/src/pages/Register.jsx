import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { BrainCircuit, Lock, User, Mail, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(form.username, form.email, form.password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 1400)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(Array.isArray(detail) ? detail[0]?.msg : detail || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute -right-32 -top-24 h-96 w-96 rounded-full bg-coral/15 blur-[100px]" />
      <div className="pointer-events-none absolute -left-24 bottom-0 h-80 w-80 rounded-full bg-teal/20 blur-[100px]" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="glass-card relative w-full max-w-md p-8"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-coral to-coral-dark shadow-glow-coral">
            <BrainCircuit size={24} className="text-void" strokeWidth={2} />
          </div>
          <h1 className="font-display text-xl font-semibold text-ink">Create your workspace</h1>
          <p className="mt-1 text-sm text-ink-muted">Start analyzing research in minutes</p>
        </div>

        {success ? (
          <div className="flex flex-col items-center gap-3 py-6 text-center">
            <CheckCircle2 size={32} className="text-teal-bright" />
            <p className="text-sm text-ink">Account created. Check your email to verify your account. Redirecting to sign in...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input
                type="text"
                placeholder="Username"
                value={form.username}
                onChange={(e) => update('username', e.target.value)}
                className="input-field pl-10"
                required
                autoFocus
              />
            </div>
            <div className="relative">
              <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input
                type="email"
                placeholder="Email"
                value={form.email}
                onChange={(e) => update('email', e.target.value)}
                className="input-field pl-10"
                required
              />
            </div>
            <div className="relative">
              <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input
                type="password"
                placeholder="Password (min. 6 characters)"
                value={form.password}
                onChange={(e) => update('password', e.target.value)}
                className="input-field pl-10"
                required
                minLength={6}
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
                <AlertCircle size={14} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Creating account...' : 'Create account'}
              {!loading && <ArrowRight size={15} />}
            </button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-ink-muted">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-teal-bright hover:underline">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
