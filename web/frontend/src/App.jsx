import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import TTSStudioPage from './pages/TTSStudioPage';
import VoiceLibraryPage from './pages/VoiceLibraryPage';
import RecordingStudioPage from './pages/RecordingStudioPage';
import TrainingPage from './pages/TrainingPage';
import APIKeysPage from './pages/APIKeysPage';
import AdminDashboardPage from './pages/AdminDashboardPage';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-page"><span className="spinner" /> Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AdminRoute({ children }) {
  const { isAdmin, loading } = useAuth();
  if (loading) return <div className="loading-page"><span className="spinner" /></div>;
  if (!isAdmin) return <Navigate to="/studio" replace />;
  return children;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-page"><span className="spinner" /> VieNeu TTS</div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/studio" replace /> : <LoginPage />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/studio" element={<TTSStudioPage />} />
        <Route path="/voices" element={<VoiceLibraryPage />} />
        <Route path="/recording" element={<RecordingStudioPage />} />
        <Route path="/training" element={<TrainingPage />} />
        <Route path="/api-keys" element={<APIKeysPage />} />
        <Route path="/admin" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
        <Route path="/admin/queue" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
        <Route path="/admin/sets" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
      </Route>
      <Route path="*" element={<Navigate to="/studio" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
