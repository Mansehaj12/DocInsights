import { useState } from 'react';
import { KeyRound, X, Check, Trash2 } from 'lucide-react';
import { useToast } from './Toast';
import { setLlmCredentials, llmCredentials } from '../services/api';

/**
 * Bring-your-own-key settings.
 *
 * Lets the user paste their own OpenAI-compatible API key for this browser
 * session. The key lives only in memory (the api.js module holder) and is sent
 * per-request as a header. It is never saved to localStorage, so it clears on
 * refresh — and the backend never stores it. With no key, the app runs in mock
 * demo mode.
 */
export default function ApiKeySettings({ collapsed, mobileOpen }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState(llmCredentials.apiKey);
  const [model, setModel] = useState(llmCredentials.model);
  const [baseUrl, setBaseUrl] = useState(llmCredentials.baseUrl);

  const active = Boolean(llmCredentials.apiKey);

  const save = () => {
    setLlmCredentials({ apiKey, model, baseUrl });
    if (apiKey.trim()) {
      toast.success('API key set', 'Live LLM answers enabled for this session.');
    } else {
      toast.info('Demo mode', 'No key set — using mock responses.');
    }
    setOpen(false);
  };

  const clear = () => {
    setApiKey('');
    setModel('');
    setBaseUrl('');
    setLlmCredentials({ apiKey: '', model: '', baseUrl: '' });
    toast.info('Key cleared', 'Back to mock demo mode.');
    setOpen(false);
  };

  const showLabel = !collapsed || mobileOpen;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={collapsed && !mobileOpen ? 'API Key' : undefined}
        className="flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-all"
      >
        <span className="relative flex-shrink-0">
          <KeyRound className="w-5 h-5" />
          <span
            className={`absolute -top-1 -right-1 w-2 h-2 rounded-full ${active ? 'bg-green-400' : 'bg-[var(--text-muted)]'}`}
          />
        </span>
        {showLabel && <span>{active ? 'LLM Key · On' : 'Add LLM Key'}</span>}
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="glass-card-static w-full max-w-md p-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-primary-400" />
                <h2 className="text-lg font-bold text-[var(--text-primary)]">Bring your own LLM key</h2>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-[var(--text-muted)] mb-5 leading-relaxed">
              Your key is held in memory for this browser tab only — never saved to disk and
              never stored by the server. It clears when you refresh. Without a key the app runs
              in mock demo mode (retrieval still works; answers are placeholders).
            </p>

            <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">
              API key
            </label>
            <input
              type="password"
              autoComplete="off"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full px-3 py-2.5 mb-4 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] outline-none focus:border-primary-500/60"
            />

            <div className="grid grid-cols-1 gap-3 mb-5">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">
                  Model <span className="text-[var(--text-muted)] font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder="gpt-3.5-turbo"
                  className="w-full px-3 py-2.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] outline-none focus:border-primary-500/60"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5">
                  Base URL <span className="text-[var(--text-muted)] font-normal">(optional · OpenRouter, etc.)</span>
                </label>
                <input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://openrouter.ai/api/v1"
                  className="w-full px-3 py-2.5 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] text-sm text-[var(--text-primary)] outline-none focus:border-primary-500/60"
                />
              </div>
            </div>

            <div className="mb-5 px-3 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
              <p className="text-[11px] text-amber-300/90 leading-relaxed">
                <strong>Using OpenRouter?</strong> Set Base URL to the full{' '}
                <code className="text-amber-200">https://openrouter.ai/api/v1</code> and namespace the
                model, e.g. <code className="text-amber-200">openai/gpt-3.5-turbo</code> (not just{' '}
                <code className="text-amber-200">gpt-3.5-turbo</code>). Plain OpenAI keys need no base URL.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={save}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-semibold transition-colors"
              >
                <Check className="w-4 h-4" /> Save
              </button>
              {active && (
                <button
                  onClick={clear}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--bg-elevated)] hover:bg-white/5 text-[var(--text-secondary)] text-sm font-semibold transition-colors"
                >
                  <Trash2 className="w-4 h-4" /> Clear
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
