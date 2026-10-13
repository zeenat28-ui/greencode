import { tokens } from '../styles/tokens';

export { tokens, GRID_ZONES } from '../styles/tokens';

export const theme = {
  colors: {
    primary: tokens.colors.primary[600],
    primaryHover: tokens.colors.primary[700],
    primaryDark: tokens.colors.primary[950],
    dark: '#0f172a',
    amber: tokens.colors.warning.DEFAULT,
    amberLight: tokens.colors.warning[50],
    red: tokens.colors.error.DEFAULT,
    green: tokens.colors.success.DEFAULT,
    slate: tokens.colors.neutral,
  },
  gradients: {
    primary: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
    light: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
  },
} as const;