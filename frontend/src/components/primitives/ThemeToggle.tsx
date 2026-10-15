import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useT } from '../../i18n/I18nContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const t = useT();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="inline-flex items-center justify-center w-8 h-8 rounded-md border border-[var(--gc-border-default)] bg-[var(--gc-bg-default)] text-[var(--gc-text-secondary)] hover:text-[var(--gc-text-primary)] hover:bg-[var(--gc-bg-subtle)] transition-colors"
      aria-label={t('theme.toggle')}
      title={isDark ? t('theme.light') : t('theme.dark')}
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
    </button>
  );
}
