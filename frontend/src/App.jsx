import { useState } from 'react';
import { Routes, Route, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Upload, MessageSquare, Search,
  GitCompare, FileText, Zap, ChevronLeft, ChevronRight, Sun, Moon, Menu, X,
  MessagesSquare
} from 'lucide-react';
import { ToastProvider } from './components/Toast';
import ApiKeySettings from './components/ApiKeySettings';

import UploadPage from './pages/UploadPage';
import DocumentPage from './pages/DocumentPage';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import ComparePage from './pages/ComparePage';
import MultiChatPage from './pages/MultiChatPage';
import SearchPage from './pages/SearchPage';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Documents' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/compare', icon: GitCompare, label: 'Compare' },
  { to: '/chat/multi', icon: MessagesSquare, label: 'Multi-Chat' },
];

function Sidebar({ collapsed, onToggle, mobileOpen, setMobileOpen }) {
  const location = useLocation();
  const [theme, setTheme] = useState('dark');

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`sidebar fixed left-0 top-0 h-screen bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] flex flex-col z-50 overflow-hidden transition-all duration-300
        ${collapsed ? 'md:w-[72px]' : 'md:w-[260px]'}
        ${mobileOpen ? 'translate-x-0 w-[260px]' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Logo */}
        <div className="p-5 border-b border-[var(--border-subtle)] flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center glow-accent flex-shrink-0">
              <Zap className="w-5 h-5 text-white" />
            </div>
            {(!collapsed || mobileOpen) && (
              <div className="animate-fade-in">
                <h1 className="text-lg font-bold gradient-text whitespace-nowrap">DocInsights</h1>
                <p className="text-[10px] text-[var(--text-muted)] tracking-widest uppercase">AI Platform</p>
              </div>
            )}
          </div>
          {/* Mobile Close Button */}
          <button
            className="md:hidden p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            onClick={() => setMobileOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => {
            const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to);
            return (
              <NavLink key={to} to={to} title={collapsed && !mobileOpen ? label : undefined}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
                ${isActive
                  ? 'bg-primary-600/20 text-primary-400 shadow-lg shadow-primary-500/10 border-glow'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]'
                }`}
                onClick={() => setMobileOpen(false)} // Close mobile menu on navigate
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {(!collapsed || mobileOpen) && <span className="whitespace-nowrap">{label}</span>}
              </NavLink>
            );
          })}
        </nav>

        {/* Footer controls */}
        <div className="p-3 space-y-2 border-t border-[var(--border-subtle)]">
          {/* Bring-your-own-key (in-memory, per-session) */}
          <ApiKeySettings collapsed={collapsed} mobileOpen={mobileOpen} />

          {/* Theme toggle */}
          <button onClick={toggleTheme}
            className={`flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-all`}>
            {theme === 'dark' ? <Sun className="w-5 h-5 flex-shrink-0" /> : <Moon className="w-5 h-5 flex-shrink-0" />}
            {(!collapsed || mobileOpen) && <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>

          {/* Collapse toggle (Desktop Only) */}
          <button onClick={onToggle}
            className="hidden md:flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] transition-all">
            {collapsed ? <ChevronRight className="w-5 h-5 flex-shrink-0" /> : <ChevronLeft className="w-5 h-5 flex-shrink-0" />}
            {!collapsed && <span>Collapse</span>}
          </button>

          {(!collapsed || mobileOpen) && (
            <div className="px-3 py-3 rounded-xl bg-gradient-to-r from-primary-900/40 to-purple-900/40 border border-primary-800/30 animate-fade-in hidden md:block">
              <p className="text-xs text-primary-300 font-medium">v2.0 — AI-Powered</p>
              <p className="text-[10px] text-[var(--text-muted)] mt-0.5">RAG • Semantic Search • Insights</p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <ToastProvider>
      <div className="flex min-h-screen bg-[var(--bg-base)]">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          mobileOpen={mobileOpen}
          setMobileOpen={setMobileOpen}
        />
        
        <main className={`flex-1 transition-all duration-[400ms] ease-in-out flex flex-col min-h-screen
          ml-0 md:ml-[72px] lg:ml-[260px] ${sidebarCollapsed ? 'lg:ml-[72px]' : ''}`}>
          
          {/* Mobile Header */}
          <div className="md:hidden flex items-center justify-between p-4 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] sticky top-0 z-30">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center glow-accent">
                <Zap className="w-4 h-4 text-white" />
              </div>
              <h1 className="text-base font-bold gradient-text">DocInsights</h1>
            </div>
            <button
              onClick={() => setMobileOpen(true)}
              className="p-2 -mr-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>

          {/* Page Content */}
          <div className="flex-1 p-4 sm:p-6 lg:p-8">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/documents/:id" element={<DocumentPage />} />
              <Route path="/documents/:id/chat" element={<ChatPage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/chat/multi" element={<MultiChatPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </ToastProvider>
  );
}
