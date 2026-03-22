import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

const SAMPLE_SENTENCES = [
  "Tác phẩm dự thi bảo đảm tính khoa học, tính đảng, tính chiến đấu, tính định hướng.",
  "Xin chào, tôi là người Việt Nam. Tôi rất vui được gặp bạn hôm nay.",
  "Hà Nội là thủ đô ngàn năm văn hiến, nơi hội tụ tinh hoa văn hóa dân tộc.",
  "Chúng tôi cam kết mang đến trải nghiệm tốt nhất cho khách hàng và đối tác.",
  "Việt Nam có bờ biển dài hơn ba ngàn cây số, trải dài từ Bắc vào Nam.",
  "Công nghệ trí tuệ nhân tạo đang thay đổi cách chúng ta sống và làm việc.",
];

export default function VoiceLibraryPage() {
  const [refs, setRefs] = useState([]);
  const [showUpload, setShowUpload] = useState(false);
  const [showRecord, setShowRecord] = useState(false);
  const [loading, setLoading] = useState(true);
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(null);
  const toast = useToast();

  const loadRefs = async () => {
    try { setRefs(await api.getRefs()); } catch {} finally { setLoading(false); }
  };
  useEffect(() => { loadRefs(); }, []);

  const handleDelete = async (id) => {
    if (!confirm('Xóa reference audio này?')) return;
    try { await api.deleteRef(id); setRefs(r => r.filter(x => x.id !== id)); toast.success('Đã xóa'); }
    catch (err) { toast.error(err.message); }
  };

  const playRef = (id) => {
    if (playingId === id) { audioRef.current?.pause(); setPlayingId(null); return; }
    const url = api.getRefAudioUrl(id);
    if (audioRef.current) { audioRef.current.src = url; audioRef.current.play(); }
    setPlayingId(id);
  };

  return (
    <>
      <div className="topbar">
        <h1>Voice Library / References</h1>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button className="btn btn-secondary" onClick={() => setShowRecord(true)}>🎙️ Record</button>
          <button className="btn btn-primary" onClick={() => setShowUpload(true)}>+ Upload</button>
        </div>
      </div>
      <div className="page-content">
        <audio ref={audioRef} onEnded={() => setPlayingId(null)} style={{ display: 'none' }} />

        {loading ? (
          <div className="loading-page"><span className="spinner" /> Đang tải...</div>
        ) : refs.length === 0 ? (
          <div className="empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" strokeWidth="1.5"/><path d="M12 8v8M8 12h8" stroke="currentColor" strokeWidth="1.5"/></svg>
            <p>Chưa có reference audio</p>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <button className="btn btn-secondary" onClick={() => setShowRecord(true)}>🎙️ Ghi âm ngay</button>
              <button className="btn btn-primary" onClick={() => setShowUpload(true)}>Upload file</button>
            </div>
          </div>
        ) : (
          <div className="grid-3">
            {refs.map(ref => (
              <div key={ref.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{ref.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{ref.duration_sec?.toFixed(1)}s</div>
                  </div>
                  <span className={`badge badge-${ref.language || 'vi'}`}>{(ref.language || 'vi').toUpperCase()}</span>
                </div>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => playRef(ref.id)}>
                    {playingId === ref.id ? '⏸' : '▶'} Play
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(ref.id)} style={{ marginLeft: 'auto' }}>
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {showUpload && <UploadModal onClose={() => setShowUpload(false)} onDone={() => { setShowUpload(false); loadRefs(); }} />}
        {showRecord && <RecordModal onClose={() => setShowRecord(false)} onDone={() => { setShowRecord(false); loadRefs(); }} />}
      </div>
    </>
  );
}

/* ─── Record Modal ─────────────────────────────── */
function RecordModal({ onClose, onDone }) {
  const [selectedSentence, setSelectedSentence] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedUrl, setRecordedUrl] = useState(null);
  const [name, setName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [duration, setDuration] = useState(0);
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const timerRef = useRef(null);
  const startTime = useRef(null);
  const toast = useToast();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 24000, channelCount: 1, echoCancellation: true, noiseSuppression: true } });
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      chunks.current = [];
      mediaRecorder.current.ondataavailable = (e) => { if (e.data.size > 0) chunks.current.push(e.data); };
      mediaRecorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' });
        setRecordedBlob(blob);
        setRecordedUrl(URL.createObjectURL(blob));
        stream.getTracks().forEach(t => t.stop());
      };
      mediaRecorder.current.start();
      setIsRecording(true);
      setRecordedBlob(null);
      setRecordedUrl(null);
      setDuration(0);
      startTime.current = Date.now();
      timerRef.current = setInterval(() => setDuration(((Date.now() - startTime.current) / 1000)), 100);
    } catch (err) {
      setError('Không thể truy cập microphone. Hãy cho phép trình duyệt truy cập micro.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current?.state === 'recording') {
      mediaRecorder.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const handleUpload = async () => {
    if (!recordedBlob) { setError('Chưa ghi âm'); return; }
    if (!name.trim()) { setError('Nhập tên cho giọng nói'); return; }
    setUploading(true); setError('');
    const fd = new FormData();
    fd.append('audio', recordedBlob, 'recording.webm');
    fd.append('name', name);
    fd.append('language', 'vi');
    fd.append('ref_text', SAMPLE_SENTENCES[selectedSentence]);
    try {
      await api.uploadRef(fd);
      toast.success('Đã lưu reference audio!');
      onDone();
    } catch (err) { setError(err.message); }
    setUploading(false);
  };

  useEffect(() => { return () => { clearInterval(timerRef.current); if (recordedUrl) URL.revokeObjectURL(recordedUrl); }; }, []);

  const formatTime = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}.${Math.floor((s % 1) * 10)}`;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <h2 className="modal-title">🎙️ Ghi âm Reference Audio</h2>

        {/* Step 1: Pick sample sentence */}
        <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
          <label className="form-label">Câu mẫu — đọc to câu bên dưới</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {SAMPLE_SENTENCES.map((s, i) => (
              <button key={i} onClick={() => setSelectedSentence(i)}
                style={{
                  padding: '10px 14px', borderRadius: 'var(--radius-md)', border: 'none',
                  textAlign: 'left', cursor: 'pointer', fontSize: 13, lineHeight: 1.5,
                  fontFamily: 'var(--font-family)', transition: 'all 0.15s',
                  background: selectedSentence === i ? 'rgba(99, 102, 241, 0.15)' : 'var(--bg-secondary)',
                  color: selectedSentence === i ? 'var(--accent-light)' : 'var(--text-secondary)',
                  outline: selectedSentence === i ? '2px solid var(--accent)' : '1px solid transparent',
                }}>
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Step 2: Record */}
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-3)',
          padding: 'var(--space-5)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          marginBottom: 'var(--space-4)',
        }}>
          {/* Timer */}
          <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'monospace', color: isRecording ? 'var(--error)' : 'var(--text-primary)' }}>
            {formatTime(duration)}
          </div>

          {/* Record button */}
          <button onClick={isRecording ? stopRecording : startRecording}
            style={{
              width: 72, height: 72, borderRadius: '50%', border: 'none', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s',
              background: isRecording
                ? 'linear-gradient(135deg, #ef4444, #dc2626)'
                : 'linear-gradient(135deg, var(--accent), var(--accent-dark))',
              boxShadow: isRecording ? '0 0 0 6px rgba(239,68,68,0.25)' : '0 0 0 4px rgba(99,102,241,0.2)',
            }}>
            {isRecording
              ? <div style={{ width: 24, height: 24, borderRadius: 4, background: 'white' }} />
              : <svg width="28" height="28" viewBox="0 0 24 24" fill="white"><path d="M12 1C10.34 1 9 2.34 9 4v8c0 1.66 1.34 3 3 3s3-1.34 3-3V4c0-1.66-1.34-3-3-3zm5 8c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V19h-2v2h6v-2h-2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>}
          </button>

          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {isRecording ? '🔴 Đang ghi... bấm để dừng' : recordedBlob ? '✅ Đã ghi xong — nghe lại bên dưới' : 'Bấm để bắt đầu ghi âm (3-10 giây)'}
          </div>
        </div>

        {/* Playback */}
        {recordedUrl && (
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <audio src={recordedUrl} controls style={{ width: '100%', height: 36 }} />
          </div>
        )}

        {/* Name input */}
        {recordedBlob && (
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Tên giọng nói</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)}
              placeholder="VD: Giọng của tôi, Giọng nam Bắc..." />
          </div>
        )}

        {error && <div className="form-error">{error}</div>}

        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Hủy</button>
          {recordedBlob && (
            <>
              <button className="btn btn-ghost" onClick={() => { setRecordedBlob(null); setRecordedUrl(null); setDuration(0); }}>
                🔄 Ghi lại
              </button>
              <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>
                {uploading ? <span className="spinner" /> : '💾 Lưu Reference'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Upload Modal ─────────────────────────────── */
function UploadModal({ onClose, onDone }) {
  const [file, setFile] = useState(null);
  const [name, setName] = useState('');
  const [refText, setRefText] = useState('');
  const [language, setLanguage] = useState('vi');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const toast = useToast();
  const dropRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) { setError('Chọn file audio'); return; }
    setLoading(true); setError('');
    const fd = new FormData();
    fd.append('audio', file);
    fd.append('name', name);
    fd.append('language', language);
    if (refText) fd.append('ref_text', refText);
    try {
      await api.uploadRef(fd);
      toast.success('Upload thành công!');
      onDone();
    } catch (err) { setError(err.message); }
    setLoading(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer?.files?.[0];
    if (f) { setFile(f); if (!name) setName(f.name.replace(/\.[^.]+$/, '')); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">Upload Reference Audio</h2>
        <form onSubmit={handleSubmit}>
          <div ref={dropRef} onDrop={handleDrop} onDragOver={e => e.preventDefault()}
            style={{ border: '2px dashed var(--border)', borderRadius: 'var(--radius-lg)', padding: 'var(--space-8)', textAlign: 'center', cursor: 'pointer', marginBottom: 'var(--space-4)', background: 'var(--bg-secondary)' }}
            onClick={() => document.getElementById('ref-file-input').click()}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>☁️</div>
            <div style={{ fontSize: 14 }}>{file ? file.name : 'Drag & drop hoặc click để chọn file'}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>WAV, MP3, OGG — 1-30 giây</div>
            <input id="ref-file-input" type="file" accept="audio/*" style={{ display: 'none' }}
              onChange={e => { const f = e.target.files[0]; if (f) { setFile(f); if (!name) setName(f.name.replace(/\.[^.]+$/, '')); }}} />
          </div>

          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Tên</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} required placeholder="Tên giọng nói" />
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Transcript (nội dung nói)</label>
            <textarea className="textarea" value={refText} onChange={e => setRefText(e.target.value)}
              placeholder="Nội dung nói trong audio" rows={3} />
          </div>
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Ngôn ngữ</label>
            <select className="select" value={language} onChange={e => setLanguage(e.target.value)}>
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Hủy</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
