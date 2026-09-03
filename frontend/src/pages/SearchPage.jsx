import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Loader2, FileText, ArrowUpRight, Sparkles } from 'lucide-react';
import { semanticSearch } from '../services/api';
import { PageHeader, EmptyState } from '../components/ui';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await semanticSearch(query.trim(), 10);
      setResults(data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const suggestions = ['GDPR compliance clauses', 'Financial projections', 'Risk factors', 'Key obligations'];

  return (
    <div className="animate-fade-in space-y-8 max-w-4xl mx-auto">
      <PageHeader title="Semantic Search" subtitle="Search across all documents using AI-powered similarity matching" />

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="glass-card p-2 flex items-center gap-3 border border-[var(--border-default)] focus-within:border-primary-500/40 transition-colors">
        <Search className="w-5 h-5 text-[var(--text-muted)] ml-3" />
        <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for clauses, financial terms, concepts..."
          className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none py-3" />
        <button type="submit" disabled={loading || !query.trim()}
          className="btn-primary text-sm flex items-center gap-2 disabled:opacity-50">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </form>

      {/* Quick suggestions */}
      {!results && !loading && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-2">
            {suggestions.map(s => (
              <button key={s} onClick={() => { setQuery(s); }}
                className="px-3 py-1.5 text-xs rounded-full border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-primary-400 hover:border-primary-500/30 transition-all">
                {s}
              </button>
            ))}
          </div>
          <div className="glass-card p-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-primary-400/50" />
            </div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Find anything in your documents</h3>
            <p className="text-sm text-[var(--text-muted)] max-w-md mx-auto">
              Use natural language to search. AI embeds your query and finds semantically similar passages across all documents.
            </p>
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-4 animate-fade-in">
          <p className="text-sm text-[var(--text-muted)]">
            {results.total} result{results.total !== 1 ? 's' : ''} for "<span className="text-primary-400 font-medium">{results.query}</span>"
          </p>
          {results.results.map((r, i) => (
            <Link key={i} to={`/documents/${r.document_id}`}
              className={`glass-card p-5 hover:border-primary-500/30 transition-all block group animate-slide-up delay-${Math.min(i + 1, 5)}`}>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-3 gap-3 sm:gap-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 rounded-xl bg-primary-500/15 flex items-center justify-center border border-primary-500/10 shrink-0">
                    <FileText className="w-4 h-4 text-primary-400" />
                  </div>
                  <span className="text-sm font-medium text-[var(--text-primary)] group-hover:text-primary-400 transition-colors truncate">{r.document_name}</span>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-2 w-full sm:w-auto">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                      <div className="h-full bg-primary-500 rounded-full" style={{ width: `${r.score * 100}%` }} />
                    </div>
                    <span className="text-xs text-primary-400 font-semibold">{(r.score * 100).toFixed(0)}%</span>
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-[var(--text-muted)] group-hover:text-primary-400 transition-colors shrink-0" />
                </div>
              </div>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{r.content}</p>
            </Link>
          ))}
          {results.total === 0 && (
            <EmptyState icon={Search} title="No results found"
              description={`Try different keywords or rephrase your search`} />
          )}
        </div>
      )}
    </div>
  );
}
