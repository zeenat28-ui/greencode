/**
 * Typed design tokens — the single source of truth for colors, spacing,
 * typography, and shadows.  These mirror the CSS custom properties defined
 * in `index.css` so that React components can reference them programmatically.
 *
 * @public
 */
export const tokens = {
  colors: {
    primary: {
      50: '#ecfdf5',
      100: '#d1fae5',
      200: '#a7f3d0',
      300: '#6ee7b7',
      400: '#34d399',
      500: '#10b981',
      600: '#059669',
      700: '#047857',
      800: '#065f46',
      900: '#064e3b',
      950: '#022c22',
    },
    neutral: {
      50: '#fafafa',
      100: '#f4f4f5',
      200: '#e4e4e7',
      300: '#d4d4d8',
      400: '#a1a1aa',
      500: '#71717a',
      600: '#52525b',
      700: '#3f3f46',
      800: '#27272a',
      900: '#18181b',
      950: '#09090b',
    },
    success: {
      DEFAULT: '#16a34a',
      50: '#dcfce7',
    },
    warning: {
      DEFAULT: '#d97706',
      50: '#ffedd5',
    },
    error: {
      DEFAULT: '#dc2626',
      50: '#fee2e2',
    },
    info: '#2563eb',
  },
  text: {
    primary: '#09090b',
    secondary: '#52525b',
    tertiary: '#71717a',
    inverse: '#fafafa',
  },
  surface: {
    canvas: '#fafafa',
    default: '#ffffff',
    subtle: '#f4f4f5',
    border: '#e4e4e7',
  },
  shadow: {
    xs: '0 1px 2px 0 rgba(9, 9, 11, 0.05)',
    sm: '0 1px 2px 0 rgba(9, 9, 11, 0.04), 0 1px 3px 0 rgba(9, 9, 11, 0.03)',
    md: '0 4px 8px -2px rgba(9, 9, 11, 0.08), 0 12px 28px -16px rgba(9, 9, 11, 0.18)',
    lg: '0 10px 25px -5px rgba(9, 9, 11, 0.12), 0 4px 6px -2px rgba(9, 9, 11, 0.05)',
  },
  radius: {
    sm: '0.375rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    xl2: '1.5rem',
    full: '9999px',
  },
  space: {
    '3xs': '0.25rem',
    '2xs': '0.5rem',
    xs: '0.75rem',
    sm: '1rem',
    md: '1.25rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '2.5rem',
    '3xl': '3rem',
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    md: '1.125rem',
    lg: '1.25rem',
    xl: '1.5rem',
    '2xl': '1.875rem',
    '3xl': '2.25rem',
  },
} as const;

export const GRID_ZONES = [
  { value: 'US-CAL-CISO', label: 'United States (California)' },
  { value: 'US-MIDW-MISO', label: 'United States (Midwest)' },
  { value: 'US-MIDA-PJM', label: 'United States (Mid-Atlantic)' },
  { value: 'US-TEX-ERCO', label: 'United States (Texas)' },
  { value: 'US-NE-ISNE', label: 'United States (New England)' },
  { value: 'CA-QC', label: 'Canada (Quebec)' },
  { value: 'DE', label: 'Germany' },
  { value: 'FR', label: 'France' },
  { value: 'GB', label: 'Great Britain' },
  { value: 'SE', label: 'Sweden' },
  { value: 'JP-TK', label: 'Japan' },
  { value: 'SG', label: 'Singapore' },
  { value: 'IN-WE', label: 'India (Western)' },
  { value: 'BR-CS', label: 'Brazil' },
] as const;

export type GridZone = typeof GRID_ZONES[number]['value'];