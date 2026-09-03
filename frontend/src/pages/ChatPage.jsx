import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Loader2, User, Bot, FileText, Sparkles, Copy, Check } from 'lucide-react';
import { getDocument, chatWithDocument, getChatHistory } from '../services/api';
import { useToast } from '../components/Toast';

export default function ChatPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const toast = useToast();

  useEffect(() => { loadChat(); }, [id]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const loadChat = async () => {
    try {
      const [docData, historyData] = await Promise.all([
        getDocument(id),
        getChatHistory(id).catch(() => ({ messages: [] })),
      ]);
      setDoc(docData);
      setMessages(historyData.messages || []);
    } catch (err) {
      console.error(err);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: question, created_at: new Date().toISOString() }]);
    setLoading(true);

    try {
      const response = await chatWithDocument(id, question);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        created_at: new Date().toISOString(),
      }]);
    } catch (err) {
      toast.error('Chat Error', 'Failed to get response');
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
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

  if (initialLoading) return <ChatSkeleton />;

  const suggestions = [
    'What are the main topics covered?',
    'Summarize the key findings',
    'What risks or concerns are mentioned?',
    'What are the important dates or deadlines?',
  ];

  return (
    <div className="animate-fade-in flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 glass-card-static px-4 sm:px-5 py-3">
        <Link to={`/documents/${id}`} className="p-2 flex-shrink-0 rounded-lg hover:bg-[var(--bg-elevated)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm sm:text-base font-bold text-[var(--text-primary)] truncate">Chat</h1>
          <p className="text-[10px] sm:text-xs text-[var(--text-muted)] truncate">{doc?.original_filename}</p>
        </div>
        <Link to={`/documents/${id}`}
          className="btn-ghost flex items-center gap-1.5 sm:gap-2 text-xs border border-[var(--border-subtle)] px-2 sm:px-3">
          <FileText className="w-3.5 h-3.5" /> <span className="hidden sm:inline">View Doc</span><span className="sm:hidden">Doc</span>
        </Link>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500/20 to-green-500/10 flex items-center justify-center mb-5 animate-float border border-primary-500/10">
              <Bot className="w-10 h-10 text-primary-400" />
            </div>
            <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">Ask anything about this document</h3>
            <p className="text-sm text-[var(--text-muted)] mb-8 max-w-md">
              I'll search through the document content and provide grounded answers with source citations.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
              {suggestions.map((s) => (
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
          <ChatBubble key={i} msg={msg} documentId={id} navigate={navigate} />
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
                Searching document...
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
            placeholder="Ask a question about this document..."
            rows={1}
            className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none resize-none max-h-32 leading-relaxed"
            style={{ minHeight: '2.25rem' }}
          />
          <button onClick={handleSend} disabled={!input.trim() || loading}
            className="p-2.5 rounded-xl bg-gradient-to-r from-primary-600 to-purple-600 hover:from-primary-500 hover:to-purple-500 disabled:from-gray-700 disabled:to-gray-700 disabled:text-gray-500 text-white transition-all shadow-lg shadow-primary-600/20 disabled:shadow-none">
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ msg, documentId, navigate }) {
  const [copied, setCopied] = useState(false);

  const handleHighlightClick = (h) => {
    try {
      const data = { start_char: h.start_char, end_char: h.end_char, text: h.text?.slice(0, 300), page_number: h.page_number };
      navigate(`/documents/${documentId}?tab=text&highlight=${encodeURIComponent(JSON.stringify(data))}`);
    } catch { /* ignore encoding errors */ }
  };

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
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'chat-user' : 'chat-assistant'} group relative`}>
        <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed">{msg.content}</p>

        {/* Copy button */}
        {msg.role === 'assistant' && (
          <button onClick={handleCopy}
            className="absolute -top-2 -right-2 p-1.5 rounded-lg bg-[var(--bg-elevated)] border border-[var(--border-subtle)] opacity-0 group-hover:opacity-100 transition-opacity text-[var(--text-muted)] hover:text-[var(--text-primary)]">
            {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          </button>
        )}

        {/* Sources */}
        {msg.sources?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
            <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-semibold mb-2">Sources</p>
            <div className="space-y-2">
              {msg.sources.map((src, j) => (
                <div key={j} className="p-2.5 rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)]">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-primary-400 font-semibold">Chunk {src.chunk_index + 1}</span>
                    <div className="flex items-center gap-1.5">
                      {src.page && <span className="text-[10px] text-[var(--text-muted)]">p.{src.page}</span>}
                      <div className="w-12 h-1.5 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                        <div className="h-full bg-primary-500 rounded-full" style={{ width: `${(src.relevance_score * 100)}%` }} />
                      </div>
                      <span className="text-[10px] text-[var(--text-muted)]">{(src.relevance_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] line-clamp-2 leading-relaxed">{src.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Highlights (evidence-based) */}
        {msg.highlights?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
            <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-semibold mb-2">Evidence</p>
            <div className="space-y-2">
              {msg.highlights.map((h, j) => (
                <button key={j} onClick={() => handleHighlightClick(h)}
                  className="w-full text-left p-2.5 rounded-lg bg-amber-500/5 border border-amber-500/10 hover:bg-amber-500/10 hover:border-amber-500/20 transition-all cursor-pointer group/hl">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-amber-400 font-semibold flex items-center gap-1.5">
                      Chunk {h.chunk_index + 1}
                      <span className="text-[9px] text-amber-400/50 group-hover/hl:text-amber-400/80 transition-colors">↗ View in doc</span>
                    </span>
                    <div className="flex items-center gap-1.5">
                      {h.page_number && <span className="text-[10px] text-[var(--text-muted)]">p.{h.page_number}</span>}
                      {h.start_char != null && (
                        <span className="text-[10px] text-[var(--text-muted)]">chars {h.start_char}–{h.end_char}</span>
                      )}
                      <span className="text-[10px] text-amber-400">{(h.relevance_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] line-clamp-3 leading-relaxed italic">"{h.text?.slice(0, 200)}{h.text?.length > 200 ? '...' : ''}"</p>
                </button>
              ))}
            </div>
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

function ChatSkeleton() {
  return (
    <div className="animate-pulse flex flex-col h-[calc(100vh-4rem)]">
      <div className="h-14 skeleton rounded-xl mb-4" />
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-20 h-20 skeleton rounded-2xl mx-auto" />
          <div className="h-6 skeleton w-64 mx-auto rounded-lg" />
          <div className="h-4 skeleton w-48 mx-auto rounded-lg" />
        </div>
      </div>
      <div className="h-14 skeleton rounded-xl" />
    </div>
  );
}
