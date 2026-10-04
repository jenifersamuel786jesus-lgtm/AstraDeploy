import { useEffect } from 'react';
import { Check, Info, LoaderCircle, TriangleAlert, X } from 'lucide-react';

export type ToastMessage = { title: string; description?: string; tone: 'success' | 'error' | 'info' };

export function AstraMark({ small = false }: { small?: boolean }) {
  return <span className={`astra-mark ${small ? 'astra-mark-small' : ''}`} aria-hidden="true"><svg viewBox="0 0 38 38" fill="none"><path d="M7 29.5 18.7 7.6a1.3 1.3 0 0 1 2.3 0l10.9 20.6" stroke="currentColor" strokeWidth="3.1" strokeLinecap="round"/><path d="M12.2 20.2h13.2" stroke="currentColor" strokeWidth="3.1" strokeLinecap="round"/><circle cx="25.8" cy="20.2" r="3.1" fill="#32D6B0" stroke="#101D2D" strokeWidth="1.2"/><path d="M28.2 25.8 32 29.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"/></svg></span>;
}

export function LoadingState({ full = false }: { full?: boolean }) {
  return <div className={`loading-state ${full ? 'loading-full' : ''}`}><div className="spinner" /><span>Preparing your workspace…</span></div>;
}

export function Toast({ message, onClose }: { message: ToastMessage; onClose: () => void }) {
  useEffect(() => { const timer = window.setTimeout(onClose, 4200); return () => window.clearTimeout(timer); }, [onClose]);
  const Icon = message.tone === 'success' ? Check : message.tone === 'error' ? TriangleAlert : Info;
  return <div className={`toast toast-${message.tone}`} role="status"><span className="toast-icon"><Icon size={17} /></span><span><b>{message.title}</b>{message.description && <small>{message.description}</small>}</span><button aria-label="Dismiss notification" onClick={onClose}><X size={15} /></button></div>;
}

export function PageHeader({ eyebrow, title, subtitle, actions }: { eyebrow?: string; title: string; subtitle?: string; actions?: React.ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow || 'ASTRADEPLOY WORKSPACE'}</div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{actions && <div className="page-actions">{actions}</div>}</div>;
}

export function StatusBadge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'demo' }) {
  return <span className={`status-badge status-${tone}`}><i />{children}</span>;
}

export function SectionHeading({ title, detail, action }: { title: string; detail?: string; action?: React.ReactNode }) {
  return <div className="section-heading"><div><h2>{title}</h2>{detail && <p>{detail}</p>}</div>{action}</div>;
}

export function IntegrationNotice({ title = 'Integration not connected', detail = 'This view uses clearly labeled sample data. Connect a provider to read actual cloud activity.' }: { title?: string; detail?: string }) {
  return <div className="integration-notice"><span className="notice-icon"><Info size={16} /></span><span><b>{title}</b><small>{detail}</small></span></div>;
}

export function InlineSpinner() { return <LoaderCircle size={17} className="spin" aria-label="Loading" />; }
