import { useEffect, useState } from 'react';
import api from '../services/api';

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

export function useApiWithKey<T>(url: string, key: string, initialValue: T) {
  const [data, setData] = useState<T>(initialValue);

  useEffect(() => {
    if (!key) return;
    api.get<T>(url + (url.includes('?') ? '&' : '?') + new URLSearchParams({ key }))
      .then(res => setData(res.data))
      .catch(() => {});
  }, [key, url]);

  return data;
}
