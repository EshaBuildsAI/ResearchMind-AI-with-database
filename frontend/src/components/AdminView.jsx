import { useEffect, useState } from 'react'
import { Users, FileStack, MessageSquare, Bot, ShieldCheck } from 'lucide-react'
import { adminApi } from '../api'

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="glass-card flex items-center gap-3 p-4">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal/10">
        <Icon size={16} className="text-teal-bright" />
      </div>
      <div>
        <p className="text-lg font-semibold text-ink">{value}</p>
        <p className="text-xs text-ink-faint">{label}</p>
      </div>
    </div>
  )
}

export default function AdminView() {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])

  useEffect(() => {
    adminApi.stats().then(({ data }) => setStats(data)).catch(() => {})
    adminApi.listUsers().then(({ data }) => setUsers(data)).catch(() => {})
  }, [])

  async function handleSetPlan(userId, plan) {
    await adminApi.setPlan(userId, plan)
    setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, plan } : u)))
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-5 flex items-center gap-2">
        <ShieldCheck size={18} className="text-teal-bright" />
        <h1 className="font-display text-xl font-semibold text-ink">Admin Dashboard</h1>
      </div>

      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard icon={Users} label="Total users" value={stats.total_users} />
          <StatCard icon={FileStack} label="Documents" value={stats.total_documents} />
          <StatCard icon={MessageSquare} label="Chat messages" value={stats.total_chat_messages} />
          <StatCard icon={Bot} label="Agent runs" value={stats.total_agent_runs} />
        </div>
      )}

      {stats && (
        <div className="glass-card mb-6 p-5">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-ink-faint">Agent usage by type</p>
          <div className="space-y-2">
            {Object.entries(stats.agent_runs_by_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between text-sm">
                <span className="text-ink-muted">{type}</span>
                <span className="text-ink">{count}</span>
              </div>
            ))}
            {Object.keys(stats.agent_runs_by_type).length === 0 && (
              <p className="text-xs text-ink-faint">No agent runs yet.</p>
            )}
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <p className="border-b border-surface-border p-4 text-xs font-medium uppercase tracking-wide text-ink-faint">Users</p>
        <div className="divide-y divide-surface-border">
          {users.map((u) => (
            <div key={u.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <div>
                <p className="text-ink">{u.username}</p>
                <p className="text-xs text-ink-faint">{u.email} · {u.document_count} docs</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`chip ${u.plan === 'pro' ? 'border-teal/30 bg-teal/10 text-teal-bright' : 'border-surface-border bg-surface-light text-ink-faint'}`}>
                  {u.plan}
                </span>
                <button
                  onClick={() => handleSetPlan(u.id, u.plan === 'pro' ? 'free' : 'pro')}
                  className="btn-secondary px-2.5 py-1 text-xs"
                >
                  {u.plan === 'pro' ? 'Downgrade' : 'Upgrade'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
