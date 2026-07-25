import { useEffect, useState } from 'react'
import { CreditCard, Sparkles, AlertCircle, FileStack, MessageSquare, Bot } from 'lucide-react'
import { billingApi } from '../api'

function UsageBar({ icon: Icon, label, used, limit }) {
  const pct = limit ? Math.min(100, Math.round((used / limit) * 100)) : 0
  return (
    <div className="mb-4">
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 text-ink-muted">
          <Icon size={13} /> {label}
        </span>
        <span className="text-ink-faint">{used} / {limit ?? '∞'}</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-light">
        <div
          className={`h-full rounded-full ${pct >= 90 ? 'bg-coral' : 'bg-teal'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default function BillingView() {
  const [usage, setUsage] = useState(null)
  const [error, setError] = useState('')
  const [upgrading, setUpgrading] = useState(false)

  useEffect(() => {
    billingApi.usageSummary().then(({ data }) => setUsage(data)).catch(() => {})
  }, [])

  async function handleUpgrade() {
    setError('')
    setUpgrading(true)
    try {
      const { data } = await billingApi.checkout()
      window.location.href = data.checkout_url
    } catch (err) {
      setError(err.response?.data?.detail || 'Billing is not set up yet on this server.')
    } finally {
      setUpgrading(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-5">
        <h1 className="font-display text-xl font-semibold text-ink">Usage &amp; Billing</h1>
        <p className="mt-1 text-sm text-ink-muted">Your current plan and daily limits.</p>
      </div>

      {usage && (
        <div className="glass-card mb-4 p-6">
          <div className="mb-5 flex items-center justify-between">
            <span className={`chip ${usage.plan === 'pro' ? 'border-teal/40 bg-teal/10 text-teal-bright' : 'border-surface-border bg-surface-light text-ink-muted'}`}>
              <Sparkles size={11} /> {usage.plan === 'pro' ? 'Pro plan' : 'Free plan'}
            </span>
          </div>

          <UsageBar icon={FileStack} label="Documents stored" used={usage.documents.used} limit={usage.documents.limit} />
          <UsageBar icon={MessageSquare} label="Chat messages today" used={usage.chat_today.used} limit={usage.chat_today.limit} />
          <UsageBar icon={Bot} label="Agent runs today" used={usage.agent_today.used} limit={usage.agent_today.limit} />
        </div>
      )}

      {error && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2 text-xs text-coral-glow">
          <AlertCircle size={14} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {usage?.plan !== 'pro' && (
        <div className="glass-card p-6 text-center">
          <p className="mb-3 text-sm text-ink">Upgrade to Pro for higher limits on documents, chat, and agents.</p>
          <button onClick={handleUpgrade} disabled={upgrading} className="btn-primary mx-auto">
            <CreditCard size={15} /> {upgrading ? 'Redirecting...' : 'Upgrade to Pro'}
          </button>
        </div>
      )}
    </div>
  )
}
