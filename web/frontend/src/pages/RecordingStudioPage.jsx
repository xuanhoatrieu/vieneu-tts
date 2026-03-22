import { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { useToast } from '../contexts/ToastContext';

export default function RecordingStudioPage() {
  const [sets, setSets] = useState([]);
  const [selectedSet, setSelectedSet] = useState(null);
  const [sentences, setSentences] = useState([]);
  const [recordings, setRecordings] = useState({ recordings: [], recorded_count: 0, total_sentences: 0 });
  const [activeSentence, setActiveSentence] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordTime, setRecordTime] = useState(0);
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const timer = useRef(null);
  const audioRef = useRef(null);
  const toast = useToast();

  useEffect(() => { api.getSets().then(setSets).catch(() => {}); }, []);

  const loadSet = async (setId) => {
    setSelectedSet(setId);
    try {
      const detail = await api.getSet(setId);
      setSentences(detail.sentences || []);
      const recs = await api.getRecordings(setId);
      setRecordings(recs);
    } catch (err) { toast.error(err.message); }
  };

  const isRecorded = (sentId) => {
    return recordings.recordings?.some(r => r.sentence_id === sentId);
  };

  const getRecording = (sentId) => {
    return recordings.recordings?.find(r => r.sentence_id === sentId);
  };

  const startRecording = async (sentId) => {
    setActiveSentence(sentId);
    chunks.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 24000, channelCount: 1, echoCancellation: true, noiseSuppression: true } });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks.current, { type: 'audio/webm' });
        await uploadRecording(selectedSet, sentId, blob);
      };
      mr.start();
      mediaRecorder.current = mr;
      setIsRecording(true);
      setRecordTime(0);
      timer.current = setInterval(() => setRecordTime(t => t + 0.1), 100);
    } catch (err) { toast.error('Không thể truy cập microphone'); }
  };

  const stopRecording = () => {
    if (mediaRecorder.current?.state === 'recording') {
      mediaRecorder.current.stop();
    }
    clearInterval(timer.current);
    setIsRecording(false);
  };

  const uploadRecording = async (setId, sentId, blob) => {
    const fd = new FormData();
    fd.append('audio', blob, 'recording.webm');
    try {
      await api.uploadRecording(setId, sentId, fd);
      toast.success('Đã lưu bản ghi!');
      await loadSet(setId);
    } catch (err) { toast.error(err.message); }
    setActiveSentence(null);
  };

  const playRecording = (recId) => {
    if (audioRef.current) {
      audioRef.current.src = api.getRecordingAudioUrl(recId);
      audioRef.current.play();
    }
  };

  const progress = recordings.total_sentences > 0
    ? Math.round((recordings.recorded_count / recordings.total_sentences) * 100) : 0;

  return (
    <>
      <div className="topbar">
        <h1>Recording Studio</h1>
        <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
          {recordings.recorded_count}/{recordings.total_sentences} đã thu âm
        </div>
      </div>
      <div className="page-content">
        <audio ref={audioRef} style={{ display: 'none' }} />

        {/* Set selector */}
        <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-5)', alignItems: 'center' }}>
          <label className="form-label" style={{ marginBottom: 0 }}>Sentence Set</label>
          <select className="select" value={selectedSet || ''} onChange={e => loadSet(parseInt(e.target.value))} style={{ maxWidth: 400 }}>
            <option value="">-- Chọn bộ câu --</option>
            {sets.map(s => <option key={s.id} value={s.id}>{s.name} — {s.sentence_count || '?'} câu</option>)}
          </select>
        </div>

        {/* Progress bar */}
        {selectedSet && (
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
              Đã thu: {recordings.recorded_count}/{recordings.total_sentences} câu ({progress}%)
            </div>
          </div>
        )}

        {/* Sentence list */}
        {sentences.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {sentences.map((sent, i) => {
              const rec = getRecording(sent.id);
              const isActive = activeSentence === sent.id;
              return (
                <div key={sent.id}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
                    padding: 'var(--space-3) var(--space-4)',
                    background: isActive ? 'var(--bg-card)' : 'transparent',
                    borderRadius: 'var(--radius-md)',
                    border: isActive ? '1px solid var(--border)' : '1px solid transparent',
                  }}>
                  <span style={{ width: 28, fontSize: 13, color: 'var(--text-muted)', textAlign: 'right' }}>{i + 1}</span>
                  <span style={{ flex: 1, fontSize: 14 }}>{sent.text}</span>

                  {/* Record button */}
                  {isActive && isRecording ? (
                    <button className="btn btn-danger btn-sm" onClick={stopRecording}>
                      ⏹ {recordTime.toFixed(1)}s
                    </button>
                  ) : (
                    <button className="btn btn-ghost btn-sm" onClick={() => startRecording(sent.id)}
                      disabled={isRecording} style={{ color: 'var(--danger)', fontSize: 16 }}>
                      🎙️
                    </button>
                  )}

                  {/* Play existing */}
                  {rec && (
                    <button className="btn btn-ghost btn-sm" onClick={() => playRecording(rec.id)}>▶</button>
                  )}

                  {/* Status */}
                  <span style={{ width: 20, textAlign: 'center' }}>
                    {rec ? '✅' : '⬜'}
                  </span>

                  {/* Duration */}
                  {rec && (
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', width: 40 }}>
                      {rec.duration?.toFixed(1)}s
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Submit training */}
        {selectedSet && recordings.recorded_count >= 10 && (
          <div style={{ marginTop: 'var(--space-6)', textAlign: 'right' }}>
            <button className="btn btn-primary btn-lg" onClick={() => window.location.href = '/training'}>
              Gửi yêu cầu Training →
            </button>
          </div>
        )}

        {!selectedSet && (
          <div className="empty-state">
            <p>Chọn một bộ câu để bắt đầu thu âm</p>
          </div>
        )}
      </div>
    </>
  );
}
