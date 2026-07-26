import client from './client'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
export const WS_BASE_URL = BASE_URL.replace(/^http/, 'ws')

// ---------------- Auth ----------------
export const authApi = {
  register: (data) => client.post('/auth/register', data),
  login: (data) => client.post('/auth/login', data),
  login2fa: (pendingToken, code) => client.post('/auth/login/2fa', { pending_token: pendingToken, code }),
  me: () => client.get('/auth/me'),
  logout: () => client.post('/auth/logout'),
  deleteAccount: () => client.delete('/auth/account'),
  resetWorkspace: () => client.post('/auth/reset-workspace'),
  verifyEmail: (token) => client.post('/auth/verify-email', { token }),
  resendVerification: (email) => client.post('/auth/resend-verification', { email }),
  forgotPassword: (email) => client.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) => client.post('/auth/reset-password', { token, new_password: newPassword }),
  enable2fa: () => client.post('/auth/2fa/enable'),
  confirm2fa: (code) => client.post('/auth/2fa/confirm', { code }),
  disable2fa: (code) => client.post('/auth/2fa/disable', { code }),
}

// ---------------- Documents ----------------
export const documentsApi = {
  upload: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/documents/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
  },
  list: () => client.get('/documents'),
  get: (id) => client.get(`/documents/${id}`),
  delete: (id) => client.delete(`/documents/${id}`),
}

// ---------------- Chat ----------------
export const chatApi = {
  ask: (question, documentIds) => {
    const ids = Array.isArray(documentIds) ? documentIds : documentIds ? [documentIds] : []
    return client.post('/query/chat', {
      question,
      document_id: ids[0] || null,
      document_ids: ids.length > 1 ? ids : null,
    })
  },
  history: (documentId) => client.get('/query/history', { params: { document_id: documentId } }),
}

// ---------------- Agents ----------------
function _agentPayload(question, documentIds) {
  const ids = Array.isArray(documentIds) ? documentIds : documentIds ? [documentIds] : []
  return { question, document_id: ids[0] || null, document_ids: ids.length > 1 ? ids : null }
}

export const agentsApi = {
  research: (question, documentIds) => client.post('/agents/research', _agentPayload(question, documentIds)),
  planner: (question, documentIds) => client.post('/agents/planner', _agentPayload(question, documentIds)),
  recommendation: (question, documentIds) => client.post('/agents/recommendation', _agentPayload(question, documentIds)),
  timeline: (question, documentIds) => client.post('/agents/timeline', _agentPayload(question, documentIds)),
  innovation: (question, documentIds) => client.post('/agents/innovation', _agentPayload(question, documentIds)),
  citation: (question, documentIds) => client.post('/agents/citation', _agentPayload(question, documentIds)),
  summarizeReference: (url, question, documentId) =>
    client.post('/agents/summarize-reference', { url, question, document_id: documentId }),
  listRuns: (documentId) => client.get('/agents/runs', { params: { document_id: documentId } }),
  getRun: (id) => client.get(`/agents/runs/${id}`),
  deleteRun: (id) => client.delete(`/agents/runs/${id}`),
  // Streaming: kicks off the agent in the background, returns {run_id, status}.
  // Caller then opens a WebSocket to WS_BASE_URL + `/ws/agents/${run_id}?token=...`
  startStreaming: (agentType, question, documentIds) =>
    client.post(`/agents/stream?agent_type=${agentType}`, _agentPayload(question, documentIds)),
}

// ---------------- AI Features ----------------
export const featuresApi = {
  summary: (documentId, length) => client.post('/features/summary', { document_id: documentId, length }),
  quiz: (documentId, numQuestions) => client.post('/features/quiz', { document_id: documentId, num_questions: numQuestions }),
  flashcards: (documentId, numCards) => client.post('/features/flashcards', { document_id: documentId, num_cards: numCards }),
  literatureReview: (documentId) => client.post('/features/literature-review', { document_id: documentId }),
  researchGap: (documentId) => client.post('/features/research-gap', { document_id: documentId }),
  presentation: (documentId, numSlides) => client.post('/features/presentation', { document_id: documentId, num_slides: numSlides }),
  proposal: (documentId, degreeLevel, university) =>
    client.post('/features/proposal', { document_id: documentId, degree_level: degreeLevel, university }),
  smartMemory: (documentId) => client.get(`/features/smart-memory/${documentId}`),
}

// ---------------- Voice ----------------
export const voiceApi = {
  ask: (audioBlob, documentId, speakResponse, researchMode) => {
    const form = new FormData()
    form.append('audio', audioBlob, 'question.webm')
    if (documentId) form.append('document_id', documentId)
    form.append('speak_response', speakResponse ? 'true' : 'false')
    form.append('research_mode', researchMode ? 'true' : 'false')
    return client.post('/voice/ask', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

// ---------------- Usage / Billing ----------------
export const billingApi = {
  usageSummary: () => client.get('/usage/summary'),
  checkout: () => client.post('/billing/checkout'),
  portal: () => client.post('/billing/portal'),
}

// ---------------- Admin ----------------
export const adminApi = {
  stats: () => client.get('/admin/stats'),
  listUsers: () => client.get('/admin/users'),
  promoteUser: (userId) => client.post(`/admin/users/${userId}/promote`),
  setPlan: (userId, plan) => client.post(`/admin/users/${userId}/set-plan?plan=${plan}`),
}