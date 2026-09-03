import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, Send, Loader2, User, Bot, FileText, Sparkles,
  Copy, Check, CheckSquare, MessagesSquare
} from 'lucide-react';
import { getDocuments, multiDocumentChat } from '../services/api';
import { useToast } from '../components/Toast';

export default function MultiChatPage() {
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const toast = useToast();

  useEffect(() => {
    getDocuments()
      .then(d => {
        setDocuments(d.documents.filter(doc => doc.status === 'ready'));
      })
      .catch(console.error)
      .finally(() => setInitialLoading(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggle = (id) => {
    setSelected(prev =>
      prev.includes(id)
        ? prev.filter(x => x !== id)
        : prev.length < 5
          ? [...prev, id]
          : prev
    );
  };

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading || selected.length < 2) return;

    setInput('');
    setMessages(prev => [...prev, {
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }]);
    setLoading(true);

    try {
      const response = await multiDocumentChat(selected, question);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        highlights: response.highlights,
        document_groups: response.document_groups,
        created_at: new Date().toISOString(),
      }]);
    } catch (err) {
      toast.error('Chat Error', err.response?.data?.detail || 'Failed to get response');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your multi-document question. Please try again.',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const selectedDocs = documents.filter(d => selected.includes(d.id));

  if (initialLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-14 skeleton rounded-xl" />
        <div className="h-40 skeleton rounded-xl" />
        <div className="flex-1 h-64 skeleton rounded-xl" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 glass-card-static px-4 sm:px-5 py-3">
        <Link to="/" className="p-2 flex-shrink-0 rounded-lg hover:bg-[var(--bg-elevated)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm sm:text-base font-bold text-[var(--text-primary)]">Multi-Document Chat</h1>
          <p className="text-[10px] sm:text-xs text-[var(--text-muted)]">
            {selected.length < 2
              ? `Select at least 2 documents (${selected.length}/5)`
              : `Chatting across ${selected.length} documents`}
          </p>
        </div>
      </div>

      {/* Document Selector (collapsible) */}
      {messages.length === 0 && (
        <div className="glass-card-static mb-4 overflow-hidden">
          <div className="p-4 border-b border-[var(--border-subtle)]">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)]">
              Select Documents ({selected.length}/5)
            </h3>
          </div>
          {documents.length > 0 ? (
            <div className="max-h-48 overflow-y-auto divide-y divide-[var(--border-subtle)]">
              {documents.map(doc => {
                const isSelected = selected.includes(doc.id);
                return (
                  <button key={doc.id} onClick={() => toggle(doc.id)}
                    className={`w-full flex items-center gap-3 p-3 transition-all text-left hover:bg-[var(--bg-elevated)] min-w-0
                      ${isSelected ? 'bg-primary-600/10' : ''}`}>
                    <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all shrink-0
                      ${isSelected ? 'bg-primary-600 border-primary-600' : 'border-[var(--border-default)]'}`}>
                      {isSelected && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                    </div>
                    <FileText className="w-4 h-4 text-primary-400 shrink-0" />
                    <span className="text-sm text-[var(--text-primary)] font-medium truncate flex-1">
                      {doc.original_filename}
                    </span>
                    <span className="text-xs text-[var(--text-muted)] shrink-0">
                      {doc.file_type.toUpperCase()}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center text-[var(--text-muted)] text-sm">
              No documents ready. Upload and process documents first.
            </div>
          )}
        </div>
      )}

      {/* Selected docs pills (when chatting) */}
      {messages.length > 0 && selectedDocs.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {selectedDocs.map(doc => (
            <span key={doc.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-primary-600/10 border border-primary-500/20 text-xs text-primary-400">
              <FileText className="w-3 h-3" />
              {doc.original_filename}
            </span>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
        {messages.length === 0 && selected.length >= 2 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500/20 to-green-500/10 flex items-center justify-center mb-5 animate-float border border-primary-500/10">
              <MessagesSquare className="w-10 h-10 text-primary-400" />
            </div>
            <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">
              Ask across {selected.length} documents
            </h3>
            <p className="text-sm text-[var(--text-muted)] mb-8 max-w-md">
              I'll search all selected documents and provide a comprehensive answer with per-document source attribution.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {[
                'Compare the key findings across these documents',
                'What are the common themes?',
                'Summarize the differences between these documents',
                'What risks are mentioned across all documents?',
              ].map((s) => (
                <button key={s} onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  className="text-left text-xs p-4 rounded-xl glass-card-static border border-[var(--border-subtle)] hover:border-primary-500/30 hover:bg-primary-600/5 text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-all duration-200 group">
                  <Sparkles className="w-3.5 h-3.5 text-primary-400/50 group-hover:text-primary-400 mb-2 transition-colors" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <MultiChatBubble key={i} msg={msg} />
        ))}

        {loading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-xl bg-green-500/15 flex-shrink-0 flex items-center justify-center border border-green-500/10">
              <Bot className="w-4 h-4 text-green-400" />
            </div>
            <div className="chat-assistant rounded-2xl px-4 py-3 max-w-[75%]">
              <div className="flex items-center gap-3 text-sm text-[var(--text-muted)]">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                Searching {selected.length} documents...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="glass-card-static p-3 border border-[var(--border-default)]">
        <div className="flex items-end gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={selected.length < 2 ? "Select at least 2 documents above..." : "Ask a question across all selected documents..."}
            disabled={selected.length < 2}
            rows={1}
            className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none resize-none max-h-32 leading-relaxed disabled:opacity-50"
            style={{ minHeight: '2.25rem' }}
          />
          <button onClick={handleSend} disabled={!input.trim() || loading || selected.length < 2}
            className="p-2.5 rounded-xl bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-500 hover:to-purple-500 disabled:from-gray-700 disabled:to-gray-700 disabled:text-gray-500 text-white transition-all shadow-lg shadow-primary-600/20 disabled:shadow-none">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}


function MultiChatBubble({ msg }) {
  const [copied, setCopied] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      {msg.role === 'assistant' && (
        <div className="w-8 h-8 rounded-xl bg-green-500/15 flex-shrink-0 flex items-center justify-center border border-green-500/10">
          <Bot className="w-4 h-4 text-green-400" />
        </div>
      )}
      <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'chat-user' : 'chat-assistant'} group relative`}>
        <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed">{msg.content}</p>

        {/* Copy button */}
        {msg.role === 'assistant' && (
          <button onClick={handleCopy}
            className="absolute -top-2 -right-2 p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] opacity-0 group-hover:opacity-100 transition-opacity text-[var(--text-muted)] hover:text-[var(--text-primary)]">
            {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          </button>
        )}

        {/* Document Groups */}
        {msg.document_groups?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
            <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-semibold mb-2">Sources by Document</p>
            <div className="space-y-3">
              {msg.document_groups.map((group, gi) => (
                <div key={gi} className="p-2.5 rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)]">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="w-3.5 h-3.5 text-primary-400" />
                    <span className="text-xs text-primary-400 font-semibold">{group.document_name}</span>
                    <span className="text-[10px] text-[var(--text-muted)]">({group.sources.length} chunks)</span>
                  </div>
                  <div className="space-y-1.5">
                    {group.sources.map((src, si) => (
                      <div key={si} className="flex items-start gap-2">
                        <span className="text-[10px] text-[var(--text-muted)] mt-0.5 shrink-0">#{src.chunk_index + 1}</span>
                        <p className="text-xs text-[var(--text-muted)] line-clamp-1 leading-relaxed">{src.content}</p>
                        <span className="text-[10px] text-primary-400 shrink-0">{(src.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Evidence toggle */}
        {msg.highlights?.length > 0 && (
          <div className="mt-2">
            <button onClick={() => setShowEvidence(!showEvidence)}
              className="text-[10px] text-amber-400 hover:text-amber-300 transition-colors uppercase tracking-widest font-semibold">
              {showEvidence ? 'Hide' : 'Show'} Evidence ({msg.highlights.length})
            </button>
            {showEvidence && (
              <div className="mt-2 space-y-2 animate-fade-in">
                {msg.highlights.map((h, j) => (
                  <div key={j} className="p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/10">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-amber-400 font-semibold">Chunk {h.chunk_index + 1}</span>
                      <div className="flex items-center gap-1.5">
                        {h.page_number && <span className="text-[10px] text-[var(--text-muted)]">p.{h.page_number}</span>}
                        {h.start_char != null && (
                          <span className="text-[10px] text-[var(--text-muted)]">chars {h.start_char}–{h.end_char}</span>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-[var(--text-muted)] line-clamp-3 leading-relaxed italic">
                      "{h.text?.slice(0, 200)}{h.text?.length > 200 ? '...' : ''}"
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      {msg.role === 'user' && (
        <div className="w-8 h-8 rounded-xl bg-primary-500/15 flex-shrink-0 flex items-center justify-center border border-primary-500/10">
          <User className="w-4 h-4 text-primary-400" />
        </div>
      )}
    </div>
  );
}
