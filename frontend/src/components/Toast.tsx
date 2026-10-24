import React, { useEffect, useRef } from 'react';
import { AlertCircle, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  type: 'error' | 'success' | 'info';
  message: string;
}

interface ToastProps {
  toast: ToastMessage | null;
  onDismiss: () => void;
  duration?: number;
}

export const Toast: React.FC<ToastProps> = ({ toast, onDismiss, duration = 4000 }) => {
  const onDismissRef = useRef(onDismiss);
  useEffect(() => {
    onDismissRef.current = onDismiss;
  });

  // I15: Key timer effect on toast.id and use onDismissRef so parent inline arrows don't restart timer
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => {
      onDismissRef.current();
    }, duration);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast?.id, duration]);

  if (!toast) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed bottom-[calc(5rem+env(safe-area-inset-bottom,0px))] left-1/2 -translate-x-1/2 z-50 w-full max-w-[390px] px-4 pointer-events-none"
    >
      <div className="pointer-events-auto flex items-center justify-between gap-3 p-3.5 bg-slate-900 text-white rounded-xl shadow-lg border border-slate-800 transition-all animate-in fade-in slide-in-from-bottom-2">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" aria-hidden="true" />
          <p className="text-xs sm:text-sm font-medium leading-snug break-words">
            {toast.message}
          </p>
        </div>

        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss notification"
          className="min-h-[44px] min-w-[44px] -mr-2 flex items-center justify-center text-slate-400 hover:text-white rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
