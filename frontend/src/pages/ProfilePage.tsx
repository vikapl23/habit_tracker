import React, { useState, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Globe, LogOut, Check } from 'lucide-react';
import { BottomNavigation } from '../components/BottomNavigation';
import { Toast, ToastMessage } from '../components/Toast';
import { getErrorMessage } from '../utils/errorUtils';

const FALLBACK_TIMEZONES = [
  'UTC',
  'Africa/Cairo',
  'Africa/Johannesburg',
  'America/Argentina/Buenos_Aires',
  'America/Bogota',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Mexico_City',
  'America/New_York',
  'America/Sao_Paulo',
  'America/Toronto',
  'America/Vancouver',
  'Asia/Bangkok',
  'Asia/Dubai',
  'Asia/Hong_Kong',
  'Asia/Kolkata',
  'Asia/Seoul',
  'Asia/Shanghai',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Australia/Melbourne',
  'Australia/Sydney',
  'Europe/Amsterdam',
  'Europe/Berlin',
  'Europe/Brussels',
  'Europe/Dublin',
  'Europe/Kyiv',
  'Europe/London',
  'Europe/Madrid',
  'Europe/Paris',
  'Europe/Rome',
  'Europe/Warsaw',
  'Pacific/Auckland',
  'Pacific/Honolulu',
];

export const ProfilePage: React.FC = () => {
  const { user, logout, updateProfile } = useAuth();
  const [customTimezone, setCustomTimezone] = useState<string | null>(null);
  const selectedTimezone = customTimezone ?? user?.timezone ?? 'UTC';
  const [isSaving, setIsSaving] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const timezoneOptions = useMemo(() => {
    let supported: string[] = [];
    try {
      if (typeof Intl !== 'undefined' && 'supportedValuesOf' in Intl) {
        supported = Intl.supportedValuesOf('timeZone');
      }
    } catch {
      supported = [];
    }
    const combined = Array.from(new Set([...FALLBACK_TIMEZONES, ...supported]));
    if (user?.timezone && !combined.includes(user.timezone)) {
      combined.push(user.timezone);
    }
    return combined.sort((a, b) => a.localeCompare(b));
  }, [user?.timezone]);

  const handleSaveTimezone = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isSaving || !selectedTimezone) return;

    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await updateProfile({ timezone: selectedTimezone });
      setCustomTimezone(null);
      setSaveSuccess(true);
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: 'Timezone updated successfully.',
      });
    } catch (err: unknown) {
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: getErrorMessage(err, 'Failed to update timezone.'),
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  const hasTzChanged = selectedTimezone !== (user?.timezone || '');

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      <Toast toast={toast} onDismiss={() => setToast(null)} />

      <div className="w-full max-w-[420px] min-h-screen flex flex-col bg-white shadow-sm border-x border-slate-100 overflow-x-hidden relative">
        {/* Header */}
        <header className="px-5 py-4 pt-[calc(1rem+env(safe-area-inset-top,0px))] border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-2">
            <User className="w-5 h-5 text-blue-600" />
            <h1 className="text-base font-bold text-slate-900 leading-tight">Profile & Settings</h1>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-4 sm:p-5 pb-28 space-y-6">
          {/* User Info Card */}
          <section aria-labelledby="account-details-heading" className="rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center text-xl font-bold">
                {user?.email ? user.email.charAt(0).toUpperCase() : '👤'}
              </div>
              <div className="min-w-0 flex-1">
                <h2 id="account-details-heading" className="text-sm font-bold text-slate-900 truncate">
                  Account Details
                </h2>
                <p className="text-xs text-slate-500 truncate">{user?.email}</p>
              </div>
            </div>

            <div className="space-y-1 pt-2 border-t border-slate-100">
              <label htmlFor="profile-email" className="block text-xs font-semibold text-slate-700">
                Email Address
              </label>
              <input
                id="profile-email"
                type="email"
                readOnly
                disabled
                value={user?.email || ''}
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-600 text-sm cursor-not-allowed select-all"
              />
              <p className="text-[11px] text-slate-500">Email is read-only and managed by authentication.</p>
            </div>
          </section>

          {/* Timezone Settings Form */}
          <section aria-labelledby="timezone-settings-heading" className="rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-blue-600" />
              <h2 id="timezone-settings-heading" className="text-sm font-bold text-slate-900">
                Timezone Settings
              </h2>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Your daily habit check-in resets and streaks are calculated according to this timezone.
            </p>

            <form onSubmit={handleSaveTimezone} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="timezone-select" className="block text-xs font-semibold text-slate-700">
                  Select Timezone
                </label>
                <select
                  id="timezone-select"
                  value={selectedTimezone}
                  onChange={(e) => {
                    setCustomTimezone(e.target.value);
                    setSaveSuccess(false);
                  }}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-800 text-base sm:text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                >
                  {timezoneOptions.map((tz) => (
                    <option key={tz} value={tz}>
                      {tz}
                    </option>
                  ))}
                </select>
              </div>

              {saveSuccess && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">
                  <Check className="w-4 h-4 shrink-0" />
                  <span>Timezone saved successfully!</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isSaving || !hasTzChanged}
                className="w-full min-h-[44px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:pointer-events-none text-white text-xs font-semibold shadow-sm transition"
              >
                {isSaving ? (
                  <>
                    <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <span>Save Timezone</span>
                )}
              </button>
            </form>
          </section>

          {/* Session / Log Out */}
          <section aria-labelledby="session-heading" className="rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm space-y-3">
            <h2 id="session-heading" className="text-sm font-bold text-slate-900">
              Account Session
            </h2>
            <p className="text-xs text-slate-500 leading-relaxed">
              Sign out of this device. Your data will remain synced on the server.
            </p>

            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              aria-label="Log out of account"
              className="w-full min-h-[44px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 active:bg-red-100 disabled:opacity-50 text-xs font-semibold transition"
            >
              {isLoggingOut ? (
                <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-red-500 border-t-transparent" />
              ) : (
                <LogOut className="w-4 h-4 text-red-500" />
              )}
              <span>Log out</span>
            </button>
          </section>
        </main>

        {/* Bottom Navigation */}
        <BottomNavigation />
      </div>
    </div>
  );
};
