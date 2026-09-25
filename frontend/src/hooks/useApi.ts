import { useState, useCallback } from 'react';
import api from '../services/api';

interface UseApiOptions {
  immediate?: boolean;
}

export function useApi<T = any>(url: string, options: UseApiOptions = {}) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(options.immediate ?? false);

  const execute = useCallback(async (config: any = {}) => {
    setLoading(true);
    try {
      const response = await api.request({ url, ...config });
      setData(response.data);
      setError(null);
      return response.data;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [url]);

  return { data, error, loading, execute };
}

export function useAsync<T = any>(asyncFn: () => Promise<any>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  const execute = useCallback(async () => {
    setLoading(true);
    try {
      const result = await asyncFn();
      setData(result);
      setError(null);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, execute };
}
