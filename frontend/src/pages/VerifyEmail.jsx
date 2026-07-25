import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { MailCheck, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { authApi } from '../api'

export default function VerifyEmail() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [status, setStatus] = useState('verifying') // verifying | success | error

  useEffect(() => {
    if (!token) {
      setStatus('error')
      return
    }
    authApi.verifyEmail(token).then(() => setStatus('success')).catch(() => setStatus('error'))
  }, [token])

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-teal/20 blur-[100px]" />
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass-card relative w-full max-w-md p-8 text-center">
        <div className="mb-5 flex justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-teal/10">
            {status === 'verifying' && <Loader2 size={22} className="animate-spin text-teal-bright" />}
            {status === 'success' && <CheckCircle2 size={22} className="text-teal-bright" />}
            {status === 'error' && <XCircle size={22} className="text-coral" />}
          </div>
        </div>
        <h1 className="font-display text-lg font-semibold text-ink">
          {status === 'verifying' && 'Verifying your email...'}
          {status === 'success' && 'Email verified!'}
          {status === 'error' && 'Verification link invalid'}
        </h1>
        <p className="mt-2 text-sm text-ink-muted">
          {status === 'success' && "You're all set — you can log in now."}
          {status === 'error' && 'This link may have expired. Try resending verification from your account.'}
        </p>
        <Link to="/login" className="btn-primary mt-6 inline-flex">Go to login</Link>
      </motion.div>
    </div>
  )
}
