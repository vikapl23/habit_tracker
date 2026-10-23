import { ApiError } from '../api/client';

export function getErrorMessage(err: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!err) return fallback;

  if (err instanceof ApiError) {
    if (err.data && typeof err.data === 'object') {
      if (typeof err.data.detail === 'string' && !err.data.detail.trim().startsWith('<')) {
        return err.data.detail;
      }
      if (Array.isArray(err.data.non_field_errors) && err.data.non_field_errors.length > 0) {
        return err.data.non_field_errors.join(' ');
      }
    }

    if (err.status === 0) {
      return 'Unable to connect to the server. Please check your internet connection.';
    }
    if (err.status === 401) {
      return 'Your session has expired or is invalid. Please sign in again.';
    }
    if (err.status === 403) {
      return 'You do not have permission to perform this action.';
    }
    if (err.status === 404) {
      return 'The requested resource was not found.';
    }
    if (err.status === 429) {
      return 'Too many requests. Please slow down and wait a moment.';
    }
    if (err.status >= 500) {
      return 'A temporary server error occurred. Please try again shortly.';
    }

    if (err.message && !err.message.includes('<') && err.message !== 'Validation error') {
      return err.message;
    }

    return fallback;
  }

  if (err instanceof Error) {
    if (err.message === 'Failed to fetch' || err.message.includes('NetworkError')) {
      return 'Unable to connect to the server. Please check your internet connection.';
    }
    if (!err.message.includes('<')) {
      return err.message;
    }
  }

  return fallback;
}
