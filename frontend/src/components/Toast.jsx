import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

const ToastContext = createContext(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const addToast = useCallback(({ type = 'info', title, message, duration = 4000 }) => {
    const id = ++idRef.current;
    setToasts(prev => [...prev, { id, type, title, message, exiting: false }]);
    if (duration > 0) {
      setTimeout(() => dismissToast(id), duration);
    }
    return id;
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t));
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 300);
  }, []);

  const toast = {
    success: (title, message) => addToast({ type: 'success', title, message }),
    error: (title, message) => addToast({ type: 'error', title, message }),
    warning: (title, message) => addToast({ type: 'warning', title, message }),
    info: (title, message) => addToast({ type: 'info', title, message }),
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed top-4 right-4 z-[100] space-y-3 pointer-events-none" style={{ maxWidth: 380 }}>
        {toasts.map((t) => (
          <Toast key={t.id} {...t} onDismiss={() => dismissToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};
const colors = {
  success: 'border-green-500/30 bg-green-500/10',
  error: 'border-red-500/30 bg-red-500/10',
  warning: 'border-amber-500/30 bg-amber-500/10',
  info: 'border-primary-500/30 bg-primary-500/10',
};
const iconColors = {
  success: 'text-green-400',
  error: 'text-red-400',
  warning: 'text-amber-400',
  info: 'text-primary-400',
};

function Toast({ type, title, message, exiting, onDismiss }) {
  const Icon = icons[type] || Info;
  return (
    <div className={`pointer-events-auto glass-card-static border px-4 py-3 flex items-start gap-3 
      ${colors[type]} ${exiting ? 'toast-exit' : 'toast-enter'}`}>
      <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${iconColors[type]}`} />
      <div className="flex-1 min-w-0">
        {title && <p className="text-sm font-semibold text-gray-200">{title}</p>}
        {message && <p className="text-xs text-gray-400 mt-0.5">{message}</p>}
      </div>
      <button onClick={onDismiss} className="p-1 rounded-lg hover:bg-white/5 text-gray-500 hover:text-gray-300 transition-colors">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
