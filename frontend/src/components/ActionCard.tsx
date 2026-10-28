import React, { useState } from 'react';
import {
  Check,
  X,
  Loader2,
  Sparkles,
  Clock,
  AlertCircle,
  PlusCircle,
  Edit3,
  Archive,
} from 'lucide-react';
import { PendingAction } from '../types/coach';
import { getErrorMessage } from '../utils/errorUtils';

interface ActionCardProps {
  action: PendingAction;
  onConfirm: (actionId: number) => Promise<void>;
  onCancel: (actionId: number) => Promise<void>;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  action,
  onConfirm,
  onCancel,
}) => {
  const [isConfirming, setIsConfirming] = useState<boolean>(false);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isExpired =
    action.status === 'expired' ||
    (action.status === 'pending' &&
      Boolean(action.expires_at) &&
      new Date(action.expires_at).getTime() <= Date.now());

  const handleConfirm = async () => {
    if (isConfirming || isCancelling) return;
    setErrorMessage(null);
    setIsConfirming(true);
    try {
      await onConfirm(action.id);
    } catch (err: unknown) {
      setErrorMessage(getErrorMessage(err, 'Failed to confirm action.'));
    } finally {
      setIsConfirming(false);
    }
  };

  const handleCancel = async () => {
    if (isConfirming || isCancelling) return;
    setErrorMessage(null);
    setIsCancelling(true);
    try {
      await onCancel(action.id);
    } catch (err: unknown) {
      setErrorMessage(getErrorMessage(err, 'Failed to cancel action.'));
    } finally {
      setIsCancelling(false);
    }
  };

  const renderActionIcon = () => {
    switch (action.action_type) {
      case 'create_habit':
        return <PlusCircle className="w-4 h-4 text-emerald-600" />;
      case 'update_habit':
        return <Edit3 className="w-4 h-4 text-blue-600" />;
      case 'archive_habit':
        return <Archive className="w-4 h-4 text-amber-600" />;
      default:
        return <Sparkles className="w-4 h-4 text-indigo-600" />;
    }
  };

  const getActionTitle = () => {
    switch (action.action_type) {
      case 'create_habit':
        return 'Create Habit';
      case 'update_habit':
        return 'Update Habit';
      case 'archive_habit':
        return 'Archive Habit';
      default:
        return 'Proposed Action';
    }
  };

  return (
    <div
      data-testid={`action-card-${action.id}`}
      className="mt-2.5 bg-white border border-slate-200 rounded-xl p-3 shadow-xs space-y-2.5 max-w-full"
    >
      {/* Header with Type & Status */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-2">
        <div className="flex items-center space-x-1.5">
          {renderActionIcon()}
          <span className="text-xs font-semibold text-slate-800">
            {getActionTitle()}
          </span>
        </div>

        {/* State Badges */}
        {action.status === 'confirmed' && (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <Check className="w-3 h-3 text-emerald-600" />
            <span>Confirmed</span>
          </span>
        )}

        {action.status === 'cancelled' && (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
            <X className="w-3 h-3 text-slate-500" />
            <span>Cancelled</span>
          </span>
        )}

        {isExpired && action.status !== 'confirmed' && action.status !== 'cancelled' && (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3 h-3 text-amber-600" />
            <span>Expired</span>
          </span>
        )}
      </div>

      {/* Summary Content */}
      <p className="text-xs text-slate-700 leading-relaxed font-medium">
        {action.summary}
      </p>

      {/* Inline Error Message */}
      {errorMessage && (
        <div className="p-2 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-1.5 text-[11px] text-red-700">
          <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
          <span className="flex-1">{errorMessage}</span>
        </div>
      )}

      {/* Interactive Buttons (Only shown if pending & not expired) */}
      {action.status === 'pending' && !isExpired && (
        <div className="flex items-center justify-end space-x-2 pt-1">
          <button
            type="button"
            onClick={handleCancel}
            disabled={isConfirming || isCancelling}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors flex items-center space-x-1 disabled:opacity-50"
            aria-label={isCancelling ? 'Cancelling' : 'Cancel'}
          >
            {isCancelling ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Cancelling...</span>
              </>
            ) : (
              <>
                <X className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleConfirm}
            disabled={isConfirming || isCancelling}
            className="px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors flex items-center space-x-1 disabled:opacity-50"
            aria-label={isConfirming ? 'Confirming' : 'Confirm'}
          >
            {isConfirming ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Confirming...</span>
              </>
            ) : (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Confirm</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
