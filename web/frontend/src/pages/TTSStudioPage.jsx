import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function TTSStudioPage() {
  const [text, setText] = useState('');
  const [voices, setVoices] = useState([]);
  const [refs, setRefs] = useState([]);
  const [trainedVoices, setTrainedVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [voiceType, setVoiceType] = useState('preset');
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [temp, setTemp] = useState(0.7);
  const [modelStatus, setModelStatus] = useState(null);
  const [modelSwitching, setModelSwitching] = useState(false);
  const audioRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    api.getVoices().then(v => { setVoices(v); if (v.length) setSelectedVoice(v[0].id); });
    api.getRefs().then(setRefs).catch(() => {});
    api.getTrainedVoicesForTTS().then(setTrainedVoices).catch(() => {});
    api.getTTSModels().then(setModelStatus).catch(() => {});
  }, []);

  // Poll model status while loading
  useEffect(() => {
    if (!modelStatus?.is_loading) return;
    const interval = setInterval(async () => {
      try {
        const s = await api.getTTSModelStatus();
        setModelStatus(s);
        if (!s.is_loading) {
          clearInterval(interval);
          setModelSwitching(false);
          if (s.error) toast.error('Lỗi nạp model: ' + s.error);
          else toast.success('✅ Model đã sẵn sàng!');
        }
      } catch (err) { console.error(err); }
    }, 2000);
    return () => clearInterval(interval);
  }, [modelStatus?.is_loading]);

  const handleModelSwitch = async (repo) => {
    if (repo === modelStatus?.current_model) return;
    setModelSwitching(true);
    try {
      await api.switchTTSModel(repo);
      setModelStatus(prev => ({ ...prev, is_loading: true }));
    } catch (err) {
      toast.error(err.message);
      setModelSwitching(false);
    }
  };

  const synthesize = async () => {
    if (!text.trim()) { toast.error('Nhập văn bản trước!'); return; }
    setLoading(true); setAudioUrl(null);
    try {
      let data;
      if (voiceType === 'preset') {
        data = await api.synthesize({ text, voice_id: selectedVoice, temperature: temp });
      } else if (voiceType === 'ref') {
        data = await api.synthesizeWithRef({ text, ref_id: selectedVoice, temperature: temp });
      } else if (voiceType === 'trained') {
        const voiceId = parseInt(selectedVoice);
        if (isNaN(voiceId)) {
          toast.error('Vui lòng chọn giọng trained!');
          setLoading(false);
          return;
        }
        // Job-based polling to avoid Cloudflare 524 timeout
        const job = await api.synthesizeTrained({ text, trained_voice_id: voiceId });
        toast.loading('⏳ Đang xử lý...', { id: 'trained-synth' });
        // Poll every 3 seconds
        data = await new Promise((resolve, reject) => {
          const poll = setInterval(async () => {
            try {
              const status = await api.pollTrainedJob(job.job_id);
              if (status.status === 'processing') {
                toast.loading(`⏳ ${status.error || 'Đang xử lý...'}`, { id: 'trained-synth' });
              } else if (status.status === 'completed') {
                clearInterval(poll);
                toast.dismiss('trained-synth');
                resolve(status);
              } else if (status.status === 'failed') {
                clearInterval(poll);
                toast.dismiss('trained-synth');
                reject(new Error(status.error || 'Synthesis failed'));
              }
            } catch (e) {
              clearInterval(poll);
              toast.dismiss('trained-synth');
              reject(e);
            }
          }, 3000);
        });
      }
      if (data?.audio_file) {
        setAudioUrl(api.getAudioUrl(data.audio_file));
        toast.success('Tổng hợp thành công!');
      }
    } catch (err) {
      toast.dismiss('trained-synth');
      toast.error(err.message);
    }
    setLoading(false);
  };

  const currentList = voiceType === 'preset' ? voices
    : voiceType === 'ref' ? refs.map(r => ({ id: r.id, name: r.name }))
    : trainedVoices.map(v => ({ ...v, id: v.id, name: v.name }));

  const currentModel = modelStatus?.available_models?.find(m => m.repo === modelStatus?.current_model);

  return (
    <>
      <div className="topbar">
        <h1>VieNeu TTS Studio</h1>
        {/* Current model indicator in topbar */}
        {currentModel && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
            <span style={{ color: 'var(--text-muted)' }}>Model:</span>
            <span style={{
              background: 'rgba(99,102,241,0.15)', color: '#818cf8',
              padding: '3px 10px', borderRadius: 12, fontWeight: 600,
            }}>{currentModel.name}</span>
          </div>
        )}
      </div>
      <div className="page-content" style={{ display: 'flex', gap: 'var(--space-6)' }}>
        {/* Main Area */}
        <div style={{ flex: 1 }}>
          <div className="form-group" style={{ marginBottom: 'var(--space-5)' }}>
            <label className="form-label">Nhập văn bản</label>
            <textarea className="textarea" rows={6}
              placeholder="Nhập văn bản tiếng Việt tại đây..."
              value={text} onChange={e => setText(e.target.value)} />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'right' }}>
              {text.length} ký tự
            </div>
          </div>

          {/* Voice selector */}
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
            <select className="select" value={voiceType}
              onChange={e => { setVoiceType(e.target.value); setSelectedVoice(''); }}
              style={{ width: 140 }}>
              <option value="preset">Preset</option>
              <option value="ref">Reference</option>
              <option value="trained">Trained</option>
            </select>
            <select className="select" value={selectedVoice}
              onChange={e => setSelectedVoice(e.target.value)} style={{ flex: 1 }}>
              <option value="">-- Chọn giọng --</option>
              {currentList.map(v => (
                <option key={v.id} value={v.id}>
                  {v.name || v.id}
                  {v.type === 'trained' && !v.checkpoint_exists ? ' ❌ (mất checkpoint)' : ''}
                </option>
              ))}
            </select>
            <button className="btn btn-primary btn-lg" onClick={synthesize}
              disabled={loading || !selectedVoice || modelStatus?.is_loading}>
              {loading ? <span className="spinner" /> : '🔊 Tổng hợp'}
            </button>
          </div>

          {/* Trained voice info badge */}
          {voiceType === 'trained' && selectedVoice && (() => {
            const tv = trainedVoices.find(v => String(v.id) === String(selectedVoice));
            if (!tv) return null;
            return (
              <div style={{
                display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 'var(--space-5)',
                fontSize: 12, alignItems: 'center',
              }}>
                <span style={{
                  padding: '3px 10px', borderRadius: 12,
                  background: 'rgba(99,102,241,0.15)', color: '#818cf8', fontWeight: 600,
                }}>
                  🧠 {tv.base_model_name || 'Unknown model'}
                </span>
                <span style={{
                  padding: '3px 10px', borderRadius: 12,
                  background: tv.has_ref_audio ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                  color: tv.has_ref_audio ? '#34d399' : '#fbbf24',
                }}>
                  {tv.has_ref_audio ? '📎 Ref audio' : '⚠️ No ref audio'}
                </span>
                {tv.needs_gpu_model && (
                  <span style={{
                    padding: '3px 10px', borderRadius: 12,
                    background: 'rgba(245,158,11,0.15)', color: '#fbbf24',
                  }}>
                    ⚡ Sẽ tự chuyển sang GPU model
                  </span>
                )}
                {!tv.checkpoint_exists && (
                  <span style={{
                    padding: '3px 10px', borderRadius: 12,
                    background: 'rgba(239,68,68,0.15)', color: '#f87171',
                  }}>
                    ❌ Checkpoint không tồn tại
                  </span>
                )}
              </div>
            );
          })()}

          {/* Audio Output */}
          {audioUrl && (
            <div className="audio-player">
              <button className="play-btn" onClick={() => {
                if (audioRef.current) {
                  audioRef.current.paused ? audioRef.current.play() : audioRef.current.pause();
                }
              }}>▶</button>
              <div style={{ flex: 1 }}>
                <audio ref={audioRef} src={audioUrl} controls style={{ width: '100%', height: 36 }} />
              </div>
              <a href={audioUrl} download className="btn btn-ghost" title="Download">⬇️</a>
            </div>
          )}
        </div>

        {/* Settings Panel */}
        <div style={{ width: 240, flexShrink: 0 }}>
          {/* Temperature */}
          <div className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-3)' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--space-4)' }}>⚙️ Cài đặt</h3>
            <div className="form-group">
              <label className="form-label">Temperature {temp}</label>
              <input type="range" min="0.1" max="1.0" step="0.1" value={temp}
                onChange={e => setTemp(parseFloat(e.target.value))}
                style={{ width: '100%' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
                <span>0.1</span><span>1.0</span>
              </div>
            </div>
          </div>

          {/* Model Selector */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--space-3)' }}>🧠 Model</h3>

            {/* GPU Status */}
            {modelStatus?.gpus?.length > 0 && (
              <div style={{ marginBottom: 'var(--space-3)' }}>
                {modelStatus.gpus.map(g => (
                  <div key={g.id} style={{
                    fontSize: 11, padding: '4px 8px', marginBottom: 4,
                    background: g.free_mb > 2000 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                    borderRadius: 6, color: g.free_mb > 2000 ? '#34d399' : '#f87171',
                  }}>
                    GPU {g.id}: {g.free_mb}MB free / {g.total_mb}MB
                    {g.free_mb > 2000 ? ' ✅' : ' ⛔'}
                  </div>
                ))}
              </div>
            )}

            {/* Model list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {modelStatus?.available_models?.map(m => {
                const isCurrent = m.repo === modelStatus.current_model;
                const isGpu = m.device === 'gpu';
                const gpuBusy = isGpu && modelStatus.gpus?.length > 0 &&
                  !modelStatus.gpus.some(g => g.free_mb >= (m.vram_required_mb || 2000));

                return (
                  <button key={m.repo}
                    onClick={() => !isCurrent && !modelSwitching && !gpuBusy && handleModelSwitch(m.repo)}
                    disabled={modelSwitching || (gpuBusy && !isCurrent)}
                    style={{
                      display: 'flex', flexDirection: 'column', gap: 2,
                      padding: '8px 10px', borderRadius: 8, border: 'none', cursor: isCurrent || gpuBusy ? 'default' : 'pointer',
                      background: isCurrent ? 'rgba(99,102,241,0.15)' : 'var(--bg-primary)',
                      opacity: gpuBusy && !isCurrent ? 0.5 : 1,
                      textAlign: 'left', fontFamily: 'var(--font-family)',
                      outline: isCurrent ? '2px solid var(--accent)' : '1px solid var(--border)',
                      transition: 'all 0.15s',
                    }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: isCurrent ? 'var(--accent)' : 'var(--text-primary)' }}>
                        {m.name}
                      </span>
                      {isCurrent && <span style={{ fontSize: 9, fontWeight: 700, background: 'var(--accent)', color: 'white', padding: '1px 6px', borderRadius: 8 }}>ACTIVE</span>}
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <span style={{ fontSize: 10, color: isGpu ? '#f87171' : '#fbbf24' }}>{m.device.toUpperCase()}</span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>•</span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{m.size_mb}MB</span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>•</span>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{m.format}</span>
                    </div>
                    {gpuBusy && !isCurrent && (
                      <span style={{ fontSize: 10, color: '#f87171' }}>⛔ GPU không khả dụng</span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Model Loading Overlay */}
      {modelStatus?.is_loading && (
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
              Vui lòng chờ, hệ thống đang tải model vào bộ nhớ.
              <br />Quá trình này có thể mất 10-60 giây.
            </p>
            <span className="spinner" style={{ width: 32, height: 32 }} />
          </div>
        </div>
      )}
    </>
  );
}
