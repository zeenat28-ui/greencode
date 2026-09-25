export function save(key: string, value: any): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn('Failed to save to localStorage:', e);
  }
}

export function load<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch {
    return defaultValue;
  }
}

export function remove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {}
}

export function clearAll(): void {
  try {
    localStorage.clear();
  } catch {}
}
