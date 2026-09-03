import { useState, useEffect, useRef } from 'react';

/**
 * Animated counter — smoothly counts up from 0 to target value.
 */
export function AnimatedCounter({ value, duration = 1200, prefix = '', suffix = '' }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    const target = typeof value === 'number' ? value : parseInt(value) || 0;
    if (target === 0) { setDisplay(0); return; }

    let start = 0;
    const startTime = Date.now();

    const step = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * target);
      setDisplay(current);
      if (progress < 1) ref.current = requestAnimationFrame(step);
    };

    ref.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(ref.current);
  }, [value, duration]);

  return <span>{prefix}{display.toLocaleString()}{suffix}</span>;
}

/**
 * Status badge with color-coded pill + optional pulse.
 */
export function StatusBadge({ status, size = 'sm' }) {
  const config = {
    ready: { bg: 'bg-green-500/15', text: 'text-green-400', dot: 'bg-green-400', label: 'Ready' },
    processing: { bg: 'bg-amber-500/15', text: 'text-amber-400', dot: 'bg-amber-400', label: 'Processing', pulse: true },
    embedding: { bg: 'bg-purple-500/15', text: 'text-purple-400', dot: 'bg-purple-400', label: 'Embedding', pulse: true },
    chunking: { bg: 'bg-blue-500/15', text: 'text-blue-400', dot: 'bg-blue-400', label: 'Chunking', pulse: true },
    uploaded: { bg: 'bg-blue-500/15', text: 'text-blue-400', dot: 'bg-blue-400', label: 'Uploaded' },
    failed: { bg: 'bg-red-500/15', text: 'text-red-400', dot: 'bg-red-400', label: 'Failed' },
  };
  const c = config[status] || config.uploaded;
  const sizeClass = size === 'lg' ? 'px-3 py-1.5 text-xs' : 'px-2 py-1 text-[10px]';

  return (
    <span className={`inline-flex items-center gap-1.5 ${sizeClass} rounded-full font-semibold uppercase tracking-wider ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${c.pulse ? 'animate-pulse' : ''}`} />
      {c.label}
    </span>
  );
}

/**
 * Skeleton placeholder with shimmer.
 */
export function Skeleton({ className = '', rounded = 'rounded-xl' }) {
  return <div className={`skeleton ${rounded} ${className}`} />;
}

/**
 * Empty state with icon and message.
 */
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in">
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-primary-600/10 flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-primary-400/60" />
        </div>
      )}
      {title && <h3 className="text-lg font-semibold text-gray-300 mb-1">{title}</h3>}
      {description && <p className="text-sm text-gray-500 max-w-md">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

/**
 * Page header component.
 */
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8 animate-fade-in">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold gradient-text">{title}</h1>
        {subtitle && <p className="text-gray-400 mt-1.5 text-xs sm:text-sm">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-3 w-full sm:w-auto">{actions}</div>}
    </div>
  );
}
