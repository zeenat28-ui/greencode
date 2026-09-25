import { useState } from 'react';

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const set = (val: T | ((prev: T) => T)) => {
    setValue(prev => {
      const v = typeof val === 'function' ? (val as any)(prev) : val;
      window.localStorage.setItem(key, JSON.stringify(v));
      return v;
    });
  };

  return [value, set] as const;
}
