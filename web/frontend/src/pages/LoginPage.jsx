import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      if (isRegister) {
        await register(email, password, name);
        toast.success('Đăng ký thành công!');
      } else {
        await login(email, password);
        toast.success('Đăng nhập thành công!');
      }
      navigate('/studio');
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card glass-card">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" style={{ margin: '0 auto 12px', display: 'block' }}>
          <rect x="2" y="8" width="2" height="8" rx="1" fill="#6366f1" opacity="0.4"/>
          <rect x="6" y="5" width="2" height="14" rx="1" fill="#6366f1" opacity="0.6"/>
          <rect x="10" y="3" width="2" height="18" rx="1" fill="#6366f1"/>
          <rect x="14" y="5" width="2" height="14" rx="1" fill="#6366f1" opacity="0.6"/>
          <rect x="18" y="8" width="2" height="8" rx="1" fill="#6366f1" opacity="0.4"/>
        </svg>
        <h1>VieNeu TTS</h1>
        <p>Vietnamese Text-to-Speech Platform</p>

        <form onSubmit={handleSubmit}>
          {isRegister && (
            <div className="form-group">
              <input className="input" placeholder="Họ tên" value={name}
                onChange={e => setName(e.target.value)} required />
            </div>
          )}
          <div className="form-group">
            <input className="input" type="email" placeholder="Email" value={email}
              onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <input className="input" type="password" placeholder="Mật khẩu" value={password}
              onChange={e => setPassword(e.target.value)} required minLength={6} />
          </div>

          {error && <div className="form-error" style={{ textAlign: 'center', marginTop: 8 }}>{error}</div>}

          <button className="btn btn-primary btn-block btn-lg" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : (isRegister ? 'Đăng ký' : 'Đăng nhập')}
          </button>
        </form>

        <div className="login-footer">
          {isRegister ? (
            <>Đã có tài khoản? <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(false); setError(''); }}>Đăng nhập</a></>
          ) : (
            <>Chưa có tài khoản? <a href="#" onClick={(e) => { e.preventDefault(); setIsRegister(true); setError(''); }}>Đăng ký</a></>
          )}
        </div>
      </div>
    </div>
  );
}
