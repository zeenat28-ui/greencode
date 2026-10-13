type ClassValue = string | undefined | null | false | ClassDictionary | ClassList;
interface ClassDictionary { [id: string]: unknown; }
type ClassList = ClassValue[];

function toClassNames(value: ClassValue): string {
  if (value === null || value === undefined || value === false) return '';
  if (typeof value === 'string') return value.trim();
  if (Array.isArray(value)) return value.map(toClassNames).filter(Boolean).join(' ');
  if (typeof value === 'object') {
    return Object.entries(value as ClassDictionary)
      .filter(([, v]) => v)
      .map(([k]) => k)
      .join(' ');
  }
  return '';
}

export function cn(...inputs: ClassValue[]): string {
  return inputs
    .map(toClassNames)
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function cx(...inputs: ClassValue[]): string {
  return cn(...inputs);
}
