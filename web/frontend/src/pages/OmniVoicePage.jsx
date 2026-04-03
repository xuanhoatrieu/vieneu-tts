import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

const NON_VERBAL_TAGS = [
  { tag: '[laughter]', emoji: '😂', label: 'Cười' },
  { tag: '[sigh]', emoji: '😮‍💨', label: 'Thở dài' },
  { tag: '[sniff]', emoji: '🤧', label: 'Hít mũi' },
  { tag: '[surprise-ah]', emoji: '😲', label: 'Ồ!' },
  { tag: '[surprise-oh]', emoji: '😯', label: 'Oh!' },
  { tag: '[surprise-wa]', emoji: '🤩', label: 'Wa!' },
  { tag: '[question-ah]', emoji: '🤔', label: 'À?' },
  { tag: '[question-oh]', emoji: '❓', label: 'Ô?' },
  { tag: '[confirmation-en]', emoji: '✅', label: 'Ừm' },
  { tag: '[dissatisfaction-hnn]', emoji: '😤', label: 'Hừ' },
];

const VOICE_ATTRIBUTES = {
  gender: ['male', 'female'],
  age: ['child', 'young', 'middle-aged', 'elderly'],
  pitch: ['very low', 'low', 'normal', 'high', 'very high'],
  style: ['normal', 'whisper'],
  accent_en: ['', 'american accent', 'british accent', 'australian accent', 'indian accent'],
};

export default function OmniVoicePage() {
  const [tab, setTab] = useState('auto'); // auto, design, clone
  const [text, setText] = useState('');
  const [audioUrl, setAudioUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  // Design mode
  const [gender, setGender] = useState('female');
  const [age, setAge] = useState('young');
  const [pitch, setPitch] = useState('normal');
  const [style, setStyle] = useState('normal');
  const [accentEn, setAccentEn] = useState('');
  const [customInstruct, setCustomInstruct] = useState('');

  // Clone mode
  const [cloneFile, setCloneFile] = useState(null);
  const [refText, setRefText] = useState('');
  const [cloneSource, setCloneSource] = useState('library'); // 'library' | 'upload'
  const [voiceLibrary, setVoiceLibrary] = useState([]);
  const [selectedRefId, setSelectedRefId] = useState(null);
  const [libraryPreviewUrl, setLibraryPreviewUrl] = useState(null);

  // Shared params
  const [speed, setSpeed] = useState(1.0);
  const [numStep, setNumStep] = useState(32);
  const [normalize, setNormalize] = useState(true);

  const audioRef = useRef(null);
  const previewRef = useRef(null);
  const textRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    api.omniVoiceStatus().then(setStatus).catch(() => {});
    api.getRefs().then(refs => {
      setVoiceLibrary(refs);
      if (refs?.length > 0) setSelectedRefId(refs[0].id);
    }).catch(() => {});
  }, []);

  // Update preview when selection changes
  useEffect(() => {
    if (selectedRefId) {
      setLibraryPreviewUrl(api.getRefAudioUrl(selectedRefId));
      const ref = voiceLibrary.find(r => r.id === selectedRefId);
      if (ref?.ref_text) setRefText(ref.ref_text);
    } else {
      setLibraryPreviewUrl(null);
    }
  }, [selectedRefId]);

  const buildInstruct = () => {
    const parts = [gender];
    if (age !== 'young') parts.push(age);
    if (pitch !== 'normal') parts.push(pitch + ' pitch');
    if (style === 'whisper') parts.push('whisper');
    if (accentEn) parts.push(accentEn);
    if (customInstruct.trim()) parts.push(customInstruct.trim());
    return parts.join(', ');
  };

  const insertTag = (tag) => {
    const el = textRef.current;
    if (!el) { setText(prev => prev + ' ' + tag); return; }
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const newText = text.slice(0, start) + tag + text.slice(end);
    setText(newText);
    setTimeout(() => {
      el.focus();
      el.setSelectionRange(start + tag.length, start + tag.length);
    }, 0);
  };

  const pollJob = async (jobId) => {
    return new Promise((resolve, reject) => {
      const poll = setInterval(async () => {
        try {
          const s = await api.pollOmniJob(jobId);
          if (s.status === 'processing') {
            toast.loading(`⏳ ${s.error || 'Đang xử lý...'}`, { id: 'omni-synth' });
          } else if (s.status === 'completed') {
            clearInterval(poll);
            toast.dismiss('omni-synth');
            resolve(s);
          } else if (s.status === 'failed') {
            clearInterval(poll);
            toast.dismiss('omni-synth');
            reject(new Error(s.error || 'Generation failed'));
          }
        } catch (e) {
          clearInterval(poll);
          toast.dismiss('omni-synth');
          reject(e);
        }
      }, 3000);
    });
  };

  const generate = async () => {
    if (!text.trim()) { toast.error('Nhập văn bản trước!'); return; }
    setLoading(true);
    setAudioUrl(null);

    try {
      let job;

      if (tab === 'auto') {
        job = await api.omniVoiceAuto({ text, speed, num_step: numStep, normalize });
      } else if (tab === 'design') {
        const instruct = buildInstruct();
        if (!instruct) { toast.error('Chọn thuộc tính giọng!'); setLoading(false); return; }
        job = await api.omniVoiceDesign({ text, instruct, speed, num_step: numStep, normalize });
      } else if (tab === 'clone') {
        if (cloneSource === 'library') {
          if (!selectedRefId) { toast.error('Chọn giọng từ Voice Library!'); setLoading(false); return; }
          const fd = new FormData();
          fd.append('text', text);
          fd.append('ref_id', selectedRefId);
          fd.append('speed', speed);
          fd.append('num_step', numStep);
          fd.append('normalize', normalize);
          job = await api.omniVoiceCloneRef(fd);
        } else {
          if (!cloneFile) { toast.error('Chọn file audio tham chiếu!'); setLoading(false); return; }
          const fd = new FormData();
          fd.append('text', text);
          fd.append('audio', cloneFile);
          fd.append('ref_text', refText);
          fd.append('speed', speed);
          fd.append('num_step', numStep);
          fd.append('normalize', normalize);
          job = await api.omniVoiceClone(fd);
        }
      }

      toast.loading('⏳ Đang tổng hợp giọng nói...', { id: 'omni-synth' });
      const result = await pollJob(job.job_id);

      if (result?.audio_file) {
        setAudioUrl(api.getOmniAudioUrl(result.audio_file));
        const t = result.processing_time_sec ? ` (${result.processing_time_sec}s)` : '';
        toast.success(`Tổng hợp thành công!${t}`);
      }
    } catch (err) {
      toast.dismiss('omni-synth');
      toast.error(err.message);
    }
    setLoading(false);
  };

  const tabs = [
    { id: 'auto', icon: '🤖', label: 'Auto Voice' },
    { id: 'design', icon: '🎨', label: 'Voice Design' },
    { id: 'clone', icon: '🎭', label: 'Voice Cloning' },
  ];

  return (
    <>
      <div className="topbar">
        <h1>🌍 OmniVoice</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
          <span style={{
            background: status?.initialized ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
            color: status?.initialized ? '#34d399' : '#fbbf24',
            padding: '3px 10px', borderRadius: 12, fontWeight: 600,
          }}>
            {status?.initialized ? '✅ Ready' : status?.is_loading ? '🔄 Loading...' : '⏸️ Idle'}
          </span>
          <span style={{ color: 'var(--text-muted)' }}>600+ Languages</span>
        </div>
      </div>

      <div className="page-content" style={{ display: 'flex', gap: 'var(--space-6)' }}>
        {/* Main Area */}
        <div style={{ flex: 1 }}>
          {/* Tab Selector */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 'var(--space-5)', background: 'var(--bg-secondary)', padding: 4, borderRadius: 12 }}>
            {tabs.map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{
                  flex: 1, padding: '10px 16px', border: 'none', borderRadius: 10,
                  background: tab === t.id ? 'var(--accent)' : 'transparent',
                  color: tab === t.id ? 'white' : 'var(--text-secondary)',
                  fontWeight: 600, fontSize: 13, cursor: 'pointer',
                  fontFamily: 'var(--font-family)', transition: 'all 0.2s',
                }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {/* Text Input */}
          <div className="form-group" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label">Nhập văn bản</label>
            <textarea ref={textRef} className="textarea" rows={5}
              placeholder={tab === 'clone' ? 'Nhập văn bản cần tổng hợp bằng giọng clone...'
                : tab === 'design' ? 'Nhập văn bản — chọn thuộc tính giọng bên phải...'
                : 'Nhập văn bản bất kỳ (600+ ngôn ngữ)...'}
              value={text} onChange={e => setText(e.target.value)} />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'right' }}>
              {text.length} ký tự
            </div>
          </div>

          {/* Non-verbal Tags */}
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <label className="form-label" style={{ fontSize: 12 }}>🎭 Non-verbal Tags</label>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {NON_VERBAL_TAGS.map(t => (
                <button key={t.tag} onClick={() => insertTag(t.tag)}
                  title={t.tag}
                  style={{
                    padding: '4px 10px', borderRadius: 8, border: '1px solid var(--border)',
                    background: 'var(--bg-secondary)', color: 'var(--text-secondary)',
                    fontSize: 11, cursor: 'pointer', fontFamily: 'var(--font-family)',
                    transition: 'all 0.15s',
                  }}>
                  {t.emoji} {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Clone-specific: Reference Audio */}
          {tab === 'clone' && (
            <div className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                <h3 style={{ fontSize: 14, fontWeight: 600 }}>🎤 Reference Audio</h3>
                <div style={{ display: 'flex', gap: 4, background: 'var(--bg-secondary)', padding: 2, borderRadius: 8 }}>
                  {[{ id: 'library', label: '📚 Library' }, { id: 'upload', label: '📁 Upload' }].map(s => (
                    <button key={s.id} onClick={() => setCloneSource(s.id)}
                      style={{
                        padding: '4px 10px', borderRadius: 6, border: 'none',
                        background: cloneSource === s.id ? 'var(--accent)' : 'transparent',
                        color: cloneSource === s.id ? 'white' : 'var(--text-muted)',
                        fontWeight: 600, fontSize: 11, cursor: 'pointer',
                        fontFamily: 'var(--font-family)',
                      }}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {cloneSource === 'library' ? (
                <>
                  {voiceLibrary.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: 'var(--space-4)', color: 'var(--text-muted)', fontSize: 12 }}>
                      Chưa có giọng nào. <a href="/voices" style={{ color: 'var(--accent)' }}>Thêm tại Voice Library →</a>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 200, overflowY: 'auto' }}>
                      {voiceLibrary.map(ref => {
                        const isSelected = selectedRefId === ref.id;
                        return (
                          <button key={ref.id} onClick={() => setSelectedRefId(isSelected ? null : ref.id)}
                            style={{
                              display: 'flex', alignItems: 'center', gap: 10,
                              padding: '8px 12px', borderRadius: 10, border: 'none',
                              background: isSelected ? 'rgba(99,102,241,0.12)' : 'var(--bg-secondary)',
                              outline: isSelected ? '2px solid var(--accent)' : '1px solid var(--border)',
                              cursor: 'pointer', textAlign: 'left',
                              fontFamily: 'var(--font-family)', transition: 'all 0.15s',
                            }}>
                            <span style={{ fontSize: 20 }}>🎙️</span>
                            <div style={{ flex: 1 }}>
                              <div style={{ fontSize: 12, fontWeight: 600, color: isSelected ? 'var(--accent)' : 'var(--text-primary)' }}>
                                {ref.name}
                              </div>
                              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                                {ref.language?.toUpperCase()} • {ref.duration_sec ? `${ref.duration_sec.toFixed(1)}s` : '—'}
                                {ref.ref_text && ` • "${ref.ref_text.slice(0, 30)}..."`}
                              </div>
                            </div>
                            {isSelected && <span style={{ fontSize: 14, color: 'var(--accent)' }}>✓</span>}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <input type="file" accept="audio/*"
                    onChange={e => setCloneFile(e.target.files?.[0] || null)}
                    style={{ fontSize: 13, marginBottom: 'var(--space-3)', width: '100%' }} />
                  {cloneFile && (
                    <div style={{ fontSize: 12, color: '#34d399', marginBottom: 'var(--space-2)' }}>
                      ✅ {cloneFile.name} ({(cloneFile.size / 1024).toFixed(0)} KB)
                    </div>
                  )}
                  <div className="form-group">
                    <label className="form-label" style={{ fontSize: 12 }}>Reference Text (tùy chọn — để trống để auto-transcribe)</label>
                    <input type="text" className="input" placeholder="Nội dung nói trong file audio tham chiếu..."
                      value={refText} onChange={e => setRefText(e.target.value)} />
                  </div>
                </>
              )}
            </div>
          )}

          {/* Generate Button */}
          <button className="btn btn-primary btn-lg" onClick={generate}
            disabled={loading}
            style={{ width: '100%', padding: '14px', fontSize: 15 }}>
            {loading ? <span className="spinner" /> : '🌍 Tổng hợp giọng nói'}
          </button>

          {/* Audio Output */}
          {audioUrl && (
            <div className="audio-player" style={{ marginTop: 'var(--space-5)' }}>
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

        {/* Right Panel */}
        <div style={{ width: 260, flexShrink: 0 }}>
          {/* Generation Settings */}
          <div className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-3)' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--space-4)' }}>⚙️ Cài đặt</h3>

            <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
              <label className="form-label">Tốc độ: {speed.toFixed(1)}x</label>
              <input type="range" min="0.5" max="2.0" step="0.1" value={speed}
                onChange={e => setSpeed(parseFloat(e.target.value))}
                style={{ width: '100%' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
                <span>0.5x</span><span>2.0x</span>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
              <label className="form-label">Diffusion Steps</label>
              <div style={{ display: 'flex', gap: 6 }}>
                {[16, 32].map(n => (
                  <button key={n} onClick={() => setNumStep(n)}
                    style={{
                      flex: 1, padding: '6px 0', borderRadius: 8, border: 'none',
                      background: numStep === n ? 'var(--accent)' : 'var(--bg-secondary)',
                      color: numStep === n ? 'white' : 'var(--text-secondary)',
                      fontWeight: 600, fontSize: 12, cursor: 'pointer',
                      fontFamily: 'var(--font-family)',
                    }}>
                    {n} {n === 16 ? '⚡ Fast' : '✨ Quality'}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <input type="checkbox" id="normalize" checked={normalize}
                onChange={e => setNormalize(e.target.checked)} />
              <label htmlFor="normalize" style={{ color: 'var(--text-secondary)', cursor: 'pointer' }}>
                🦭 SEA-G2P Normalize
              </label>
            </div>
          </div>

          {/* Voice Design Panel (only for design tab) */}
          {tab === 'design' && (
            <div className="card" style={{ padding: 'var(--space-4)', marginBottom: 'var(--space-3)' }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--space-3)' }}>🎨 Voice Design</h3>

              {/* Gender */}
              <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                <label className="form-label" style={{ fontSize: 12 }}>Giới tính</label>
                <div style={{ display: 'flex', gap: 6 }}>
                  {VOICE_ATTRIBUTES.gender.map(g => (
                    <button key={g} onClick={() => setGender(g)}
                      style={{
                        flex: 1, padding: '6px 0', borderRadius: 8, border: 'none',
                        background: gender === g ? 'rgba(236,72,153,0.15)' : 'var(--bg-secondary)',
                        color: gender === g ? '#ec4899' : 'var(--text-muted)',
                        fontWeight: 600, fontSize: 11, cursor: 'pointer',
                        fontFamily: 'var(--font-family)',
                        outline: gender === g ? '1px solid rgba(236,72,153,0.4)' : 'none',
                      }}>
                      {g === 'male' ? '♂️ Nam' : '♀️ Nữ'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Age */}
              <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                <label className="form-label" style={{ fontSize: 12 }}>Tuổi</label>
                <select className="select" value={age} onChange={e => setAge(e.target.value)} style={{ width: '100%' }}>
                  <option value="child">👶 Trẻ em</option>
                  <option value="young">🧑 Trẻ</option>
                  <option value="middle-aged">👨 Trung niên</option>
                  <option value="elderly">👴 Cao tuổi</option>
                </select>
              </div>

              {/* Pitch */}
              <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                <label className="form-label" style={{ fontSize: 12 }}>Cao độ</label>
                <select className="select" value={pitch} onChange={e => setPitch(e.target.value)} style={{ width: '100%' }}>
                  <option value="very low">🔉 Rất thấp</option>
                  <option value="low">🔉 Thấp</option>
                  <option value="normal">🔊 Bình thường</option>
                  <option value="high">🔊 Cao</option>
                  <option value="very high">🔊 Rất cao</option>
                </select>
              </div>

              {/* Style */}
              <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                <label className="form-label" style={{ fontSize: 12 }}>Phong cách</label>
                <div style={{ display: 'flex', gap: 6 }}>
                  {['normal', 'whisper'].map(s => (
                    <button key={s} onClick={() => setStyle(s)}
                      style={{
                        flex: 1, padding: '6px 0', borderRadius: 8, border: 'none',
                        background: style === s ? 'rgba(168,85,247,0.15)' : 'var(--bg-secondary)',
                        color: style === s ? '#a855f7' : 'var(--text-muted)',
                        fontWeight: 600, fontSize: 11, cursor: 'pointer',
                        fontFamily: 'var(--font-family)',
                        outline: style === s ? '1px solid rgba(168,85,247,0.4)' : 'none',
                      }}>
                      {s === 'normal' ? '🗣️ Normal' : '🤫 Whisper'}
                    </button>
                  ))}
                </div>
              </div>

              {/* English Accent */}
              <div className="form-group" style={{ marginBottom: 'var(--space-3)' }}>
                <label className="form-label" style={{ fontSize: 12 }}>Accent (English)</label>
                <select className="select" value={accentEn} onChange={e => setAccentEn(e.target.value)} style={{ width: '100%' }}>
                  <option value="">— Không —</option>
                  <option value="american accent">🇺🇸 American</option>
                  <option value="british accent">🇬🇧 British</option>
                  <option value="australian accent">🇦🇺 Australian</option>
                  <option value="indian accent">🇮🇳 Indian</option>
                </select>
              </div>

              {/* Custom */}
              <div className="form-group">
                <label className="form-label" style={{ fontSize: 12 }}>Tuỳ chỉnh thêm</label>
                <input type="text" className="input" placeholder="e.g. cheerful, calm..."
                  value={customInstruct} onChange={e => setCustomInstruct(e.target.value)} />
              </div>

              {/* Preview instruction */}
              <div style={{
                marginTop: 'var(--space-3)', padding: '8px 12px', borderRadius: 8,
                background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.2)',
                fontSize: 11, color: '#c084fc', wordBreak: 'break-word',
              }}>
                <strong>Instruct:</strong> {buildInstruct()}
              </div>
            </div>
          )}

          {/* Info Card */}
          <div className="card" style={{ padding: 'var(--space-4)' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 'var(--space-3)' }}>🌍 OmniVoice</h3>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.6 }}>
              <div style={{ marginBottom: 8 }}>
                <span style={{
                  background: 'rgba(6,182,212,0.15)', color: '#06b6d4',
                  padding: '2px 8px', borderRadius: 8, fontWeight: 600, fontSize: 10,
                }}>k2-fsa/OmniVoice</span>
              </div>
              <p style={{ margin: '4px 0' }}>🗣️ 600+ ngôn ngữ</p>
              <p style={{ margin: '4px 0' }}>⚡ RTF ~0.025 (40x realtime)</p>
              <p style={{ margin: '4px 0' }}>🎭 Non-verbal expressions</p>
              <p style={{ margin: '4px 0' }}>🦭 SEA-G2P text normalize</p>
              {status?.has_normalizer && (
                <p style={{ margin: '4px 0', color: '#34d399' }}>✅ Normalizer active</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
