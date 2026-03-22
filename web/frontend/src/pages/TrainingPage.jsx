import { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function TrainingPage() {
  const [requests, setRequests] = useState([]);
  const [voices, setVoices] = useState([]);
  const [sets, setSets] = useState([]);
  const [baseModels, setBaseModels] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const load = async () => {
    try {
      const [reqs, vs, ss, bm] = await Promise.all([
        api.getTrainingRequests(), api.getTrainedVoices(), api.getSets(), api.getBaseModels()
      ]);
      setRequests(reqs); setVoices(vs); setSets(ss); setBaseModels(bm);
    } catch {} finally { setLoading(false); }
  };
  useEffect(() => { load(); const i = setInterval(load, 10000); return () => clearInterval(i); }, []);

  const cancelRequest = async (id) => {
    if (!confirm('Hủy yêu cầu training?')) return;
    try { await api.cancelTraining(id); toast.success('Đã hủy'); load(); }
    catch (err) { toast.error(err.message); }
  };

  const renameVoice = async (id, current) => {
    const name = prompt('Tên mới:', current);
    if (!name || name === current) return;
    try { await api.renameVoice(id, name); toast.success('Đã đổi tên'); load(); }
    catch (err) { toast.error(err.message); }
  };

  const deleteVoice = async (id) => {
    if (!confirm('Xóa voice này?')) return;
    try { await api.deleteVoice(id); toast.success('Đã xóa'); load(); }
    catch (err) { toast.error(err.message); }
  };

  if (loading) return <div className="loading-page"><span className="spinner" /> Đang tải...</div>;

  return (
    <>
      <div className="topbar">
        <h1>Training</h1>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>+ Yêu cầu Training</button>
      </div>
      <div className="page-content">
        {/* Training Requests */}
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 'var(--space-4)' }}>Yêu cầu Training</h2>
        {requests.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-muted)' }}>
            Chưa có yêu cầu training nào
          </div>
        ) : (
          <div className="table-container" style={{ marginBottom: 'var(--space-8)' }}>
            <table>
              <thead><tr><th>Voice</th><th>Set</th><th>Status</th><th>Progress</th><th>Actions</th></tr></thead>
              <tbody>
                {requests.map(req => (
                  <tr key={req.id}>
                    <td style={{ fontWeight: 600 }}>{req.voice_name}</td>
                    <td>{req.sentence_set_id}</td>
                    <td><span className={`badge badge-${req.status}`}>{req.status}</span></td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div className="progress-bar" style={{ width: 100 }}>
                          <div className="progress-fill" style={{ width: `${req.progress}%` }} />
                        </div>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{req.progress}%</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                        {req.status === 'pending' && (
                          <button className="btn btn-danger btn-sm" onClick={() => cancelRequest(req.id)}>Hủy</button>
                        )}
                        {req.status === 'failed' && <span style={{ fontSize: 12, color: 'var(--danger)' }}>❌ Failed</span>}
                        <button className="btn btn-ghost btn-sm" onClick={() => cancelRequest(req.id)} title="Xóa">🗑️</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Trained Voices */}
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 'var(--space-4)' }}>Giọng đã Training</h2>
        {voices.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: 'var(--space-8)', color: 'var(--text-muted)' }}>
            Chưa có voice nào được train
          </div>
        ) : (
          <div className="grid-3">
            {voices.map(v => (
              <div key={v.id} className="card">
                <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>{v.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-3)' }}>
                  Training #{v.training_request_id}
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => renameVoice(v.id, v.name)}>✏️ Rename</button>
                  <button className="btn btn-danger btn-sm" onClick={() => deleteVoice(v.id)}>🗑️</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {showForm && <SubmitForm sets={sets} baseModels={baseModels} onClose={() => setShowForm(false)} onDone={() => { setShowForm(false); load(); }} />}
      </div>
    </>
  );
}

function SubmitForm({ sets, baseModels, onClose, onDone }) {
  const [voiceName, setVoiceName] = useState('');
  const [setId, setSetId] = useState('');
  const [baseModel, setBaseModel] = useState(baseModels.length ? baseModels[0].name : '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const toast = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      await api.submitTraining({ voice_name: voiceName, set_id: parseInt(setId), base_model: baseModel });
      toast.success('Đã gửi yêu cầu training!');
      onDone();
    } catch (err) { setError(err.message); }
    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">Gửi yêu cầu Training</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Tên giọng nói</label>
            <input className="input" value={voiceName} onChange={e => setVoiceName(e.target.value)} required placeholder="VD: Giọng Minh" />
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Bộ câu đã thu</label>
            <select className="select" value={setId} onChange={e => setSetId(e.target.value)} required>
              <option value="">-- Chọn bộ câu --</option>
              {sets.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Base Model</label>
            <select className="select" value={baseModel} onChange={e => setBaseModel(e.target.value)} required>
              {baseModels.map(m => <option key={m.name} value={m.name}>{m.name} — {m.description}</option>)}
            </select>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
            ⚠️ Cần thu âm ít nhất 10 câu. Admin sẽ duyệt trước khi bắt đầu training.
          </div>
          {error && <div className="form-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Gửi yêu cầu'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
