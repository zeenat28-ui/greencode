import { useState, useCallback } from 'react';

interface CopyState {
  hasCopied: boolean;
  copyToClipboard: (text: string) => Promise<void>;
}

const CLIPBOARD_TIMEOUT = 2000;

export function useCopyToClipboard(): CopyState {
  const [hasCopied, setHasCopied] = useState(false);

  const copyToClipboard = useCallback(async (text: string) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const el = document.createElement('textarea');
        el.value = text;
        el.style.position = 'fixed';
        el.style.opacity = '0';
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
      }
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), CLIPBOARD_TIMEOUT);
    } catch {
      setHasCopied(false);
    }
  }, []);

  return { hasCopied, copyToClipboard };
}
