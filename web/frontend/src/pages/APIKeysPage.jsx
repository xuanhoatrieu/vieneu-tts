import { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function APIKeysPage() {
  const [keys, setKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const load = async () => {
    try { setKeys(await api.getApiKeys()); } catch {} finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const createKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    try {
      const data = await api.createApiKey(newKeyName);
      setCreatedKey(data.key);
      setNewKeyName('');
      toast.success('API key đã tạo!');
      load();
    } catch (err) { toast.error(err.message); }
  };

  const deleteKey = async (id) => {
    if (!confirm('Xóa API key này?')) return;
    try { await api.deleteApiKey(id); toast.success('Đã xóa'); load(); }
    catch (err) { toast.error(err.message); }
  };

  return (
    <>
      <div className="topbar"><h1>API Keys</h1></div>
      <div className="page-content">
        {/* Create key */}
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--space-4)' }}>Tạo API Key mới</h3>
          <form onSubmit={createKey} style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <input className="input" value={newKeyName} onChange={e => setNewKeyName(e.target.value)}
              placeholder="Tên key (VD: Mobile App)" style={{ maxWidth: 300 }} />
            <button className="btn btn-primary" type="submit">Tạo Key</button>
          </form>

          {createdKey && (
            <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-4)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--success)' }}>
              <div style={{ fontSize: 12, color: 'var(--success)', marginBottom: 4, fontWeight: 600 }}>
                ⚠️ Sao chép ngay — key sẽ không hiển thị lại!
              </div>
              <code style={{ fontFamily: 'var(--font-mono)', fontSize: 13, wordBreak: 'break-all' }}>{createdKey}</code>
              <button className="btn btn-secondary btn-sm" style={{ marginLeft: 'var(--space-3)' }}
                onClick={() => { navigator.clipboard.writeText(createdKey); toast.success('Đã copy!'); }}>
                📋 Copy
              </button>
            </div>
          )}
        </div>

        {/* Key list */}
        {loading ? <div className="loading-page"><span className="spinner" /></div> : (
          <div className="table-container">
            <table>
              <thead><tr><th>Tên</th><th>Prefix</th><th>Tạo lúc</th><th></th></tr></thead>
              <tbody>
                {keys.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Chưa có API key</td></tr>
                ) : keys.map(k => (
                  <tr key={k.id}>
                    <td style={{ fontWeight: 600 }}>{k.name}</td>
                    <td><code style={{ fontFamily: 'var(--font-mono)' }}>{k.key_prefix}...</code></td>
                    <td>{new Date(k.created_at).toLocaleDateString('vi')}</td>
                    <td><button className="btn btn-danger btn-sm" onClick={() => deleteKey(k.id)}>Xóa</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
