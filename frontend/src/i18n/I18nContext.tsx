import { createContext, useCallback, useContext, useMemo, ReactNode } from 'react';
import en from './en.json';

type MessageTree = { [key: string]: string | MessageTree };

const dictionaries: Record<string, MessageTree> = { en: en as MessageTree };

function lookup(tree: MessageTree, path: string): string | undefined {
  const parts = path.split('.');
  let node: string | MessageTree | undefined = tree;
  for (const part of parts) {
    if (node == null || typeof node === 'string') return undefined;
    node = node[part];
  }
  return typeof node === 'string' ? node : undefined;
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, key: string) =>
    vars[key] == null ? `{${key}}` : String(vars[key]),
  );
}

export type TranslateFn = (key: string, vars?: Record<string, string | number>) => string;

interface I18nContextValue {
  locale: string;
  t: TranslateFn;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const locale = 'en';
  const t = useCallback<TranslateFn>((key, vars) => {
    const raw = lookup(dictionaries[locale], key) ?? lookup(dictionaries.en, key) ?? key;
    return interpolate(raw, vars);
  }, [locale]);

  const value = useMemo(() => ({ locale, t }), [locale, t]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useT(): TranslateFn {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useT must be used within I18nProvider');
  return ctx.t;
}

export function translateStatic(key: string, vars?: Record<string, string | number>): string {
  const raw = lookup(dictionaries.en, key) ?? key;
  return interpolate(raw, vars);
}
