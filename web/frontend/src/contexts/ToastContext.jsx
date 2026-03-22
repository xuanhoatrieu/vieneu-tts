import { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info', opts = {}) => {
    const id = opts.id || Date.now();
    setToasts(prev => {
      // Replace existing toast with same id
      const filtered = prev.filter(t => t.id !== id);
      return [...filtered, { id, message, type }];
    });
    // Auto-dismiss unless persistent (loading toasts are persistent)
    if (!opts.persistent) {
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
    }
    return id;
  }, []);

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const success = useCallback((msg) => addToast(msg, 'success'), [addToast]);
  const error   = useCallback((msg) => addToast(msg, 'error'), [addToast]);
  const info    = useCallback((msg) => addToast(msg, 'info'), [addToast]);
  const loading = useCallback((msg, opts = {}) => addToast(msg, 'info', { ...opts, persistent: true }), [addToast]);

  return (
    <ToastContext.Provider value={{ success, error, info, loading, dismiss }}>
      {children}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>{t.message}</div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
