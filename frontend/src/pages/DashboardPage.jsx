import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, AlertTriangle, BarChart3, Clock, TrendingUp,
  Shield, Upload, Activity, Sparkles, ArrowUpRight
} from 'lucide-react';
import {
  AreaChart, Area, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import { getDashboardStats, getRiskOverview } from '../services/api';
import { AnimatedCounter, StatusBadge, Skeleton, PageHeader, EmptyState } from '../components/ui';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#22c55e', '#f59e0b', '#ef4444'];
const RISK_COLORS = { Low: '#22c55e', Medium: '#f59e0b', High: '#ef4444' };

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [risks, setRisks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [statsData, riskData] = await Promise.all([
        getDashboardStats(),
        getRiskOverview().catch(() => ({ risks: [] })),
      ]);
      setStats(statsData);
      setRisks(riskData.risks || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <DashboardSkeleton />;

  const typeData = stats ? Object.entries(stats.documents_by_type).map(([name, value]) => ({ name: name.toUpperCase(), value })) : [];
  const riskData = stats ? Object.entries(stats.risk_distribution).map(([name, value]) => ({ name, value })) : [];
  const statusData = stats ? Object.entries(stats.documents_by_status).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="space-y-8 animate-fade-in">
      <PageHeader
        title="Dashboard"
        subtitle="Real-time overview of your document intelligence pipeline"
        actions={
          <Link to="/upload" className="btn-primary flex items-center gap-2 text-sm">
            <Upload className="w-4 h-4" /> Upload Document
          </Link>
        }
      />

      {/* Stat Cards — Animated Counters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard icon={FileText} label="Total Documents" value={stats?.total_documents || 0}
          gradient="from-indigo-500/15 to-purple-500/10" iconColor="text-indigo-400" borderColor="border-indigo-500/20" delay={0} />
        <StatCard icon={AlertTriangle} label="Total Risks" value={stats?.total_risks || 0}
          gradient="from-amber-500/15 to-orange-500/10" iconColor="text-amber-400" borderColor="border-amber-500/20" delay={1} />
        <StatCard icon={Shield} label="High Severity" value={stats?.risk_distribution?.High || 0}
          gradient="from-red-500/15 to-pink-500/10" iconColor="text-red-400" borderColor="border-red-500/20" delay={2} />
        <StatCard icon={TrendingUp} label="Processed" value={stats?.documents_by_status?.ready || 0}
          gradient="from-green-500/15 to-emerald-500/10" iconColor="text-green-400" borderColor="border-green-500/20" delay={3} />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document Types — Donut */}
        <div className="glass-card p-6 animate-slide-up delay-1">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-indigo-400" /> Document Types
            </h3>
            <span className="text-xs text-[var(--text-muted)]">{typeData.reduce((s, d) => s + d.value, 0)} total</span>
          </div>
          {typeData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={typeData} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
                    paddingAngle={4} dataKey="value" stroke="none">
                    {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '10px', color: 'var(--text-primary)', fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex flex-wrap gap-3 mt-3 justify-center">
                {typeData.map((d, i) => (
                  <span key={d.name} className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
                    <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    {d.name} ({d.value})
                  </span>
                ))}
              </div>
            </>
          ) : <EmptyState icon={BarChart3} title="No documents" description="Upload your first document to see analytics" />}
        </div>

        {/* Risk Distribution — Gradient Bars */}
        <div className="glass-card p-6 animate-slide-up delay-2">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Risk Distribution
            </h3>
          </div>
          {riskData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={riskData} barCategoryGap="25%">
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '10px', color: 'var(--text-primary)', fontSize: 12 }} />
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {riskData.map((entry) => <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#6366f1'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyState icon={Shield} title="No risks detected" description="Run risk analysis on your documents" />}
        </div>

        {/* Processing Status — Visual bars */}
        <div className="glass-card p-6 animate-slide-up delay-3">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-sm font-semibold text-[var(--text-secondary)] flex items-center gap-2">
              <Activity className="w-4 h-4 text-green-400" /> Pipeline Status
            </h3>
          </div>
          {statusData.length > 0 ? (
            <div className="space-y-4 mt-2">
              {statusData.map(({ name, value }) => {
                const total = statusData.reduce((s, d) => s + d.value, 0);
                const pct = total > 0 ? Math.round((value / total) * 100) : 0;
                return (
                  <div key={name} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={name} />
                      </div>
                      <span className="text-sm font-bold text-[var(--text-primary)]">{value}</span>
                    </div>
                    <div className="w-full h-1.5 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-1000 ease-out ${
                        name === 'ready' ? 'bg-green-500' : name === 'processing' ? 'bg-amber-500' : name === 'failed' ? 'bg-red-500' : 'bg-blue-500'
                      }`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : <EmptyState icon={Clock} title="No data" description="Process documents to see status" />}
        </div>
      </div>

      {/* Recent Documents — Enhanced */}
      <div className="glass-card overflow-hidden animate-slide-up delay-4">
        <div className="p-5 border-b border-[var(--border-subtle)] flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-secondary)] flex items-center gap-2">
            <Clock className="w-4 h-4 text-primary-400" /> Recent Documents
          </h3>
          <Link to="/upload" className="text-xs text-primary-400 hover:text-primary-300 transition-colors flex items-center gap-1">
            View all <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
        {stats?.recent_documents?.length > 0 ? (
          <div className="divide-y divide-[var(--border-subtle)]">
            {stats.recent_documents.map((doc, i) => (
              <Link key={doc.id} to={`/documents/${doc.id}`}
                className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-[var(--bg-elevated)] transition-all group animate-slide-up delay-${Math.min(i + 1, 5)} gap-3 sm:gap-0`}>
                <div className="flex items-start sm:items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/20 to-purple-500/10 flex items-center justify-center border border-primary-500/10 shrink-0">
                    <FileText className="w-5 h-5 text-primary-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] group-hover:text-primary-400 transition-colors truncate">{doc.original_filename}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">{(doc.file_size / 1024).toFixed(1)} KB • {doc.file_type.toUpperCase()}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto border-t sm:border-t-0 border-[var(--border-subtle)] pt-3 sm:pt-0 mt-1 sm:mt-0">
                  <StatusBadge status={doc.status} />
                  <ArrowUpRight className="w-4 h-4 text-[var(--text-muted)] group-hover:text-primary-400 transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState icon={FileText} title="No documents yet"
            description="Upload your first document to get started with AI-powered insights"
            action={<Link to="/upload" className="btn-primary text-sm flex items-center gap-2"><Upload className="w-4 h-4" /> Upload</Link>}
          />
        )}
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, gradient, iconColor, borderColor, delay }) {
  return (
    <div className={`rounded-2xl p-5 bg-gradient-to-br ${gradient} border ${borderColor}
      animate-slide-up delay-${delay + 1} hover:scale-[1.02] transition-transform duration-200`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] text-[var(--text-muted)] font-semibold uppercase tracking-wider">{label}</p>
          <p className="text-3xl font-bold text-[var(--text-primary)] mt-2">
            <AnimatedCounter value={value} />
          </p>
        </div>
        <div className={`w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center ${iconColor}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div><Skeleton className="h-9 w-48 mb-2" /><Skeleton className="h-4 w-72" /></div>
        <Skeleton className="h-10 w-40" />
      </div>
      <div className="grid grid-cols-4 gap-5">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" rounded="rounded-2xl" />)}
      </div>
      <div className="grid grid-cols-3 gap-6">
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-72" rounded="rounded-2xl" />)}
      </div>
      <Skeleton className="h-64" rounded="rounded-2xl" />
    </div>
  );
}
