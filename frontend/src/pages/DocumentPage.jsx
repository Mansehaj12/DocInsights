import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import {
  FileText, MessageSquare, Sparkles, AlertTriangle, Shield,
  BookOpen, ClipboardList, Loader2, ArrowLeft, ArrowUpRight,
  CheckCircle, XCircle, FileDown
} from 'lucide-react';
import {
  getDocument, getDocumentText, getInsights,
  summarizeDocument, extractDocument, detectRisks, generateReport
} from '../services/api';
import { StatusBadge, PageHeader, Skeleton } from '../components/ui';
import { useToast } from '../components/Toast';

const TABS = ['overview', 'text', 'insights'];

export default function DocumentPage() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const [doc, setDoc] = useState(null);
  const [text, setText] = useState('');
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [actionLoading, setActionLoading] = useState('');
  const [activeHighlight, setActiveHighlight] = useState(null);
  const textContainerRef = useRef(null);
  const highlightRef = useRef(null);
  const toast = useToast();

  // Parse highlight from query params
  useEffect(() => {
    const highlightParam = searchParams.get('highlight');
    const tabParam = searchParams.get('tab');
    if (highlightParam) {
      try {
        const parsed = JSON.parse(decodeURIComponent(highlightParam));
        if (parsed && typeof parsed.start_char === 'number' && typeof parsed.end_char === 'number') {
          setActiveHighlight(parsed);
          setActiveTab('text');
        }
      } catch { /* invalid highlight param — ignore silently */ }
    } else if (tabParam) {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  // Scroll to highlight after text renders
  useEffect(() => {
    if (activeHighlight && highlightRef.current && text) {
      // Delay to let DOM render
      const timer = setTimeout(() => {
        highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [activeHighlight, text, activeTab]);

  useEffect(() => { loadDocument(); }, [id]);

  const loadDocument = async () => {
    try {
      const [docData, textData, insightData] = await Promise.all([
        getDocument(id),
        getDocumentText(id).catch(() => ({ text: '' })),
        getInsights(id).catch(() => ({ insights: [] })),
      ]);
      setDoc(docData);
      setText(textData.text || '');
      setInsights(insightData.insights || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (action) => {
    setActionLoading(action);
    try {
      if (action === 'report') {
        await generateReport(id);
        toast.success('Report Generated', 'PDF downloaded successfully');
      } else {
        const fn = { summarize: summarizeDocument, extract: extractDocument, risks: detectRisks }[action];
        await fn(id);
        toast.success('Analysis Complete', `${action} generated successfully`);
        const insightData = await getInsights(id);
        setInsights(insightData.insights || []);
      }
    } catch (err) {
      toast.error('Action Failed', err.response?.data?.detail || 'Something went wrong');
    } finally {
      setActionLoading('');
    }
  };

  if (loading) return <DocumentSkeleton />;
  if (!doc) return <div className="text-center py-20 text-[var(--text-muted)]">Document not found</div>;

  const summaryInsight = insights.find(i => i.insight_type === 'summary');
  const riskInsight = insights.find(i => i.insight_type === 'risk');
  const extractionInsight = insights.find(i => i.insight_type === 'extraction');

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 justify-between">
        <div className="flex items-start sm:items-center gap-4 min-w-0 w-full">
          <Link to="/upload" className="p-2 flex-shrink-0 rounded-lg hover:bg-[var(--bg-elevated)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-[var(--text-primary)] truncate">{doc.original_filename}</h1>
            <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-1.5">
              <span className="text-xs text-[var(--text-muted)]">{(doc.file_size / 1024).toFixed(1)} KB</span>
              <span className="text-xs text-[var(--text-muted)]">{doc.file_type.toUpperCase()}</span>
              {doc.word_count > 0 && <span className="text-xs text-[var(--text-muted)]">{doc.word_count.toLocaleString()} words</span>}
              {doc.page_count > 0 && <span className="text-xs text-[var(--text-muted)]">{doc.page_count} pages</span>}
              <StatusBadge status={doc.status} size="lg" />
            </div>
          </div>
        </div>
        <Link to={`/documents/${id}/chat`} className="btn-primary flex justify-center items-center gap-2 text-sm w-full sm:w-auto shrink-0 mt-2 sm:mt-0">
          <MessageSquare className="w-4 h-4" /> Chat
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-[var(--bg-surface)] rounded-xl border border-[var(--border-subtle)] w-fit">
        {TABS.map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-all duration-200
              ${activeTab === tab ? 'bg-primary-600/20 text-primary-400 shadow-sm' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'}`}>
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 animate-fade-in">
          <ActionCard icon={Sparkles} title="Summarize" desc="Generate an AI-powered executive summary with key highlights"
            action="summarize" loading={actionLoading === 'summarize'} onClick={() => handleAction('summarize')}
            hasData={!!summaryInsight} color="indigo" />
          <ActionCard icon={Shield} title="Risk Analysis" desc="Detect compliance risks, legal issues, and concerning clauses"
            action="risks" loading={actionLoading === 'risks'} onClick={() => handleAction('risks')}
            hasData={!!riskInsight} color="amber" />
          <ActionCard icon={ClipboardList} title="Extract Info" desc="Pull out key facts, dates, parties, and structured data"
            action="extract" loading={actionLoading === 'extract'} onClick={() => handleAction('extract')}
            hasData={!!extractionInsight} color="purple" />
          <ActionCard icon={FileDown} title="Generate Report" desc="Download a comprehensive AI-generated PDF report"
            action="report" loading={actionLoading === 'report'} onClick={() => handleAction('report')}
            hasData={false} color="green" />
        </div>
      )}

      {activeTab === 'text' && (
        <div className="glass-card p-6 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary-400" /> Extracted Text
            </h3>
            {activeHighlight && (
              <button onClick={() => setActiveHighlight(null)}
                className="text-xs text-amber-400 hover:text-amber-300 transition-colors px-3 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/15">
                ✕ Clear Highlight
              </button>
            )}
          </div>
          <div ref={textContainerRef}
            className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap leading-relaxed max-h-[65vh] overflow-y-auto font-mono text-[13px]">
            {text ? (
              <HighlightedText text={text} highlight={activeHighlight} highlightRef={highlightRef} />
            ) : (
              'No text extracted yet.'
            )}
          </div>
        </div>
      )}

      {activeTab === 'insights' && (
        <div className="space-y-5 animate-fade-in">
          {insights.length > 0 ? insights.map((insight, i) => (
            <InsightCard key={i} insight={insight} />
          )) : (
            <div className="glass-card p-12 text-center">
              <Sparkles className="w-10 h-10 text-primary-400/40 mx-auto mb-3" />
              <p className="text-[var(--text-muted)]">No insights generated yet. Use the Overview tab to run AI analysis.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ActionCard({ icon: Icon, title, desc, loading, onClick, hasData, color }) {
  const colorMap = {
    indigo: { bg: 'from-indigo-500/10 to-purple-500/5', border: 'border-indigo-500/20', icon: 'text-indigo-400', btnBg: 'bg-indigo-600 hover:bg-indigo-500' },
    amber: { bg: 'from-amber-500/10 to-orange-500/5', border: 'border-amber-500/20', icon: 'text-amber-400', btnBg: 'bg-amber-600 hover:bg-amber-500' },
    purple: { bg: 'from-purple-500/10 to-pink-500/5', border: 'border-purple-500/20', icon: 'text-purple-400', btnBg: 'bg-purple-600 hover:bg-purple-500' },
    green: { bg: 'from-green-500/10 to-emerald-500/5', border: 'border-green-500/20', icon: 'text-green-400', btnBg: 'bg-green-600 hover:bg-green-500' },
  };
  const c = colorMap[color] || colorMap.indigo;

  return (
    <div className={`rounded-2xl p-6 bg-gradient-to-br ${c.bg} border ${c.border} transition-all hover:scale-[1.02] duration-200`}>
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center ${c.icon}`}>
          <Icon className="w-6 h-6" />
        </div>
        {hasData && <CheckCircle className="w-5 h-5 text-green-400" />}
      </div>
      <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-1">{title}</h3>
      <p className="text-xs text-[var(--text-muted)] mb-5 leading-relaxed">{desc}</p>
      <button onClick={onClick} disabled={loading}
        className={`w-full py-2.5 rounded-xl text-sm font-semibold text-white transition-all shadow-lg ${c.btnBg} disabled:opacity-50`}>
        {loading ? (
          <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Analyzing...</span>
        ) : hasData ? 'Regenerate' : 'Run Analysis'}
      </button>
    </div>
  );
}

function InsightCard({ insight }) {
  const [expanded, setExpanded] = useState(true);
  let data = {};
  try { data = typeof insight.content_json === 'string' ? JSON.parse(insight.content_json) : insight.content_json; } catch { data = {}; }

  const typeConfig = {
    summary: { icon: Sparkles, label: 'Summary', color: 'text-indigo-400', border: 'border-indigo-500/20' },
    risk: { icon: Shield, label: 'Risk Analysis', color: 'text-amber-400', border: 'border-amber-500/20' },
    extraction: { icon: ClipboardList, label: 'Extraction', color: 'text-purple-400', border: 'border-purple-500/20' },
  };
  const cfg = typeConfig[insight.insight_type] || typeConfig.summary;
  const Icon = cfg.icon;

  return (
    <div className={`glass-card overflow-hidden border ${cfg.border}`}>
      <button onClick={() => setExpanded(!expanded)}
        className="w-full p-5 flex items-center justify-between hover:bg-[var(--bg-elevated)] transition-colors">
        <div className="flex items-center gap-3">
          <Icon className={`w-5 h-5 ${cfg.color}`} />
          <span className="text-sm font-semibold text-[var(--text-primary)]">{cfg.label}</span>
        </div>
        <ArrowUpRight className={`w-4 h-4 text-[var(--text-muted)] transition-transform ${expanded ? 'rotate-90' : ''}`} />
      </button>
      {expanded && (
        <div className="px-5 pb-5 animate-fade-in">
          {insight.insight_type === 'summary' && <SummaryContent data={data} />}
          {insight.insight_type === 'risk' && <RiskContent data={data} />}
          {insight.insight_type === 'extraction' && <ExtractionContent data={data} />}
        </div>
      )}
    </div>
  );
}

function SummaryContent({ data }) {
  return (
    <div className="space-y-5">
      {data.executive_summary && (
        <div>
          <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Executive Summary</h4>
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{data.executive_summary}</p>
        </div>
      )}
      {data.bullet_highlights?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Key Highlights</h4>
          <ul className="space-y-2">
            {data.bullet_highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
                <span className="w-1.5 h-1.5 rounded-full bg-primary-400 mt-2 flex-shrink-0" />
                {h}
              </li>
            ))}
          </ul>
        </div>
      )}
      {data.key_takeaways?.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2">Key Takeaways</h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {data.key_takeaways.map((t, i) => (
              <div key={i} className="p-3 rounded-xl bg-[var(--bg-elevated)] text-sm text-[var(--text-secondary)]">{t}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RiskContent({ data }) {
  const severityColor = { Low: 'text-green-400 bg-green-500/10', Medium: 'text-amber-400 bg-amber-500/10', High: 'text-red-400 bg-red-500/10' };
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-xs text-[var(--text-muted)]">Overall Risk:</span>
        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${severityColor[data.overall_risk_score] || 'text-gray-400 bg-gray-500/10'}`}>
          {data.overall_risk_score || 'N/A'}
        </span>
        <span className="text-xs text-[var(--text-muted)]">{data.total_risks || 0} risks found</span>
      </div>
      {data.risk_items?.map((risk, i) => (
        <div key={i} className="p-4 rounded-xl bg-[var(--bg-elevated)] border border-[var(--border-subtle)] space-y-2">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${severityColor[risk.severity] || ''}`}>{risk.severity}</span>
            <span className="text-xs text-primary-400 font-medium">{risk.risk_type}</span>
          </div>
          <p className="text-sm text-[var(--text-secondary)]">{risk.description}</p>
          {risk.highlighted_text && (
            <p className="text-xs text-[var(--text-muted)] italic border-l-2 border-amber-500/30 pl-3">"{risk.highlighted_text}"</p>
          )}
          {risk.recommendation && (
            <p className="text-xs text-green-400/80 flex items-start gap-1.5">
              <CheckCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" /> {risk.recommendation}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function ExtractionContent({ data }) {
  return (
    <div className="space-y-3">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="p-3 rounded-xl bg-[var(--bg-elevated)]">
          <span className="text-xs text-primary-400 font-semibold uppercase tracking-wider">{key.replace(/_/g, ' ')}</span>
          <div className="mt-1.5 text-sm text-[var(--text-secondary)]">
            {Array.isArray(value) ? (
              <ul className="space-y-1">
                {value.map((v, i) => <li key={i} className="flex items-start gap-2"><span className="w-1 h-1 rounded-full bg-[var(--text-muted)] mt-2" />{typeof v === 'object' ? JSON.stringify(v) : v}</li>)}
              </ul>
            ) : typeof value === 'object' ? (
              <pre className="text-xs font-mono">{JSON.stringify(value, null, 2)}</pre>
            ) : <p>{value}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Renders document text with an optional highlighted range.
 * Splits text into before/highlighted/after segments.
 * Handles edge cases gracefully — falls back to plain text.
 */
function HighlightedText({ text, highlight, highlightRef }) {
  if (!highlight || highlight.start_char == null || highlight.end_char == null) {
    return <>{text}</>;
  }

  const { start_char, end_char } = highlight;

  // Validate indices
  if (start_char < 0 || end_char <= start_char || start_char >= text.length) {
    return <>{text}</>;
  }

  const safeEnd = Math.min(end_char, text.length);
  const before = text.slice(0, start_char);
  const highlighted = text.slice(start_char, safeEnd);
  const after = text.slice(safeEnd);

  return (
    <>
      {before}
      <mark
        ref={highlightRef}
        className="bg-amber-400/20 text-amber-200 px-0.5 rounded-sm ring-2 ring-amber-400/30 ring-offset-1 ring-offset-transparent"
        style={{ scrollMarginTop: '120px' }}
      >
        {highlighted}
      </mark>
      {after}
    </>
  );
}


function DocumentSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="w-10 h-10" />
        <div><Skeleton className="h-7 w-64 mb-2" /><Skeleton className="h-4 w-48" /></div>
      </div>
      <Skeleton className="h-10 w-72" />
      <div className="grid grid-cols-3 gap-5">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-56" rounded="rounded-2xl" />)}
      </div>
    </div>
  );
}
