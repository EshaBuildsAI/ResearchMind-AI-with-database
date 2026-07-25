import client from './client'

// ---------------- Auth ----------------
export const authApi = {
  register: (data) => client.post('/auth/register', data),
  login: (data) => client.post('/auth/login', data),
  me: () => client.get('/auth/me'),
  logout: () => client.post('/auth/logout'),
  deleteAccount: () => client.delete('/auth/account'),
  resetWorkspace: () => client.post('/auth/reset-workspace'),
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
  ask: (question, documentId) => client.post('/query/chat', { question, document_id: documentId }),
  history: (documentId) => client.get('/query/history', { params: { document_id: documentId } }),
}

// ---------------- Agents ----------------
export const agentsApi = {
  research: (question, documentId) => client.post('/agents/research', { question, document_id: documentId }),
  planner: (question, documentId) => client.post('/agents/planner', { question, document_id: documentId }),
  recommendation: (question, documentId) => client.post('/agents/recommendation', { question, document_id: documentId }),
  timeline: (question, documentId) => client.post('/agents/timeline', { question, document_id: documentId }),
  innovation: (question, documentId) => client.post('/agents/innovation', { question, document_id: documentId }),
  citation: (question, documentId) => client.post('/agents/citation', { question, document_id: documentId }),
  summarizeReference: (url, question, documentId) =>
    client.post('/agents/summarize-reference', { url, question, document_id: documentId }),
  listRuns: (documentId) => client.get('/agents/runs', { params: { document_id: documentId } }),
  getRun: (id) => client.get(`/agents/runs/${id}`),
  deleteRun: (id) => client.delete(`/agents/runs/${id}`),
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
  ask: (audioBlob, documentId, speakResponse) => {
    const form = new FormData()
    form.append('audio', audioBlob, 'question.webm')
    if (documentId) form.append('document_id', documentId)
    form.append('speak_response', speakResponse ? 'true' : 'false')
    return client.post('/voice/ask', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}