import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

const TAB_MAP = { '/admin': 'overview', '/admin/queue': 'training', '/admin/sets': 'sets' };
const PATH_MAP = { overview: '/admin', training: '/admin/queue', sets: '/admin/sets', users: '/admin' };

export default function AdminDashboardPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [tab, setTab] = useState(TAB_MAP[location.pathname] || 'overview');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [queue, setQueue] = useState([]);
  const [sets, setSets] = useState([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  // Sync tab with URL
  useEffect(() => {
    const t = TAB_MAP[location.pathname];
    if (t && t !== tab) setTab(t);
  }, [location.pathname]);

  const switchTab = (t) => {
    setTab(t);
    const path = PATH_MAP[t] || '/admin';
    if (location.pathname !== path) navigate(path);
  };

  const loadStats = async () => {
    try { setStats(await api.getAdminStats()); } catch (err) { console.error('Stats error:', err); }
  };
  const loadUsers = async () => {
    try { setUsers(await api.getAdminUsers()); } catch (err) { console.error('Users error:', err); }
  };
  const loadQueue = async () => {
    try { setQueue(await api.getTrainingQueue(filter)); } catch (err) { console.error('Queue error:', err); }
  };
  const loadSets = async () => {
    try { setSets(await api.getSets()); } catch (err) { console.error('Sets error:', err); }
  };

  useEffect(() => {
    Promise.all([loadStats(), loadUsers(), loadQueue(), loadSets()]).finally(() => setLoading(false));
    const i = setInterval(() => { loadStats(); loadQueue(); }, 10000);
    return () => clearInterval(i);
  }, []);
  useEffect(() => { loadQueue(); }, [filter]);

  const approve = async (id) => {
    try { await api.approveTraining(id); toast.success('Đã approve'); loadQueue(); }
    catch (err) { toast.error(err.message); }
  };
  const reject = async (id) => {
    if (!confirm('Reject yêu cầu này?')) return;
    try { await api.rejectTraining(id); toast.success('Đã reject'); loadQueue(); }
    catch (err) { toast.error(err.message); }
  };
  const start = async (id) => {
    const modelStr = prompt('Chọn base model:\n1. VieNeu-TTS-0.3B (nhẹ, train nhanh)\n2. VieNeu-TTS-0.5B (chất lượng cao)\n\nNhập 1 hoặc 2:', '1');
    if (!modelStr) return;
    const baseModels = { '1': 'pnnbao-ump/VieNeu-TTS-0.3B', '2': 'pnnbao-ump/VieNeu-TTS' };
    const baseModel = baseModels[modelStr.trim()];
    if (!baseModel) { toast.error('Chọn 1 hoặc 2'); return; }

    const stepsStr = prompt('Số bước training (100-50000):', '5000');
    if (!stepsStr) return;
    const maxSteps = parseInt(stepsStr);
    if (isNaN(maxSteps) || maxSteps < 100 || maxSteps > 50000) {
      toast.error('Số bước phải từ 100 đến 50000');
      return;
    }
    const gpuStr = prompt('GPU ID (0 hoặc 1, để trống = mặc định):', '1');
    const gpuId = gpuStr !== null && gpuStr.trim() !== '' ? parseInt(gpuStr) : null;
    try {
      await api.startTraining(id, maxSteps, gpuId, baseModel);
      const modelName = modelStr.trim() === '1' ? '0.3B' : '0.5B';
      toast.success(`Đã bắt đầu training ${modelName} (${maxSteps} steps, GPU ${gpuId ?? 'default'})`);
      loadQueue();
    } catch (err) { toast.error(err.message); }
  };
  const del = async (id) => {
    if (!confirm('Xóa training request này?')) return;
    try { await api.deleteTraining(id); toast.success('Đã xóa'); loadQueue(); }
    catch (err) { toast.error(err.message); }
  };

  if (loading) return <div className="loading-page"><span className="spinner" /> Loading admin...</div>;

  return (
    <>
      <div className="topbar">
        <h1>Admin Dashboard</h1>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          {[['overview','📊 Tổng quan'],['users','👥 Users'],['training','🧪 Training'],['sets','📝 Sentences']].map(([t, label]) => (
            <button key={t} className="btn btn-sm"
              style={{
                background: tab === t ? 'var(--accent)' : 'transparent',
                color: tab === t ? 'white' : 'var(--text-secondary)',
                border: tab === t ? 'none' : '1px solid var(--border)',
              }}
              onClick={() => switchTab(t)}>
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="page-content">
        {tab === 'overview' && <OverviewTab stats={stats} queue={queue} users={users} />}
        {tab === 'users' && <UsersTab users={users} onReload={loadUsers} />}
        {tab === 'training' && <TrainingTab queue={queue} filter={filter} setFilter={setFilter}
          approve={approve} reject={reject} start={start} onDelete={del} />}
        {tab === 'sets' && <SetsTab sets={sets} onReload={loadSets} />}
      </div>
    </>
  );
}

/* ─── Overview Tab ───────────────────────────────── */
function OverviewTab({ stats, queue, users }) {
  if (!stats) return <div style={{ color: 'var(--text-muted)' }}>Không tải được thống kê</div>;
  const cards = [
    { label: 'Users', value: stats.users, icon: '👥', color: '#6366f1' },
    { label: 'Synthesis', value: stats.synths, icon: '🔊', color: '#10b981' },
    { label: 'Ref Audio', value: stats.refs, icon: '🎙️', color: '#f59e0b' },
    { label: 'Training', value: stats.training_total, icon: '🧪', color: '#ef4444' },
  ];
  const trainCards = [
    { label: 'Chờ duyệt', value: stats.training_pending, color: 'var(--warning)' },
    { label: 'Đang train', value: stats.training_active, color: 'var(--accent)' },
    { label: 'Hoàn thành', value: stats.training_done, color: 'var(--success)' },
  ];

  return (
    <>
      {/* Main stats */}
      <div className="stats-grid" style={{ marginBottom: 'var(--space-6)' }}>
        {cards.map(c => (
          <div key={c.label} className="card stat-card" style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 28, marginBottom: 4 }}>{c.icon}</div>
            <div className="stat-value" style={{ color: c.color }}>{c.value}</div>
            <div className="stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Training breakdown */}
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 'var(--space-4)' }}>🧪 Training Queue</h2>
      <div className="stats-grid" style={{ marginBottom: 'var(--space-6)' }}>
        {trainCards.map(c => (
          <div key={c.label} className="card stat-card">
            <div className="stat-value" style={{ color: c.color }}>{c.value}</div>
            <div className="stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Model Selector */}
      <ModelSelector />

      {/* Recent users */}
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 'var(--space-4)' }}>👥 Users gần đây</h2>
      <div className="table-container">
        <table>
          <thead><tr><th>Email</th><th>Tên</th><th>Role</th><th>Ngày tạo</th></tr></thead>
          <tbody>
            {users.slice(0, 5).map(u => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td>{u.name || '—'}</td>
                <td><span className={`badge badge-${u.role}`}>{u.role}</span></td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.created_at ? new Date(u.created_at).toLocaleDateString('vi') : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* ─── Model Selector ─────────────────────────────── */
function ModelSelector() {
  const [status, setStatus] = useState(null);
  const [switching, setSwitching] = useState(false);
  const toast = useToast();

  const loadStatus = async () => {
    try { setStatus(await api.getModels()); } catch (err) { console.error(err); }
  };

  useEffect(() => { loadStatus(); }, []);

  // Poll while loading
  useEffect(() => {
    if (!status?.is_loading) return;
    const interval = setInterval(async () => {
      try {
        const s = await api.getModelStatus();
        setStatus(s);
        if (!s.is_loading) {
          clearInterval(interval);
          setSwitching(false);
          if (s.error) toast.error('Lỗi nạp model: ' + s.error);
          else toast.success('✅ Model đã sẵn sàng!');
        }
      } catch (err) { console.error(err); }
    }, 2000);
    return () => clearInterval(interval);
  }, [status?.is_loading]);

  const handleSwitch = async (repo) => {
    if (repo === status?.current_model) return;
    setSwitching(true);
    try {
      await api.switchModel(repo);
      // Immediately update local state to show loading
      setStatus(prev => ({ ...prev, is_loading: true }));
    } catch (err) { toast.error(err.message); setSwitching(false); }
  };

  if (!status) return null;

  return (
    <>
      <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 'var(--space-4)' }}>🧠 Model TTS</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-6)' }}>
        {status.available_models?.map(m => {
          const isCurrent = m.repo === status.current_model;
          return (
            <div key={m.repo} className="card" style={{
              padding: 'var(--space-4)',
              border: isCurrent ? '2px solid var(--accent)' : '1px solid var(--border)',
              position: 'relative',
              opacity: switching && !isCurrent ? 0.6 : 1,
            }}>
              {isCurrent && (
                <span style={{
                  position: 'absolute', top: 8, right: 8, fontSize: 10, fontWeight: 700,
                  background: 'var(--accent)', color: 'white', padding: '2px 8px', borderRadius: 10,
                }}>ACTIVE</span>
              )}
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{m.name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, lineHeight: 1.4 }}>{m.description}</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                <span className="badge" style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8', fontSize: 10 }}>{m.format}</span>
                <span className="badge" style={{ background: 'rgba(16,185,129,0.15)', color: '#34d399', fontSize: 10 }}>{m.size_mb}MB</span>
                <span className="badge" style={{ background: m.device === 'gpu' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)', color: m.device === 'gpu' ? '#f87171' : '#fbbf24', fontSize: 10 }}>{m.device.toUpperCase()}</span>
              </div>
              {!isCurrent && (
                <button className="btn btn-primary btn-sm" onClick={() => handleSwitch(m.repo)} disabled={switching}
                  style={{ width: '100%' }}>
                  {switching ? '⏳ Đang chuyển...' : '🔄 Sử dụng model này'}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Loading overlay */}
      {status.is_loading && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', zIndex: 9999,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          backdropFilter: 'blur(4px)',
        }}>
          <div style={{
            background: 'var(--bg-primary)', padding: 'var(--space-8)', borderRadius: 16,
            textAlign: 'center', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
          }}>
            <div style={{ fontSize: 48, marginBottom: 'var(--space-4)', animation: 'spin 2s linear infinite' }}>🧠</div>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 'var(--space-2)' }}>Đang nạp model...</h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 'var(--space-4)' }}>
              Vui lòng chờ, hệ thống đang tải và nạp model vào bộ nhớ.
              <br />Quá trình này có thể mất 10-30 giây.
            </p>
            <span className="spinner" style={{ width: 32, height: 32 }} />
          </div>
        </div>
      )}
    </>
  );
}

/* ─── Users Tab ──────────────────────────────────── */
function UsersTab({ users, onReload }) {
  const [showAdd, setShowAdd] = useState(false);
  const [editId, setEditId] = useState(null);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [deletePreview, setDeletePreview] = useState(null);
  const toast = useToast();

  const handleDelete = async (u) => {
    try {
      const preview = await api.previewDeleteUser(u.id);
      setDeletePreview(preview);
    } catch (err) { toast.error(err.message); }
  };

  const confirmDelete = async () => {
    if (!deletePreview) return;
    try {
      await api.deleteAdminUser(deletePreview.user.id);
      toast.success('Đã xóa user và dữ liệu liên quan');
      setDeletePreview(null);
      onReload();
    } catch (err) { toast.error(err.message); }
  };

  const startEdit = (u) => {
    setEditId(u.id);
    setEditData({ name: u.name, role: u.role, is_active: u.is_active, password: '' });
  };

  const saveEdit = async () => {
    setSaving(true);
    try {
      const body = { name: editData.name, role: editData.role, is_active: editData.is_active };
      if (editData.password) body.password = editData.password;
      await api.updateAdminUser(editId, body);
      toast.success('Đã cập nhật');
      setEditId(null);
      onReload();
    } catch (err) { toast.error(err.message); }
    setSaving(false);
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Tất cả Users ({users.length})</h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(true)}>+ Thêm User</button>
      </div>
      <div className="table-container">
        <table>
          <thead><tr><th>Email</th><th>Tên</th><th>Role</th><th>Trạng thái</th><th>Ngày tạo</th><th>Actions</th></tr></thead>
          <tbody>
            {users.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Không có user</td></tr>
            ) : users.map(u => (
              <tr key={u.id}>
                <td style={{ fontWeight: 600 }}>{u.email}</td>
                {editId === u.id ? (
                  <>
                    <td><input className="input" value={editData.name} onChange={e => setEditData(d => ({ ...d, name: e.target.value }))} style={{ height: 30, fontSize: 13 }} /></td>
                    <td>
                      <select className="select" value={editData.role} onChange={e => setEditData(d => ({ ...d, role: e.target.value }))} style={{ height: 30, fontSize: 13 }}>
                        <option value="user">user</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13 }}>
                        <input type="checkbox" checked={editData.is_active} onChange={e => setEditData(d => ({ ...d, is_active: e.target.checked }))} />
                        Active
                      </label>
                    </td>
                    <td>
                      <input className="input" type="password" placeholder="Mật khẩu mới (bỏ trống = giữ)" value={editData.password}
                        onChange={e => setEditData(d => ({ ...d, password: e.target.value }))} style={{ height: 30, fontSize: 13, width: 140 }} />
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="btn btn-primary btn-sm" onClick={saveEdit} disabled={saving}>💾</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => setEditId(null)}>✕</button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td>{u.name || '—'}</td>
                    <td><span className={`badge badge-${u.role}`}>{u.role}</span></td>
                    <td>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', marginRight: 6,
                        background: u.is_active ? 'var(--success)' : 'var(--text-muted)' }} />
                      {u.is_active ? 'Active' : 'Inactive'}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.created_at ? new Date(u.created_at).toLocaleString('vi') : '—'}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => startEdit(u)} title="Sửa">✏️</button>
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(u)} title="Xóa">🗑️</button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAdd && <AddUserModal onClose={() => setShowAdd(false)} onDone={() => { setShowAdd(false); onReload(); }} />}
      {deletePreview && <DeleteConfirmModal preview={deletePreview} onClose={() => setDeletePreview(null)} onConfirm={confirmDelete} />}
    </>
  );
}

/* ─── Delete Confirm Modal ────────────────────────── */
const DATA_LABELS = {
  training_requests: { icon: '🧪', label: 'Training requests' },
  trained_voices:    { icon: '🎤', label: 'Trained voices' },
  recordings:        { icon: '🎙️', label: 'Recordings' },
  references:        { icon: '📎', label: 'Reference audio' },
  api_keys:          { icon: '🔑', label: 'API keys' },
  synthesis_history: { icon: '🔊', label: 'Synthesis history' },
};

function DeleteConfirmModal({ preview, onClose, onConfirm }) {
  const [confirming, setConfirming] = useState(false);
  const { user, related_data, total_records } = preview;
  const hasData = total_records > 0;

  const doConfirm = async () => {
    setConfirming(true);
    await onConfirm();
    setConfirming(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 460 }}>
        <h2 className="modal-title" style={{ color: hasData ? 'var(--danger, #ef4444)' : 'var(--text-primary)' }}>
          {hasData ? '⚠️ Xóa user có dữ liệu' : '🗑️ Xóa user'}
        </h2>

        <div style={{ padding: 'var(--space-3)', background: 'var(--bg-secondary)', borderRadius: 8, marginBottom: 'var(--space-4)' }}>
          <div style={{ fontWeight: 600 }}>{user.email}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{user.name} • {user.role}</div>
        </div>

        {hasData ? (
          <>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-3)' }}>
              User này có <strong>{total_records} bản ghi</strong> liên quan sẽ bị xóa vĩnh viễn:
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 'var(--space-4)' }}>
              {Object.entries(related_data).filter(([, v]) => v > 0).map(([key, count]) => (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '6px 12px', background: 'var(--bg-tertiary, rgba(255,255,255,0.05))', borderRadius: 6, fontSize: 13 }}>
                  <span>{DATA_LABELS[key]?.icon} {DATA_LABELS[key]?.label || key}</span>
                  <span style={{ fontWeight: 700, color: 'var(--danger, #ef4444)' }}>{count}</span>
                </div>
              ))}
            </div>
            <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.1)', borderRadius: 6, fontSize: 12, color: 'var(--danger, #ef4444)', marginBottom: 'var(--space-4)' }}>
              ⚠️ Hành động này không thể hoàn tác. Tất cả dữ liệu sẽ bị xóa vĩnh viễn.
            </div>
          </>
        ) : (
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
            User này không có dữ liệu liên quan. Có thể xóa an toàn.
          </p>
        )}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Hủy</button>
          <button type="button" className="btn btn-danger" onClick={doConfirm} disabled={confirming}>
            {confirming ? <span className="spinner" /> : hasData ? `Xóa user + ${total_records} bản ghi` : 'Xóa user'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Add User Modal ──────────────────────────────── */
function AddUserModal({ onClose, onDone }) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('user');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const toast = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) { setError('Email và mật khẩu bắt buộc'); return; }
    setLoading(true); setError('');
    try {
      await api.createAdminUser({ email, name: name || undefined, password, role });
      toast.success('Đã tạo user!');
      onDone();
    } catch (err) { setError(err.message); }
    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 440 }}>
        <h2 className="modal-title">Thêm User mới</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Email *</label>
            <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="user@example.com" />
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Tên</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="Họ tên" />
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Mật khẩu *</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Tối thiểu 6 ký tự" />
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Role</label>
            <select className="select" value={role} onChange={e => setRole(e.target.value)}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          {error && <div className="form-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Tạo User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Training Tab ───────────────────────────────── */
function TrainingTab({ queue, filter, setFilter, approve, reject, start, onDelete }) {
  const [logReqId, setLogReqId] = useState(null);

  return (
    <>
      <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', alignItems: 'center' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Training Queue ({queue.length})</h2>
        <select className="select" value={filter} onChange={e => setFilter(e.target.value)} style={{ width: 160, marginLeft: 'auto' }}>
          <option value="">Tất cả</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="training">Training</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <div className="table-container">
        <table>
          <thead><tr><th>User</th><th>Voice</th><th>Base Model</th><th>Status</th><th>Progress</th><th>Submitted</th><th>Actions</th></tr></thead>
          <tbody>
            {queue.length === 0 ? (
              <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Không có request</td></tr>
            ) : queue.map(req => (
              <tr key={req.id}>
                <td style={{ fontSize: 13 }}>{req.user_email || req.user_id?.toString().slice(0, 8) + '...' || '—'}</td>
                <td style={{ fontWeight: 600 }}>{req.voice_name}</td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{req.base_model_path?.split('/').pop() || '—'}</td>
                <td><span className={`badge badge-${req.status}`}>{req.status}</span></td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div className="progress-bar" style={{ width: 80 }}>
                      <div className="progress-fill" style={{ width: `${req.progress}%` }} />
                    </div>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{req.progress}%</span>
                  </div>
                </td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(req.submitted_at).toLocaleString('vi')}</td>
                <td>
                  <div style={{ display: 'flex', gap: 'var(--space-1)', flexWrap: 'wrap' }}>
                    {req.status === 'pending' && (
                      <>
                        <button className="btn btn-primary btn-sm" onClick={() => approve(req.id)}>✅</button>
                        <button className="btn btn-danger btn-sm" onClick={() => reject(req.id)}>❌</button>
                      </>
                    )}
                    {req.status === 'approved' && (
                      <button className="btn btn-primary btn-sm" onClick={() => start(req.id)}>▶ Start</button>
                    )}
                    {req.status === 'training' && <span style={{ fontSize: 12, color: 'var(--accent)' }}>⏳ Training...</span>}
                    {req.status === 'completed' && <span style={{ fontSize: 12, color: 'var(--success)' }}>✅ Done</span>}
                    {req.status === 'rejected' && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>🚫</span>}
                    {req.status === 'failed' && <span style={{ fontSize: 12, color: 'var(--danger)' }}>❌ Failed</span>}

                    {/* Log button — show for training, completed, failed */}
                    {['training', 'completed', 'failed'].includes(req.status) && (
                      <button className="btn btn-secondary btn-sm" onClick={() => setLogReqId(req.id)}
                        title="Xem log training" style={{ fontSize: 11, padding: '2px 8px' }}>
                        📋 Log
                      </button>
                    )}

                    <button className="btn btn-ghost btn-sm" onClick={() => onDelete(req.id)} title="Xóa" style={{ marginLeft: 4 }}>🗑️</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {logReqId && <TrainingLogModal requestId={logReqId} onClose={() => setLogReqId(null)}
        isTraining={queue.find(q => q.id === logReqId)?.status === 'training'} />}
    </>
  );
}

/* ─── Training Log Modal ─────────────────────────── */
function TrainingLogModal({ requestId, onClose, isTraining }) {
  const [log, setLog] = useState('Loading...');
  const [loading, setLoading] = useState(true);
  const [tail, setTail] = useState(200);
  const logRef = useState(null);

  const loadLog = async (lines) => {
    try {
      const text = await api.getTrainingLog(requestId, lines || tail);
      setLog(text);
    } catch (err) {
      setLog(`[Error: ${err.message}]`);
    }
    setLoading(false);
  };

  useEffect(() => { loadLog(); }, [requestId, tail]);

  // Auto-refresh every 3s if training is in progress
  useEffect(() => {
    if (!isTraining) return;
    const interval = setInterval(() => loadLog(), 3000);
    return () => clearInterval(interval);
  }, [isTraining, tail]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (logRef[0]) logRef[0].scrollTop = logRef[0].scrollHeight;
  }, [log]);

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 9999 }}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{
        maxWidth: 900, width: '95vw', maxHeight: '90vh', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
          <h2 className="modal-title" style={{ margin: 0 }}>
            📋 Training Log — Request #{requestId}
            {isTraining && <span style={{
              fontSize: 11, background: 'var(--accent)', color: 'white',
              padding: '2px 8px', borderRadius: 10, marginLeft: 8, animation: 'pulse 2s infinite',
            }}>LIVE</span>}
          </h2>
          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
            <select className="select" value={tail} onChange={e => setTail(Number(e.target.value))}
              style={{ width: 120, height: 30, fontSize: 12 }}>
              <option value={100}>100 dòng</option>
              <option value={200}>200 dòng</option>
              <option value={500}>500 dòng</option>
              <option value={2000}>2000 dòng</option>
              <option value={5000}>Full log</option>
            </select>
            <button className="btn btn-secondary btn-sm" onClick={() => loadLog()}>🔄</button>
            <button className="btn btn-ghost btn-sm" onClick={onClose} style={{ fontSize: 18 }}>✕</button>
          </div>
        </div>

        <pre ref={el => { logRef[0] = el; }} style={{
          flex: 1, overflow: 'auto', background: '#0d1117', color: '#c9d1d9',
          padding: 'var(--space-4)', borderRadius: 8, fontSize: 12, lineHeight: 1.6,
          fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
          whiteSpace: 'pre-wrap', wordBreak: 'break-all', minHeight: 300, maxHeight: '60vh',
          border: '1px solid rgba(99, 102, 241, 0.2)',
        }}>
          {loading ? <span style={{ color: '#8b949e' }}>⏳ Loading log...</span> : log}
        </pre>

        {isTraining && (
          <div style={{
            marginTop: 'var(--space-2)', fontSize: 11, color: 'var(--text-muted)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span className="spinner" style={{ width: 12, height: 12 }} />
            Auto-refresh mỗi 3 giây...
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Sets Tab ───────────────────────────────────── */
function SetsTab({ sets, onReload }) {
  const [expanded, setExpanded] = useState(null);
  const [setDetail, setSetDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [editSentId, setEditSentId] = useState(null);
  const [editSentText, setEditSentText] = useState('');
  const [addingTo, setAddingTo] = useState(null);
  const [newText, setNewText] = useState('');
  const toast = useToast();

  const loadDetail = async (id) => {
    setLoadingDetail(true);
    try { setSetDetail(await api.getSet(id)); }
    catch (err) { toast.error(err.message); }
    setLoadingDetail(false);
  };

  const toggleExpand = async (id) => {
    if (expanded === id) { setExpanded(null); setSetDetail(null); return; }
    setExpanded(id);
    await loadDetail(id);
  };

  const deleteSet = async (id) => {
    if (!confirm('Xóa sentence set này?')) return;
    try { await api.deleteSet(id); toast.success('Đã xóa'); onReload(); }
    catch (err) { toast.error(err.message); }
  };

  const startEditSent = (s) => { setEditSentId(s.id); setEditSentText(s.text); };

  const saveEditSent = async () => {
    if (!editSentText.trim()) return;
    try {
      await api.updateSentence(editSentId, { text: editSentText.trim() });
      toast.success('Đã cập nhật');
      setEditSentId(null);
      await loadDetail(expanded);
      onReload();
    } catch (err) { toast.error(err.message); }
  };

  const deleteSent = async (sentId) => {
    if (!confirm('Xóa đoạn này?')) return;
    try {
      await api.deleteSentence(sentId);
      toast.success('Đã xóa đoạn');
      await loadDetail(expanded);
      onReload();
    } catch (err) { toast.error(err.message); }
  };

  const addSent = async (setId) => {
    if (!newText.trim()) return;
    try {
      await api.addSentence(setId, { text: newText.trim() });
      toast.success('Đã thêm đoạn');
      setNewText('');
      setAddingTo(null);
      await loadDetail(setId);
      onReload();
    } catch (err) { toast.error(err.message); }
  };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700 }}>Sentence Sets ({sets.length})</h2>
      </div>

      {sets.length === 0 ? (
        <div className="empty-state"><p>Chưa có sentence set nào</p></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
          {sets.map(s => (
            <div key={s.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
              {/* Header */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: 'var(--space-4)', cursor: 'pointer',
              }} onClick={() => toggleExpand(s.id)}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{s.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                    {s.language?.toUpperCase() || 'VI'} • {s.sentence_count ?? '?'} đoạn
                    {s.created_at && ` • ${new Date(s.created_at).toLocaleDateString('vi')}`}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center' }}>
                  <button className="btn btn-danger btn-sm" onClick={e => { e.stopPropagation(); deleteSet(s.id); }}>🗑️</button>
                  <span style={{ fontSize: 16, color: 'var(--text-muted)', transition: 'transform 0.2s', transform: expanded === s.id ? 'rotate(180deg)' : 'none' }}>▼</span>
                </div>
              </div>

              {/* Expanded sentences */}
              {expanded === s.id && (
                <div style={{ borderTop: '1px solid var(--border)', padding: 'var(--space-4)', background: 'var(--bg-secondary)' }}>
                  {loadingDetail ? <span className="spinner" /> : (
                    <>
                      {setDetail?.sentences?.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {setDetail.sentences.map((sent, i) => (
                            <div key={sent.id || i} style={{
                              display: 'flex', gap: 8, fontSize: 13, padding: '6px 8px',
                              background: editSentId === sent.id ? 'var(--bg-tertiary, rgba(255,255,255,0.05))' : 'transparent',
                              borderRadius: 6, alignItems: 'flex-start',
                            }}>
                              <span style={{ color: 'var(--text-muted)', minWidth: 28, fontWeight: 600, paddingTop: 2 }}>{i + 1}.</span>

                              {editSentId === sent.id ? (
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                  <textarea className="input" value={editSentText} onChange={e => setEditSentText(e.target.value)}
                                    style={{ fontSize: 13, minHeight: 60, resize: 'vertical' }} />
                                  <div style={{ display: 'flex', gap: 4 }}>
                                    <button className="btn btn-primary btn-sm" onClick={saveEditSent}>💾 Lưu</button>
                                    <button className="btn btn-secondary btn-sm" onClick={() => setEditSentId(null)}>✕ Hủy</button>
                                  </div>
                                </div>
                              ) : (
                                <>
                                  <span style={{ flex: 1, lineHeight: 1.5 }}>{sent.text}</span>
                                  <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                                    <button className="btn btn-secondary btn-sm" onClick={() => startEditSent(sent)} title="Sửa" style={{ padding: '2px 6px', fontSize: 11 }}>✏️</button>
                                    <button className="btn btn-danger btn-sm" onClick={() => deleteSent(sent.id)} title="Xóa" style={{ padding: '2px 6px', fontSize: 11 }}>🗑️</button>
                                  </div>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Không có đoạn nào</div>}

                      {/* Add sentence */}
                      <div style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--border)', paddingTop: 'var(--space-3)' }}>
                        {addingTo === s.id ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <textarea className="input" placeholder="Nhập nội dung đoạn mới (3-5 câu)..." value={newText}
                              onChange={e => setNewText(e.target.value)} style={{ fontSize: 13, minHeight: 60, resize: 'vertical' }} />
                            <div style={{ display: 'flex', gap: 4 }}>
                              <button className="btn btn-primary btn-sm" onClick={() => addSent(s.id)}>➕ Thêm</button>
                              <button className="btn btn-secondary btn-sm" onClick={() => { setAddingTo(null); setNewText(''); }}>Hủy</button>
                            </div>
                          </div>
                        ) : (
                          <button className="btn btn-secondary btn-sm" onClick={() => setAddingTo(s.id)}>
                            ➕ Thêm đoạn mới
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
