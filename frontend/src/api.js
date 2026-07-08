/**
 * Centralized API helper — every page calls through here.
 * Points at the FastAPI backend on port 8000.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function fetchApi(endpoint, params = {}) {
  const url = new URL(`${API_BASE}/${endpoint}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.append(key, value);
    }
  });

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

/** Format a number with commas, e.g. 25000 → "25,000" */
export function formatNumber(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-US');
}

/** Format as currency (EGP by default) */
export function formatSalary(n, currency) {
  if (n == null) return '—';
  const num = Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 });
  return `${num} ${currency || 'EGP'}`;
}

/** Format percentage */
export function formatPct(n) {
  if (n == null) return '—';
  return `${Number(n).toFixed(1)}%`;
}

/** Chart color palette */
export const CHART_COLORS = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#8b5cf6', '#14b8a6',
  '#f97316', '#a855f7',
];

/**
 * Display utility: Moves the exact category "Other" to the end of a ranked array.
 * Keeps all other elements in their original order. Does not mutate the original array.
 */
export function sortWithOtherLast(data, key = 'category_name') {
  if (!Array.isArray(data)) return data;
  const otherItems = data.filter(item => item[key] === 'Other');
  if (otherItems.length === 0) return data;
  const nonOtherItems = data.filter(item => item[key] !== 'Other');
  return [...nonOtherItems, ...otherItems];
}
