import React from 'react';
import { AlertTriangle, Trash2 } from 'lucide-react';

interface DeleteConfirmDialogProps {
  isOpen: boolean;
  habitName: string;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const DeleteConfirmDialog: React.FC<DeleteConfirmDialogProps> = ({
  isOpen,
  habitName,
  isDeleting,
  onConfirm,
  onCancel,
}) => {
  React.useEffect(() => {
    if (!isOpen) return;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isDeleting) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isDeleting, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
      aria-describedby="delete-dialog-desc"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={() => {
        if (!isDeleting) onCancel();
      }}
    >
      <div
        className="w-full max-w-[340px] rounded-2xl bg-white p-5 shadow-xl border border-slate-100 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-11 h-11 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
          <AlertTriangle className="w-5 h-5" />
        </div>

        <div className="text-center space-y-1">
          <h3 id="delete-dialog-title" className="text-base font-bold text-slate-900">
            Delete habit?
          </h3>
          <p id="delete-dialog-desc" className="text-xs text-slate-500 leading-relaxed">
            Are you sure you want to permanently delete{' '}
            <strong className="text-slate-700 font-semibold">{habitName}</strong>? This action
            cannot be undone and all streak history will be lost.
          </p>
        </div>

        <div className="flex gap-2.5 pt-1">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="flex-1 min-h-[44px] rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 active:bg-slate-100 transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 min-h-[44px] rounded-xl bg-red-600 text-xs font-semibold text-white hover:bg-red-700 active:bg-red-800 transition shadow-sm flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            {isDeleting ? (
              <div className="w-4 h-4 rounded-full border-2 border-white/60 border-t-white animate-spin" />
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
