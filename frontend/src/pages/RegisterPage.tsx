import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../api/client';
import { UserPlus, AlertCircle } from 'lucide-react';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});
    setGeneralError(null);

    const errors: Record<string, string> = {};
    if (!email.trim()) {
      errors.email = 'Email is required.';
    }
    if (!password) {
      errors.password = 'Password is required.';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters.';
    }
    if (password && confirmPassword && password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.';
    } else if (password && !confirmPassword) {
      errors.confirmPassword = 'Please confirm your password.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);
    try {
      const browserTimezone =
        Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

      await register(email.trim(), password, browserTimezone);
      navigate('/', { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        const data = err.data;
        const newFieldErrors: Record<string, string> = {};
        const unhandledErrors: string[] = [];

        if (data.email) {
          newFieldErrors.email = Array.isArray(data.email) ? data.email.join(' ') : String(data.email);
        }
        if (data.password) {
          newFieldErrors.password = Array.isArray(data.password) ? data.password.join(' ') : String(data.password);
        }
        // I10: Show unknown fields (like timezone) in the general alert
        for (const [key, val] of Object.entries(data)) {
          if (key !== 'email' && key !== 'password' && key !== 'detail' && key !== 'non_field_errors') {
            const valStr = Array.isArray(val) ? val.join(' ') : String(val);
            unhandledErrors.push(`${key}: ${valStr}`);
          }
        }

        if (data.detail) {
          setGeneralError(String(data.detail));
        } else if (data.non_field_errors) {
          setGeneralError(
            Array.isArray(data.non_field_errors)
              ? data.non_field_errors.join(' ')
              : String(data.non_field_errors)
          );
        } else if (unhandledErrors.length > 0) {
          setGeneralError(unhandledErrors.join(' | '));
        } else if (Object.keys(newFieldErrors).length === 0) {
          setGeneralError(err.message || 'Registration failed. Please check your information.');
        }

        setFieldErrors(newFieldErrors);
      } else {
        // I4: If registration succeeded but auto-login failed
        navigate('/login?registered=1', { replace: true });
        return;
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center bg-slate-50 px-4 py-8 sm:px-6">
      <div className="w-full max-w-[375px] mx-auto">
        <div className="text-center mb-6">
          <span className="text-4xl select-none" role="img" aria-label="Habit Tracker Target">🎯</span>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
            Create your account
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Start tracking daily habits and keeping streaks
          </p>
        </div>

        <div className="bg-white px-5 py-6 shadow-sm ring-1 ring-slate-900/5 rounded-2xl sm:px-8">
          {generalError && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2.5 rounded-xl bg-red-50 p-3 text-sm text-red-700 border border-red-200"
            >
              <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
              <div className="flex-1">{generalError}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1"
              >
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                aria-invalid={!!fieldErrors.email}
                aria-describedby={fieldErrors.email ? 'email-error' : undefined}
                className={`w-full rounded-xl border px-3.5 py-2.5 text-base sm:text-sm outline-none transition duration-150 ${
                  fieldErrors.email
                    ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100 bg-red-50/20'
                    : 'border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
                }`}
              />
              {fieldErrors.email && (
                <p id="email-error" className="mt-1.5 text-xs text-red-600 font-medium">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                aria-invalid={!!fieldErrors.password}
                aria-describedby={fieldErrors.password ? 'password-error' : undefined}
                className={`w-full rounded-xl border px-3.5 py-2.5 text-base sm:text-sm outline-none transition duration-150 ${
                  fieldErrors.password
                    ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100 bg-red-50/20'
                    : 'border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
                }`}
              />
              {fieldErrors.password && (
                <p id="password-error" className="mt-1.5 text-xs text-red-600 font-medium">
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1"
              >
                Confirm password
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                aria-invalid={!!fieldErrors.confirmPassword}
                aria-describedby={fieldErrors.confirmPassword ? 'confirm-password-error' : undefined}
                className={`w-full rounded-xl border px-3.5 py-2.5 text-base sm:text-sm outline-none transition duration-150 ${
                  fieldErrors.confirmPassword
                    ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-100 bg-red-50/20'
                    : 'border-slate-300 focus:border-blue-600 focus:ring-2 focus:ring-blue-100'
                }`}
              />
              {fieldErrors.confirmPassword && (
                <p id="confirm-password-error" className="mt-1.5 text-xs text-red-600 font-medium">
                  {fieldErrors.confirmPassword}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 active:bg-blue-700 transition duration-150 disabled:opacity-60 disabled:cursor-not-allowed mt-2"
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  <span>Creating account...</span>
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  <span>Create account</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-blue-600 hover:text-blue-500 underline underline-offset-2"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
