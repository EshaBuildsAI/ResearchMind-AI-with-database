import { useState } from 'react'
import { ShieldCheck, ShieldOff, AlertCircle, CheckCircle2 } from 'lucide-react'
import { authApi } from '../api'
import { useAuth } from '../context/AuthContext'

export default function SettingsView() {
  const { user, setUser } = useAuth()
  const [step, setStep] = useState('idle') // idle | scanning | done
  const [qrCode, setQrCode] = useState(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleEnable() {
    setError('')
    setLoading(true)
    try {
      const { data } = await authApi.enable2fa()
      setQrCode(data.qr_code_base64)
      setStep('scanning')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not start 2FA setup.')
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.confirm2fa(code)
      setUser((prev) => ({ ...prev, totp_enabled: true }))
      setStep('idle')
      setQrCode(null)
      setCode('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code.')
    } finally {
      setLoading(false)
    }
  }

  async function handleDisable(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.disable2fa(code)
      setUser((prev) => ({ ...prev, totp_enabled: false }))
      setCode('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-5">
        <h1 className="font-display text-xl font-semibold text-ink">Security Settings</h1>
        <p className="mt-1 text-sm text-ink-muted">Two-factor authentication — free, using any authenticator app.</p>
      </div>

      <div className="glass-card p-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal/10">
            {user?.totp_enabled ? <ShieldCheck size={18} className="text-teal-bright" /> : <ShieldOff size={18} className="text-ink-faint" />}
          </div>
          <div>
            <p className="text-sm font-medium text-ink">Two-Factor Authentication</p>
            <p className="text-xs text-ink-faint">
              {user?.totp_enabled ? 'Enabled — your account requires a code at login.' : 'Not enabled'}
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {!user?.totp_enabled && step === 'idle' && (
          <button onClick={handleEnable} disabled={loading} className="btn-primary">
            {loading ? 'Starting...' : 'Enable 2FA'}
          </button>
        )}

        {step === 'scanning' && qrCode && (
          <div className="space-y-4">
            <p className="text-xs text-ink-muted">Scan this QR code with Google Authenticator, Authy, or 1Password:</p>
            <div className="flex justify-center rounded-xl bg-white p-4">
              <img src={`data:image/png;base64,${qrCode}`} alt="2FA QR code" className="h-40 w-40" />
            </div>
            <form onSubmit={handleConfirm} className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                placeholder="Enter 6-digit code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="input-field text-center tracking-[0.2em]"
                maxLength={6}
                required
              />
              <button type="submit" disabled={loading} className="btn-primary shrink-0">
                Confirm
              </button>
            </form>
          </div>
        )}

        {user?.totp_enabled && (
          <form onSubmit={handleDisable} className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              placeholder="Enter code to disable"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="input-field text-center tracking-[0.2em]"
              maxLength={6}
              required
            />
            <button type="submit" disabled={loading} className="btn-secondary shrink-0 text-coral-glow">
              Disable
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
