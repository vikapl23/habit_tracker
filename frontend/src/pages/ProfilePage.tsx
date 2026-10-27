import React, { useState, useMemo, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Globe, Bell, LogOut, Check, Search } from 'lucide-react';
import { BottomNavigation } from '../components/BottomNavigation';
import { Toast, ToastMessage } from '../components/Toast';
import { getErrorMessage } from '../utils/errorUtils';
import {
  formatTimezoneDisplay,
  getBrowserTimezone,
  getTimezoneOffsetString,
  normalizeTimezone,
} from '../utils/timezoneUtils';

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
  const detectedTimezone = useMemo(() => getBrowserTimezone(), []);
  const normalizedUserTimezone = normalizeTimezone(user?.timezone);

  // Auto toggle state
  const isAutoDefault = user?.timezone_auto ?? true;
  const [isAuto, setIsAuto] = useState<boolean>(isAutoDefault);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedTimezone, setSelectedTimezone] = useState<string>(
    normalizedUserTimezone || detectedTimezone || 'UTC'
  );

  const [isSaving, setIsSaving] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Notification preferences state
  const defaultNotificationsEnabled = user?.notifications_enabled ?? true;
  const defaultWeeklySummary = user?.weekly_summary_enabled ?? false;

  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(defaultNotificationsEnabled);
  const [weeklySummaryEnabled, setWeeklySummaryEnabled] = useState<boolean>(defaultWeeklySummary);
  const [isSavingNotifications, setIsSavingNotifications] = useState<boolean>(false);
  const [notificationsSaveSuccess, setNotificationsSaveSuccess] = useState<boolean>(false);

  // Sync state if user changes / finishes loading
  useEffect(() => {
    if (user) {
      if (user.notifications_enabled !== undefined) {
        setNotificationsEnabled(user.notifications_enabled);
      }
      if (user.weekly_summary_enabled !== undefined) {
        setWeeklySummaryEnabled(user.weekly_summary_enabled);
      }
    }
  }, [user]);

  const hasNotificationsChanged = useMemo(() => {
    if (notificationsEnabled !== defaultNotificationsEnabled) return true;
    if (weeklySummaryEnabled !== defaultWeeklySummary) return true;
    return false;
  }, [
    notificationsEnabled,
    defaultNotificationsEnabled,
    weeklySummaryEnabled,
    defaultWeeklySummary,
  ]);

  const handleSaveNotifications = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isSavingNotifications || !hasNotificationsChanged) return;

    setIsSavingNotifications(true);
    setNotificationsSaveSuccess(false);
    try {
      await updateProfile({
        notifications_enabled: notificationsEnabled,
        weekly_summary_enabled: weeklySummaryEnabled,
      });
      setNotificationsSaveSuccess(true);
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: 'Notification preferences updated.',
      });
    } catch (err: unknown) {
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: getErrorMessage(err, 'Failed to update notification preferences.'),
      });
    } finally {
      setIsSavingNotifications(false);
    }
  };

  // All known timezones with detected placed first
  const allTimezones = useMemo(() => {
    let supported: string[] = [];
    try {
      if (typeof Intl !== 'undefined' && 'supportedValuesOf' in Intl) {
        supported = Intl.supportedValuesOf('timeZone');
      }
    } catch {
      supported = [];
    }
    const set = new Set([...FALLBACK_TIMEZONES, ...supported]);
    if (normalizedUserTimezone) set.add(normalizedUserTimezone);
    if (detectedTimezone) set.add(detectedTimezone);

    const sorted = Array.from(set).sort((a, b) => a.localeCompare(b));
    // Ensure detected timezone is placed first
    const withoutDetected = sorted.filter((tz) => tz !== detectedTimezone);
    return detectedTimezone ? [detectedTimezone, ...withoutDetected] : sorted;
  }, [detectedTimezone, normalizedUserTimezone]);

  // Filtered by query
  const filteredTimezones = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allTimezones;
    return allTimezones.filter((tz) => {
      const display = tz.toLowerCase();
      const readable = tz.replace(/_/g, ' ').toLowerCase();
      return display.includes(q) || readable.includes(q);
    });
  }, [allTimezones, searchQuery]);

  const autoDisplayString = useMemo(() => {
    return formatTimezoneDisplay(detectedTimezone || normalizedUserTimezone || 'UTC');
  }, [detectedTimezone, normalizedUserTimezone]);

  const hasChanged = useMemo(() => {
    if (isAuto !== isAutoDefault) return true;
    if (!isAuto && selectedTimezone !== normalizedUserTimezone) return true;
    return false;
  }, [isAuto, isAutoDefault, selectedTimezone, normalizedUserTimezone]);

  const handleToggleAuto = () => {
    const nextAuto = !isAuto;
    setIsAuto(nextAuto);
    setSaveSuccess(false);
    if (nextAuto) {
      // Revert selection to detected when turning on auto
      setSelectedTimezone(detectedTimezone);
    }
  };

  const handleSaveTimezone = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isSaving || !hasChanged) return;

    setIsSaving(true);
    setSaveSuccess(false);
    try {
      const targetTimezone = isAuto ? detectedTimezone : selectedTimezone;
      await updateProfile({
        timezone: targetTimezone,
        timezone_auto: isAuto,
      });
      setSaveSuccess(true);
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: `Timezone updated to ${targetTimezone}.`,
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
              {/* Automatic Timezone Toggle */}
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/60">
                <div className="min-w-0 flex-1 pr-3">
                  <span id="auto-tz-label" className="block text-xs font-semibold text-slate-800">
                    Set timezone automatically
                  </span>
                  <span className="block text-xs text-slate-500 truncate">
                    {autoDisplayString}
                  </span>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={isAuto}
                  aria-labelledby="auto-tz-label"
                  onClick={handleToggleAuto}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    isAuto ? 'bg-blue-600' : 'bg-slate-300'
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                      isAuto ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Searchable Picker when Toggle is OFF */}
              {!isAuto && (
                <div className="space-y-2 pt-1 animate-in fade-in slide-in-from-top-1">
                  <label htmlFor="timezone-search" className="block text-xs font-semibold text-slate-700">
                    Select Timezone
                  </label>
                  <div className="relative">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      id="timezone-search"
                      type="text"
                      placeholder="Search timezone (e.g. kyiv, new york)"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-xs font-medium placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                    />
                  </div>

                  {/* Options list */}
                  <div
                    role="listbox"
                    aria-label="Timezone list"
                    className="max-h-52 overflow-y-auto rounded-xl border border-slate-200 bg-white divide-y divide-slate-100 shadow-inner"
                  >
                    {filteredTimezones.length === 0 ? (
                      <div className="p-3 text-center text-xs text-slate-400">
                        No timezones match "{searchQuery}"
                      </div>
                    ) : (
                      filteredTimezones.map((tz) => {
                        const isSelected = selectedTimezone === tz;
                        const isDetected = tz === detectedTimezone;
                        const offset = getTimezoneOffsetString(tz);
                        return (
                          <div
                            key={tz}
                            role="option"
                            aria-selected={isSelected}
                            onClick={() => {
                              setSelectedTimezone(tz);
                              setSaveSuccess(false);
                            }}
                            className={`min-h-[44px] px-3.5 py-2.5 flex items-center justify-between cursor-pointer text-xs font-medium transition ${
                              isSelected
                                ? 'bg-blue-50 text-blue-700 font-semibold'
                                : 'text-slate-700 hover:bg-slate-50'
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate">
                              <span className="truncate">{tz}</span>
                              <span className="text-[11px] text-slate-400 shrink-0">
                                ({offset})
                              </span>
                              {isDetected && (
                                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-700 shrink-0">
                                  Detected
                                </span>
                              )}
                            </div>
                            {isSelected && <Check className="w-4 h-4 text-blue-600 shrink-0" />}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              )}

              {saveSuccess && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">
                  <Check className="w-4 h-4 shrink-0" />
                  <span>Timezone saved successfully!</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isSaving || !hasChanged}
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

          {/* Notifications Settings Form */}
          <section
            aria-labelledby="notifications-settings-heading"
            className="rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm space-y-4"
          >
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-blue-600" />
              <h2 id="notifications-settings-heading" className="text-sm font-bold text-slate-900">
                Notifications
              </h2>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Configure daily email reminders for incomplete habits and your weekly summary report.
            </p>

            <form onSubmit={handleSaveNotifications} className="space-y-4">
              {/* Master Switch: Email notifications */}
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/60">
                <div className="min-w-0 flex-1 pr-3">
                  <span id="email-notifications-label" className="block text-xs font-semibold text-slate-800">
                    Email notifications
                  </span>
                  <span className="block text-xs text-slate-500">
                    Master switch for all email notifications, including habit reminders and weekly summaries.
                  </span>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={notificationsEnabled}
                  aria-labelledby="email-notifications-label"
                  onClick={() => {
                    setNotificationsEnabled(!notificationsEnabled);
                    setNotificationsSaveSuccess(false);
                  }}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    notificationsEnabled ? 'bg-blue-600' : 'bg-slate-300'
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                      notificationsEnabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {/* Weekly Summary Toggle */}
              <div className="flex items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50/60">
                <div className="min-w-0 flex-1 pr-3">
                  <span id="weekly-summary-label" className="block text-xs font-semibold text-slate-800">
                    Weekly summary
                  </span>
                  <span className="block text-xs text-slate-500">
                    Receive a summary of your streak and progress every Monday morning.
                  </span>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={weeklySummaryEnabled}
                  aria-labelledby="weekly-summary-label"
                  onClick={() => {
                    setWeeklySummaryEnabled(!weeklySummaryEnabled);
                    setNotificationsSaveSuccess(false);
                  }}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                    weeklySummaryEnabled ? 'bg-blue-600' : 'bg-slate-300'
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                      weeklySummaryEnabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>

              {notificationsSaveSuccess && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg p-2.5">
                  <Check className="w-4 h-4 shrink-0" />
                  <span>Notification preferences saved successfully!</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isSavingNotifications || !hasNotificationsChanged}
                className="w-full min-h-[44px] flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 disabled:pointer-events-none text-white text-xs font-semibold shadow-sm transition"
              >
                {isSavingNotifications ? (
                  <>
                    <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <span>Save Notifications</span>
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
