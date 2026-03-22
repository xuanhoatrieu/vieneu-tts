import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { to: '/studio',    icon: '🎙️', label: 'TTS Studio' },
  { to: '/voices',    icon: '📚', label: 'Voice Library' },
  { to: '/recording', icon: '🎤', label: 'Recording Studio' },
  { to: '/training',  icon: '🏋️', label: 'Training' },
  { to: '/api-keys',  icon: '🔑', label: 'API Keys' },
];

const adminItems = [
  { to: '/admin',     icon: '📊', label: 'Dashboard' },
  { to: '/admin/queue', icon: '📋', label: 'Training Queue' },
  { to: '/admin/sets',  icon: '📝', label: 'Sentence Sets' },
];

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  const initials = user?.name
    ? user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : '?';

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect x="2" y="8" width="2" height="8" rx="1" fill="currentColor" opacity="0.4"/>
            <rect x="6" y="5" width="2" height="14" rx="1" fill="currentColor" opacity="0.6"/>
            <rect x="10" y="3" width="2" height="18" rx="1" fill="currentColor"/>
            <rect x="14" y="5" width="2" height="14" rx="1" fill="currentColor" opacity="0.6"/>
            <rect x="18" y="8" width="2" height="8" rx="1" fill="currentColor" opacity="0.4"/>
          </svg>
          <span>VieNeu TTS</span>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}

          {isAdmin && (
            <>
              <div style={{ height: 1, background: 'var(--border)', margin: '8px 12px' }} />
              <div style={{ padding: '4px 16px', fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>
                Admin
              </div>
              {adminItems.map(item => (
                <NavLink key={item.to} to={item.to} end={item.to === '/admin'}
                  className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
                  <span style={{ fontSize: 16 }}>{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </>
          )}
        </nav>

        <div className="sidebar-user">
          <div className="sidebar-avatar">{initials}</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.name}</div>
            <div className="sidebar-user-email">{user?.email}</div>
          </div>
          <button className="btn-ghost" onClick={handleLogout} title="Đăng xuất"
            style={{ marginLeft: 'auto', fontSize: 16, padding: 4 }}>⏻</button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
