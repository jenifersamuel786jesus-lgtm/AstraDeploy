import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, BarChart3, Bell, Boxes, BrainCircuit, ChevronDown, CircleHelp,
  Cloud, DollarSign, FileText, Gauge, GitBranch, LayoutDashboard, LogOut, Menu, Package,
  Search, Settings, ShieldCheck, Sparkles, Users, Workflow, X,
} from 'lucide-react';
import { api, type AuditEvent, type DashboardData, type RecordItem, type SessionInfo, type SettingsData, type TeamMember, type Workload } from './api';
import { AstraMark, LoadingState, Toast, type ToastMessage } from './components/ui';

const OverviewPage = lazy(() => import('./pages/Overview').then(module => ({ default: module.OverviewPage })));
const AdvisorPage = lazy(() => import('./pages/Advisor').then(module => ({ default: module.AdvisorPage })));
const WorkloadsPage = lazy(() => import('./pages/Workloads').then(module => ({ default: module.WorkloadsPage })));
const OperationsPage = lazy(() => import('./pages/Operations').then(module => ({ default: module.OperationsPage })));

const navigation = [
  { path: '/', label: 'Overview', icon: LayoutDashboard, group: 'Workspace' },
  { path: '/advisor', label: 'AI Resource Advisor', icon: BrainCircuit, group: 'Workspace' },
  { path: '/workloads', label: 'Workload Analysis', icon: Activity, group: 'Workspace' },
  { path: '/optimizer', label: 'Cloud Resource Optimizer', icon: Gauge, group: 'Operate' },
  { path: '/deployments', label: 'Deployment Center', icon: Cloud, group: 'Operate' },
  { path: '/pipelines', label: 'ML Pipeline', icon: Workflow, group: 'Operate' },
  { path: '/models', label: 'Model Registry', icon: Package, group: 'Operate' },
  { path: '/experiments', label: 'Experiment Tracking', icon: GitBranch, group: 'Operate' },
  { path: '/monitoring', label: 'Resource Monitoring', icon: BarChart3, group: 'Insights' },
  { path: '/cost', label: 'Cost Intelligence', icon: DollarSign, group: 'Insights' },
  { path: '/infrastructure', label: 'Infrastructure', icon: Boxes, group: 'Insights' },
  { path: '/alerts', label: 'Alerts & Notifications', icon: Bell, group: 'Insights' },
  { path: '/reports', label: 'Reports', icon: FileText, group: 'Insights' },
  { path: '/team', label: 'Team & Access', icon: Users, group: 'Manage' },
  { path: '/settings', label: 'Settings', icon: Settings, group: 'Manage' },
] as const;

const collections = ['pipelines', 'models', 'experiments', 'deployments', 'alerts', 'budgets', 'costs', 'optimizations', 'infrastructure', 'metrics', 'activity', 'integrations', 'provisioning', 'reports', 'scaling'] as const;
type Collection = (typeof collections)[number];
type WorkspaceData = { dashboard?: DashboardData; workloads: Workload[]; records: Partial<Record<Collection, RecordItem[]>>; team: TeamMember[]; settings?: SettingsData; audit: AuditEvent[] };

type OAuthCompletion = { code: string; state: string; redirect_uri: string };
const oauthCompletions = new Map<string, Promise<void>>();

function completeOAuthOnce(payload: OAuthCompletion): Promise<void> {
  const existing = oauthCompletions.get(payload.state);
  if (existing) return existing;
  const pending = fetch('/api/v1/auth/complete', {
    method: 'POST', credentials: 'same-origin', referrerPolicy: 'same-origin',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  }).then(async response => {
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || 'Could not complete sign-in.');
    }
    await response.json();
  });
  oauthCompletions.set(payload.state, pending);
  const forget = () => { if (oauthCompletions.get(payload.state) === pending) oauthCompletions.delete(payload.state); };
  void pending.then(forget, forget);
  return pending;
}

export default function App() {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authMessage, setAuthMessage] = useState('');
  const [authRefresh, setAuthRefresh] = useState(0);
  const completeSignIn = useCallback(() => setAuthRefresh(v => v + 1), []);

  useEffect(() => {
    api.me().then(setSession).catch((error: Error & { status?: number }) => { if (error.status !== 401) setAuthMessage(error.message); }).finally(() => setAuthLoading(false));
  }, [authRefresh]);

  return <Suspense fallback={<LoadingState full />}><Routes>
    <Route path="/auth/callback" element={<OAuthCallback onComplete={completeSignIn} />} />
    <Route path="*" element={authLoading ? <LoadingState full /> : session ? <AppWorkspace session={session} onSessionEnd={() => { setSession(null); setAuthMessage('You have signed out.'); }} /> : <SignIn message={authMessage} />} />
  </Routes></Suspense>;
}

function SignIn({ message }: { message: string }) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const signIn = async () => {
    setWorking(true);
    setError('');
    const callback = `${window.location.origin}/auth/callback`;
    try {
      const response = await api.startOAuth(callback);
      if (!response.authorization_url) throw new Error('Identity service did not return a sign-in URL.');
      window.location.assign(response.authorization_url);
    } catch (reason) {
      setWorking(false);
      setError(reason instanceof Error ? reason.message : 'Could not start secure sign-in. Please try again.');
    }
  };
  return <div className="auth-screen">
    <div className="auth-glow auth-glow-a" /><div className="auth-glow auth-glow-b" />
    <div className="auth-card">
      <div className="auth-brand"><AstraMark /><div><strong>AstraDeploy</strong><span>RESOURCE INTELLIGENCE</span></div></div>
      <div className="auth-kicker"><span className="status-dot" /> WORKLOAD-AWARE CLOUD OPERATIONS</div>
      <h1>Provision with<br /><em>context.</em></h1>
      <p className="auth-copy">Make infrastructure decisions from the workload outward. Compare transparent resource plans, validate budgets and keep every operation traceable.</p>
      <div className="auth-feature-list"><div><BrainCircuit size={16} /><span>Explainable resource recommendations</span></div><div><ShieldCheck size={16} /><span>Policy-aware by design</span></div><div><Activity size={16} /><span>Demo data is labeled, never passed off as live</span></div></div>
      {(error || message) && <div className="auth-error"><AlertTriangle size={16} />{error || message}</div>}
      <button className="button button-primary button-wide" onClick={signIn} disabled={working}>{working ? 'Opening secure sign-in…' : 'Continue with Manus'}<span>→</span></button>
      <p className="auth-legal">Secure identity · Organization-scoped access · No cloud credentials required for demo mode</p>
    </div>
    <div className="auth-footer"><span>ASTRADEPLOY / INTELLIGENCE LAYER</span><span>DEMO MODE · 0 PROVIDERS CONNECTED</span></div>
  </div>;
}

function OAuthCallback({ onComplete }: { onComplete: () => void }) {
  const [message, setMessage] = useState('Verifying your identity…');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams(window.location.search);
    const code = query.get('code');
    const state = query.get('state');
    const providerError = query.get('error');
    if (providerError || !code || !state) {
      setError(providerError || 'The sign-in response is incomplete. Please start again.');
      return;
    }
    const redirect_uri = `${window.location.origin}/auth/callback`;
    api.me().then(() => { if (active) navigate('/', { replace: true }); }).catch(() => {
      completeOAuthOnce({ code, state, redirect_uri })
        .then(() => { if (active) { setMessage('Sign-in complete. Loading your workspace…'); onComplete(); navigate('/', { replace: true }); } })
        .catch((reason: Error) => { if (active) setError(reason.message); });
    });
    return () => { active = false; };
  }, [navigate, onComplete]);
  return <div className="callback-screen"><AstraMark /><div className="callback-card"><div className="spinner" />{error ? <><h2>Sign-in needs another try</h2><p>{error}</p><Link className="button button-secondary" to="/">Return to sign in</Link></> : <><h2>Secure identity check</h2><p>{message}</p></>}</div></div>;
}

function AppWorkspace({ session, onSessionEnd }: { session: SessionInfo; onSessionEnd: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState<WorkspaceData>({ workloads: [], records: {}, team: [], audit: [] });
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [syncState, setSyncState] = useState<'connecting' | 'ok' | 'error'>('connecting');
  const [streamState, setStreamState] = useState<'connecting' | 'live' | 'reconnecting'>('connecting');
  const latestWorkspaceRevision = useRef(0);
  const [lastSynced, setLastSynced] = useState<Date | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const current = navigation.find(item => item.path === location.pathname) || navigation[0];

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setBusy(true);
    try {
      const snapshot = await api.workspace();
      if (snapshot.revision >= latestWorkspaceRevision.current) {
        latestWorkspaceRevision.current = snapshot.revision;
        setData({ dashboard: snapshot.dashboard, workloads: snapshot.workloads.items, records: snapshot.records as WorkspaceData['records'], team: snapshot.team.items, settings: snapshot.settings, audit: snapshot.audit.items });
        setLastSynced(new Date());
      }
      setSyncState('ok');
      setError('');
    } catch (reason) {
      const text = reason instanceof Error ? reason.message : 'Unable to load workspace data.';
      setError(text);
      setSyncState('error');
      if ((reason as { status?: number }).status === 401) onSessionEnd();
    } finally { if (!quiet) setBusy(false); }
  }, [onSessionEnd]);

  useEffect(() => {
    let active = true;
    void refresh();
    const source = api.workspaceEvents();
    source.onopen = () => { if (active) setStreamState('live'); };
    source.onmessage = event => {
      if (!active) return;
      try {
        const payload = JSON.parse(event.data) as { type?: string };
        if (payload.type === 'workspace.updated') {
          setStreamState('live');
          void refresh(true);
        }
      } catch { /* Ignore malformed notices and retain the last good snapshot. */ }
    };
    source.onerror = () => { if (active) setStreamState('reconnecting'); };
    const timer = window.setInterval(() => { if (active) void refresh(true); }, 60_000);
    return () => { active = false; source.close(); window.clearInterval(timer); };
  }, [refresh]);
  useEffect(() => { setMobileOpen(false); window.scrollTo({ top: 0, behavior: 'smooth' }); }, [location.pathname]);
  const notify = useCallback((title: string, tone: ToastMessage['tone'] = 'success') => setToast({ title, tone }), []);
  const doLogout = async () => { try { await fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'same-origin' }); } finally { onSessionEnd(); } };
  const results = useMemo(() => query.trim() ? data.workloads.filter(w => `${w.name} ${w.task_type} ${w.framework}`.toLowerCase().includes(query.toLowerCase())).slice(0, 5) : [], [query, data.workloads]);
  const shared = { data, busy, error, refresh, notify, session };

  return <div className="app-layout">
    {mobileOpen && <button className="mobile-backdrop" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <Link to="/" className="brand-lockup" aria-label="AstraDeploy overview"><AstraMark /><span><b>AstraDeploy</b><small>ML RESOURCE OPS</small></span></Link>
      <div className="workspace-switch"><div className="workspace-symbol">{(data.settings?.organization?.name || 'A')[0].toUpperCase()}</div><div className="workspace-info"><b>{data.settings?.organization?.name || 'Loading workspace'}</b><span>Organization</span></div><ChevronDown size={15} /></div>
      <div className="nav-list">
        {(['Workspace', 'Operate', 'Insights', 'Manage'] as const).map(group => <div key={group} className="nav-group"><span className="nav-caption">{group}</span>{navigation.filter(item => item.group === group).map(item => {
          const Icon = item.icon;
          const active = location.pathname === item.path;
          return <Link key={item.path} to={item.path} className={`nav-item ${active ? 'active' : ''}`}><Icon size={17} strokeWidth={active ? 2.15 : 1.75} /><span>{item.label}</span>{item.path === '/alerts' && (data.dashboard?.summary.open_alerts || 0) > 0 && <i className="nav-count">{data.dashboard?.summary.open_alerts}</i>}</Link>;
        })}</div>)}
      </div>
      <div className="sidebar-bottom"><div className="plan-card"><div className="plan-head"><span className="plan-spark"><Sparkles size={14} /></span><b>Context engine</b><span className="pill-live">DEMO</span></div><p>Rule-based recommendations are active. Connect history to unlock forecasting.</p><Link to="/settings">View integrations <span>↗</span></Link></div><button className="help-link" onClick={() => navigate('/reports')}><CircleHelp size={16} /><span>Help & reports</span><span className="help-key">?</span></button></div>
      <div className="sidebar-footer"><span className={`sidebar-status sidebar-status-${streamState}`}><i />{streamState === 'live' ? 'Live app updates connected' : streamState === 'reconnecting' ? 'Reconnecting live updates' : 'Connecting live updates'}</span><span className="version-label">APP DATA · EVENT STREAM</span></div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="topbar-left"><button className="mobile-menu" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu size={20} /></button><div className="breadcrumbs"><span>Workspace</span><i>/</i><b>{current.label}</b></div></div>
        <div className="topbar-actions">
          <div className={`global-search ${searchOpen ? 'search-open' : ''}`}><Search size={16} /><input aria-label="Search workloads" placeholder="Search workloads…" value={query} onFocus={() => setSearchOpen(true)} onChange={e => { setQuery(e.target.value); setSearchOpen(true); }} onKeyDown={e => { if (e.key === 'Escape') { setSearchOpen(false); setQuery(''); } }} /><kbd>⌘ K</kbd>{searchOpen && query && <button className="icon-button search-clear" aria-label="Clear search" onClick={() => { setQuery(''); setSearchOpen(false); }}><X size={14} /></button>}
            {searchOpen && query && <div className="search-popover">{results.length ? results.map(item => <button key={item.id} onClick={() => { navigate('/workloads'); setQuery(''); setSearchOpen(false); }}><span className="search-item-icon"><Activity size={15} /></span><span><b>{item.name}</b><small>{item.task_type} · {item.framework}</small></span><span className="search-arrow">↗</span></button>) : <div className="search-empty">No matching workloads</div>}</div>}
          </div>
          <button className="environment-select" type="button" aria-label="Demo environment; open integration settings" title="No live cloud environment is connected. Open integration status." onClick={() => navigate('/settings')}><Cloud size={15} /><span>Demo environment</span><ChevronDown size={13} /></button>
          <span className={`sync-indicator sync-${streamState}`} aria-live="polite" title={`${data.dashboard?.is_demo ? 'Application changes stream from AstraDeploy; provider telemetry remains demo-only until connected. ' : 'Application changes stream from AstraDeploy. '}${syncState === 'error' ? 'The latest snapshot request failed; the last good data is retained. ' : ''}${lastSynced ? `Last snapshot: ${lastSynced.toLocaleTimeString()}.` : 'Loading the initial snapshot.'}`}><i />{streamState === 'live' ? `Connected${syncState === 'error' ? ' · snapshot error' : ''}` : streamState === 'reconnecting' ? 'Reconnecting' : 'Connecting'}</span>
          <button className="icon-button notification-button" aria-label="View alerts" onClick={() => navigate('/alerts')}><Bell size={17} />{(data.dashboard?.summary.open_alerts || 0) > 0 && <i />}</button>
          <div className="profile-wrap"><button className="profile-button" onClick={() => setProfileOpen(v => !v)} aria-expanded={profileOpen}><span className="avatar">{(session.user.name || 'A').split(' ').map(x => x[0]).slice(0, 2).join('').toUpperCase()}</span><span className="profile-name">{session.user.name.split(' ')[0]}</span><ChevronDown size={14} /></button>{profileOpen && <div className="profile-menu"><div className="profile-menu-head"><b>{session.user.name}</b><span>{session.user.email || session.user.role}</span></div><button onClick={() => { setProfileOpen(false); navigate('/team'); }}><Users size={15} />Team & access</button><button onClick={() => { setProfileOpen(false); navigate('/settings'); }}><Settings size={15} />Settings</button><button onClick={doLogout}><LogOut size={15} />Sign out</button></div>}</div>
        </div>
      </header>
      <div className="workspace-content">
        {error && <div className="banner banner-error"><AlertTriangle size={17} /><span>{error}<small>Showing the last successful snapshot when available. The event stream reconnects automatically; fallback refresh runs every 60 seconds.</small></span><button onClick={() => void refresh()}>Retry now</button></div>}
        <Routes>
          <Route path="/" element={<OverviewPage {...shared} />} />
          <Route path="/advisor" element={<AdvisorPage {...shared} />} />
          <Route path="/workloads" element={<WorkloadsPage {...shared} />} />
          <Route path="/optimizer" element={<OperationsPage page="optimizer" {...shared} />} />
          <Route path="/deployments" element={<OperationsPage page="deployments" {...shared} />} />
          <Route path="/pipelines" element={<OperationsPage page="pipelines" {...shared} />} />
          <Route path="/models" element={<OperationsPage page="models" {...shared} />} />
          <Route path="/experiments" element={<OperationsPage page="experiments" {...shared} />} />
          <Route path="/monitoring" element={<OperationsPage page="monitoring" {...shared} />} />
          <Route path="/cost" element={<OperationsPage page="cost" {...shared} />} />
          <Route path="/infrastructure" element={<OperationsPage page="infrastructure" {...shared} />} />
          <Route path="/alerts" element={<OperationsPage page="alerts" {...shared} />} />
          <Route path="/reports" element={<OperationsPage page="reports" {...shared} />} />
          <Route path="/team" element={<OperationsPage page="team" {...shared} />} />
          <Route path="/settings" element={<OperationsPage page="settings" {...shared} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      <footer className="main-footer"><span><i className={`footer-status footer-${syncState === 'error' ? 'error' : streamState === 'live' ? 'ok' : 'connecting'}`} />Cloud metrics are demo · app data streams live{lastSynced ? ` · snapshot ${lastSynced.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}` : ''} · 60s fallback · providers not connected</span><span>© AstraDeploy · Evidence-led infrastructure decisions</span></footer>
    </main>
    {toast && <Toast message={toast} onClose={() => setToast(null)} />}
  </div>;
}
