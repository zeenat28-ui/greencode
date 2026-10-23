import { useState } from 'react';
import type { FormEvent } from 'react';
import { Loader2, Mic, MicOff, Send, Volume2, X } from 'lucide-react';
import { useAlexaVoice } from '../../hooks/useAlexaVoice';
import { useT } from '../../i18n/I18nContext';

export default function AlexaAssistant() {
  const t = useT();
  const voice = useAlexaVoice();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const submitQuery = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = query.trim();
    if (!message || voice.isProcessing) return;
    setQuery('');
    void voice.sendText(message);
  };

  const close = () => {
    if (voice.isHandsFree) voice.toggleMic();
    setOpen(false);
  };
  const togglePanel = () => {
    if (open) close();
    else setOpen(true);
  };

  return (
    <div className="gc-voice-assistant fixed bottom-10 right-4 sm:right-6 z-50 flex flex-col items-end gap-3">
      {open && (
        <section
          aria-label={t('voice.title')}
          className="w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-emerald-800 bg-white shadow-xl"
        >
          <header className="flex items-center justify-between gap-3 bg-[#103f2b] px-4 py-3 text-white">
            <div className="min-w-0">
              <p className="text-sm font-semibold">{t('voice.title')}</p>
              <p className="text-xs text-emerald-100">{t('voice.subtitle')}</p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label={t('voice.close')}
              className="rounded-md p-1.5 text-emerald-50 hover:bg-white/10"
            >
              <X size={16} />
            </button>
          </header>

          <div className="space-y-3 p-4">
            <div aria-live="polite" className="min-h-20 rounded-lg border border-emerald-200 bg-emerald-50/70 p-3">
              {voice.isListening ? (
                <p className="flex items-center gap-2 text-sm font-medium text-emerald-900">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-600" />
                  {t('voice.listening')}
                </p>
              ) : voice.isProcessing ? (
                <p className="flex items-center gap-2 text-sm font-medium text-emerald-900">
                  <Loader2 size={15} className="animate-spin" />
                  {t('voice.processing')}
                </p>
              ) : voice.lastReply ? (
                <div className="space-y-2">
                  {voice.lastUtterance && (
                    <p className="text-xs text-emerald-800">
                      <span className="font-semibold">{t('voice.youSaid')} </span>
                      {voice.lastUtterance}
                    </p>
                  )}
                  <p className="text-sm leading-relaxed text-slate-900">{voice.lastReply}</p>
                </div>
              ) : (
                <p className="text-sm leading-relaxed text-slate-700">
                  {voice.isHandsFree && !voice.lastReply
                    ? t('voice.handsFreeReady')
                    : voice.speechSupported
                      ? t('voice.ready')
                      : t('voice.typeInstead')}
                </p>
              )}
            </div>
            <p className="text-xs leading-relaxed text-slate-600">
              {t('voice.releaseBriefingHint')}
            </p>

            <div className="flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={voice.toggleMic}
                disabled={!voice.speechSupported}
                aria-pressed={voice.isHandsFree}
                className={`inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                  voice.isHandsFree ? 'bg-rose-700 hover:bg-rose-800' : 'bg-[#0e482f] hover:bg-[#0a3824]'
                }`}
              >
                {voice.isHandsFree ? <MicOff size={16} /> : <Mic size={16} />}
                {voice.isHandsFree ? t('voice.stop') : t('voice.startHandsFree')}
              </button>
              <span className="flex items-center gap-1 text-xs text-slate-600">
                <Volume2 size={14} />
                {t('voice.replySpoken')}
              </span>
            </div>

            <form onSubmit={submitQuery} className="flex gap-2 border-t border-slate-200 pt-3">
              <label className="sr-only" htmlFor="voice-assistant-query">{t('voice.inputLabel')}</label>
              <input
                id="voice-assistant-query"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                disabled={voice.isProcessing}
                placeholder={t('voice.inputPlaceholder')}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 focus:border-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-700/20 disabled:bg-slate-100"
              />
              <button
                type="submit"
                disabled={!query.trim() || voice.isProcessing}
                aria-label={t('voice.send')}
                className="inline-flex min-h-10 min-w-10 items-center justify-center rounded-lg bg-[#0e482f] text-white hover:bg-[#0a3824] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {voice.isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Send size={15} />}
              </button>
            </form>
            {!voice.speechSupported && (
              <p className="text-xs leading-relaxed text-slate-600">{t('voice.unsupported')}</p>
            )}
          </div>
        </section>
      )}

      <button
        type="button"
        onClick={togglePanel}
        aria-label={open ? t('voice.close') : t('voice.open')}
        aria-expanded={open}
        className="inline-flex h-12 w-12 items-center justify-center rounded-full border-2 border-emerald-300 bg-[#0e482f] text-white shadow-lg transition-transform hover:scale-105 hover:bg-[#0a3824] focus-visible:outline-offset-4"
      >
        {open ? <X size={20} /> : <Mic size={20} />}
      </button>
    </div>
  );
}
