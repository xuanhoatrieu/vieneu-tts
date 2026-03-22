// VieNeu TTS — API Service Layer
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://127.0.0.1:8888/api/v1'
  : `${window.location.origin}/api/v1`;

class ApiService {
  constructor() {
    this.token = localStorage.getItem('token');
  }

  setToken(token) {
    this.token = token;
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
  }

  async request(path, options = {}) {
    const headers = { ...options.headers };
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    // Support custom timeout (default 60s, trained voice needs more)
    const timeoutMs = options.timeoutMs || 60000;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(`${API_BASE}${path}`, {
        ...options, headers, signal: controller.signal,
      });

      if (res.status === 401) {
        this.setToken(null);
        window.location.href = '/login';
        throw new Error('Unauthorized');
      }

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = Array.isArray(err.detail)
          ? err.detail.map(e => e.msg || e.message || JSON.stringify(e)).join('; ')
          : (err.detail || err.message || 'Request failed');
        throw new Error(detail);
      }
      if (res.status === 204) return null;
      const ct = res.headers.get('content-type') || '';
      if (ct.includes('audio') || ct.includes('octet')) return res.blob();
      return res.json();
    } catch (e) {
      if (e.name === 'AbortError') {
        throw new Error('Request timed out — quá trình xử lý mất quá lâu, vui lòng thử lại.');
      }
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }

  get(path)            { return this.request(path); }
  post(path, body)     { return this.request(path, { method: 'POST', body: JSON.stringify(body) }); }
  put(path, body)      { return this.request(path, { method: 'PUT', body: JSON.stringify(body) }); }
  del(path)            { return this.request(path, { method: 'DELETE' }); }
  upload(path, formData) { return this.request(path, { method: 'POST', body: formData }); }

  // Auth
  login(email, password)          { return this.post('/auth/login', { email, password }); }
  register(email, password, name) { return this.post('/auth/register', { email, password, name }); }
  getProfile()                    { return this.get('/users/profile'); }

  // TTS
  getVoices()           { return this.get('/tts/voices'); }
  synthesize(body)      { return this.request('/tts/synthesize', { method: 'POST', body: JSON.stringify(body) }); }
  synthesizeWithRef(body){ return this.request('/tts/synthesize-with-ref', { method: 'POST', body: JSON.stringify(body) }); }
  synthesizeCustom(fd)  { return this.upload('/tts/synthesize-custom', fd); }
  synthesizeTrained(body){ return this.request('/tts/synthesize-trained', { method: 'POST', body: JSON.stringify(body), timeoutMs: 600000 }); }
  getAudioUrl(filename) { return `${API_BASE}/tts/audio/${filename}`; }
  getTTSModels()        { return this.get('/tts/models'); }
  switchTTSModel(repo)  { return this.post('/tts/models/switch', { repo }); }
  getTTSModelStatus()   { return this.get('/tts/models/status'); }
  getTrainedVoicesForTTS() { return this.get('/tts/trained-voices'); }

  // References
  getRefs()             { return this.get('/refs'); }
  uploadRef(fd)         { return this.upload('/refs', fd); }
  deleteRef(id)         { return this.del(`/refs/${id}`); }
  getRefAudioUrl(id)    { return `${API_BASE}/refs/${id}/audio`; }

  // Sentences
  getSets()             { return this.get('/sentences/sets'); }
  getSet(id)            { return this.get(`/sentences/sets/${id}`); }
  createSet(body)       { return this.post('/sentences/sets', body); }
  updateSet(id, body)   { return this.put(`/sentences/sets/${id}`, body); }
  deleteSet(id)         { return this.del(`/sentences/sets/${id}`); }
  addSentence(setId, body) { return this.post(`/sentences/sets/${setId}/sentences`, body); }
  updateSentence(id, body) { return this.put(`/sentences/sentences/${id}`, body); }
  deleteSentence(id) { return this.del(`/sentences/sentences/${id}`); }

  // Recordings
  uploadRecording(setId, sentId, fd) { return this.upload(`/training/recordings/${setId}/${sentId}`, fd); }
  getRecordings(setId)  { return this.get(`/training/recordings/${setId}`); }
  getRecordingAudioUrl(id) { return `${API_BASE}/training/recordings/audio/${id}`; }
  deleteRecording(id)   { return this.del(`/training/recordings/item/${id}`); }
  recordingToRef(id)    { return this.request(`/training/recordings/${id}/to-ref`, { method: 'POST' }); }

  // Training
  getBaseModels()       { return this.get('/training/base-models'); }
  submitTraining(body)  { return this.post('/training/requests', body); }
  getTrainingRequests() { return this.get('/training/requests'); }
  getTrainingRequest(id){ return this.get(`/training/requests/${id}`); }
  cancelTraining(id)    { return this.del(`/training/requests/${id}`); }
  getTrainedVoices()    { return this.get('/training/voices'); }
  renameVoice(id, name) { return this.put(`/training/voices/${id}`, { name }); }
  deleteVoice(id)       { return this.del(`/training/voices/${id}`); }

  // Admin
  getAdminStats()       { return this.get('/admin/stats'); }
  getAdminUsers()       { return this.get('/admin/users'); }
  createAdminUser(body) { return this.post('/admin/users', body); }
  updateAdminUser(id, body) { return this.request(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }); }
  deleteAdminUser(id)   { return this.del(`/admin/users/${id}`); }
  previewDeleteUser(id) { return this.get(`/admin/users/${id}/delete-preview`); }
  getModels()           { return this.get('/admin/models'); }
  switchModel(repo)     { return this.post('/admin/models/switch', { repo }); }
  getModelStatus()      { return this.get('/admin/models/status'); }
  getTrainingQueue(status) {
    const q = status ? `?status=${status}` : '';
    return this.get(`/admin/training-queue${q}`);
  }
  approveTraining(id)   { return this.request(`/admin/training-queue/${id}/approve`, { method: 'POST' }); }
  rejectTraining(id)    { return this.request(`/admin/training-queue/${id}/reject`, { method: 'POST' }); }
  startTraining(id, maxSteps = 5000, gpuId = null, baseModel = null) {
    const params = new URLSearchParams({ max_steps: maxSteps });
    if (gpuId !== null) params.append('gpu_id', gpuId);
    if (baseModel) params.append('base_model', baseModel);
    return this.request(`/admin/training-queue/${id}/start?${params}`, { method: 'POST' });
  }
  deleteTraining(id)    { return this.del(`/admin/training-queue/${id}`); }

  // API Keys
  getApiKeys()          { return this.get('/api-keys'); }
  createApiKey(name)    { return this.post('/api-keys', { name }); }
  deleteApiKey(id)      { return this.del(`/api-keys/${id}`); }
}

export const api = new ApiService();
export default api;
