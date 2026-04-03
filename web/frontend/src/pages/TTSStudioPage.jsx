import { useNavigate } from 'react-router-dom';

export default function TTSStudioPage() {
  const navigate = useNavigate();

  return (
    <>
      <div className="topbar"><h1>🎙️ TTS Studio</h1></div>
      <div className="page-content" style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', minHeight: '60vh', textAlign: 'center',
      }}>
        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 24, padding: '48px 64px',
          border: '1px solid var(--border)', maxWidth: 500,
        }}>
          <div style={{ fontSize: 64, marginBottom: 'var(--space-4)' }}>🚧</div>
          <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 'var(--space-3)', color: 'var(--text-primary)' }}>
            Coming Soon
          </h2>
          <p style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: 'var(--space-5)' }}>
            VieNeu TTS Studio đang được nâng cấp lên phiên bản mới.<br />
            Trong thời gian này, hãy sử dụng <strong style={{ color: 'var(--accent)' }}>OmniVoice</strong> — 
            hỗ trợ 600+ ngôn ngữ với chất lượng cao hơn.
          </p>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/omnivoice')}
            style={{ padding: '12px 32px', fontSize: 14, borderRadius: 12 }}>
            🌍 Dùng OmniVoice ngay
          </button>
        </div>
      </div>
    </>
  );
}
