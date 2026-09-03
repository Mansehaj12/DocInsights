import { useState, useEffect } from 'react';
import { GitCompare, Loader2, CheckSquare, FileText, ArrowRight, CheckCircle } from 'lucide-react';
import { getDocuments, compareDocuments } from '../services/api';
import { PageHeader, EmptyState } from '../components/ui';
import { useToast } from '../components/Toast';

export default function ComparePage() {
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    getDocuments().then(d => setDocuments(d.documents.filter(doc => doc.status === 'ready'))).catch(console.error);
  }, []);

  const toggle = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 5 ? [...prev, id] : prev);
  };

  const handleCompare = async () => {
    if (selected.length < 2) return;
    setLoading(true);
    try {
      const data = await compareDocuments(selected);
      setResult(data);
      toast.success('Comparison Complete', `${selected.length} documents compared`);
    } catch (err) {
      toast.error('Comparison Failed', err.response?.data?.detail || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in space-y-8">
      <PageHeader title="Compare Documents" subtitle="Select 2–5 documents to find similarities and differences" />

      {/* Document selector */}
      <div className="glass-card overflow-hidden">
        <div className="p-5 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)]">Select Documents ({selected.length}/5)</h3>
          <button onClick={handleCompare} disabled={selected.length < 2 || loading}
            className="btn-primary text-sm flex items-center gap-2 disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />}
            Compare
          </button>
        </div>
        {documents.length > 0 ? (
          <div className="divide-y divide-[var(--border-subtle)]">
            {documents.map(doc => {
              const isSelected = selected.includes(doc.id);
              return (
                <button key={doc.id} onClick={() => toggle(doc.id)}
                  className={`w-full flex items-center gap-3 sm:gap-4 p-4 transition-all text-left hover:bg-[var(--bg-elevated)] min-w-0
                    ${isSelected ? 'bg-primary-600/10' : ''}`}>
                  <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all shrink-0
                    ${isSelected ? 'bg-primary-600 border-primary-600' : 'border-[var(--border-default)]'}`}>
                    {isSelected && <CheckSquare className="w-3.5 h-3.5 text-white" />}
                  </div>
                  <div className="w-9 h-9 rounded-xl bg-primary-500/10 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-primary-400" />
                  </div>
                  <span className="text-sm text-[var(--text-primary)] font-medium truncate flex-1">{doc.original_filename}</span>
                  <span className="text-xs text-[var(--text-muted)] shrink-0 ml-auto">{doc.file_type.toUpperCase()}</span>
                </button>
              );
            })}
          </div>
        ) : (
          <EmptyState icon={FileText} title="No ready documents"
            description="Upload and process documents first to compare them" />
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-5 animate-slide-up">
          {/* Summary */}
          <div className="glass-card p-6">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-3 flex items-center gap-2">
              <GitCompare className="w-4 h-4 text-primary-400" /> Comparison Summary
            </h3>
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{result.summary}</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Similarities */}
            {result.similarities?.length > 0 && (
              <div className="glass-card p-6 border border-green-500/15">
                <h3 className="text-sm font-semibold text-green-400 mb-4 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" /> Similarities
                </h3>
                <ul className="space-y-3">
                  {result.similarities.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-2 flex-shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Differences */}
            {result.differences?.length > 0 && (
              <div className="glass-card p-6 border border-amber-500/15">
                <h3 className="text-sm font-semibold text-amber-400 mb-4 flex items-center gap-2">
                  <ArrowRight className="w-4 h-4" /> Differences
                </h3>
                <div className="space-y-3">
                  {result.differences.map((d, i) => (
                    <div key={i} className="p-3 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)]">
                      <span className="text-xs font-semibold text-primary-400">{d.category}</span>
                      <p className="text-xs text-[var(--text-secondary)] mt-1 leading-relaxed">{d.detail}</p>
                      {(d.document_a || d.document_b) && (
                        <div className="grid grid-cols-2 gap-2 mt-2">
                          {d.document_a && <div className="text-[11px] text-[var(--text-muted)] p-2 bg-[var(--bg-base)] rounded-lg"><span className="text-indigo-400 font-semibold">Doc A:</span> {d.document_a}</div>}
                          {d.document_b && <div className="text-[11px] text-[var(--text-muted)] p-2 bg-[var(--bg-base)] rounded-lg"><span className="text-purple-400 font-semibold">Doc B:</span> {d.document_b}</div>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
