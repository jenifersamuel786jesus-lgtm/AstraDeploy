export type ApiError = Error & { status?: number };

const API = '/api/v1';

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`${API}${path}`, { credentials: 'same-origin', ...options, headers });
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json() as { detail?: unknown; error?: unknown };
      detail = typeof body.detail === 'string' ? body.detail : typeof body.error === 'string' ? body.error : '';
    } catch { /* retain endpoint and status when no JSON body is returned */ }
    const error = new Error(`${path} · HTTP ${response.status}${detail ? `: ${detail}` : ''}`) as ApiError;
    error.status = response.status;
    throw error;
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<SessionInfo>('/auth/me'),
  startOAuth: (redirect_uri: string) => request<{ authorization_url: string }>('/auth/start', { method: 'POST', referrerPolicy: 'same-origin', body: JSON.stringify({ redirect_uri }) }),
  dashboard: (range = '7d') => request<DashboardData>(`/dashboard?range=${range}`),
  workspace: (range = '7d') => request<WorkspaceSnapshot>(`/workspace?range=${range}`),
  workspaceEvents: () => new EventSource(`${API}/workspace/events`, { withCredentials: true }),
  projects: () => request<{ items: Project[]; total: number }>('/projects'),
  createProject: (payload: { name: string; description: string }) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  workloads: () => request<{ items: Workload[]; total: number }>('/workloads'),
  createWorkload: (data: WorkloadInput) => request<Workload>('/workloads', { method: 'POST', body: JSON.stringify(data) }),
  analyze: (id: string) => request<Analysis>(`/workloads/${id}/analysis`, { method: 'POST' }),
  recommend: (id: string) => request<{ recommendations: Recommendation[]; is_demo: boolean }>(`/workloads/${id}/recommendations`, { method: 'POST' }),
  selectRecommendation: (id: string) => request<{ ok: boolean; tier: string }>(`/recommendations/${id}/select`, { method: 'POST' }),
  previewPlan: (id: string) => request<ProvisioningPreview>(`/recommendations/${id}/plan`, { method: 'POST' }),
  records: (kind: string) => request<{ items: RecordItem[]; total: number }>(`/records/${kind}`),
  action: (action: string, record_id?: string, payload: Record<string, unknown> = {}) => request<RecordItem>('/actions', { method: 'POST', body: JSON.stringify({ action, record_id, payload }) }),
  createRecord: (kind: string, payload: Record<string, unknown>) => request<RecordItem>('/records', { method: 'POST', body: JSON.stringify({ kind, payload }) }),
  generateReport: (reportType: ReportType = 'Workload analysis') => request<RecordItem>('/reports/generate', { method: 'POST', body: JSON.stringify({ report_type: reportType }) }),
  team: () => request<{ items: TeamMember[]; total: number }>('/team'),
  updateTeamRole: (userId: string, role: string) => request<{ user_id: string; role: string; organization_id: string }>(`/team/${userId}/role`, { method: 'PATCH', body: JSON.stringify({ role }) }),
  settings: () => request<SettingsData>('/settings'),
  audit: () => request<{ items: AuditEvent[] }>('/audit'),
};

export type SessionInfo = { user: { id: string; name: string; email?: string | null; role: string }; organization: { id: string }; demo_mode: boolean };
export type WorkspaceSnapshot = { revision: number; dashboard: DashboardData; workloads: { items: Workload[]; total: number }; records: Record<string, RecordItem[]>; team: { items: TeamMember[]; total: number }; settings: SettingsData; audit: { items: AuditEvent[] } };
export type ReportType = 'Workload analysis' | 'Resource recommendations' | 'Cost optimization' | 'Deployment summary' | 'Pipeline execution' | 'Audit activity';
export type Project = { id: string; name: string; description: string; created_at: string };
export type WorkloadInput = { name: string; project_id?: string; task_type: string; framework: string; dataset_gb: number; training_samples: number; training_hours: number; cpu_cores: number; memory_gb: number; gpu_count: number; storage_gb: number; latency_ms: number; inference_rps: number; provider: string; budget_usd: number; availability: string };
export type Workload = WorkloadInput & { id: string; status: string; requirements: Record<string, number | string>; is_demo: boolean; created_at: string };
export type Recommendation = { id: string; workload_id: string; tier: string; provider: string; instance: string; cpu_cores: number; memory_gb: number; gpu_count: number; storage_gb: number; estimated_cost_usd: number; runtime_hours_estimate: number; fits_budget: boolean; rationale: string[]; confidence: string; architecture: string; assumptions: string[]; selected?: boolean; is_demo: boolean };
export type Analysis = { id: string; classification: string; demand: Record<string, number>; profile: Record<string, number>; bottlenecks: string[]; limitations: string[]; source: string; is_demo: boolean };
export type ProvisioningPreview = { id: string; name: string; state: string; mode: string; real_resources_created: boolean; steps: string[]; estimated_cost_usd: number };
export type RecordItem = {
  id: string; name?: string; title?: string; type?: string; status?: string; state?: string;
  is_demo?: boolean; mode?: string; created_at?: string; updated?: string; project?: string;
  progress?: number; stages?: string[]; framework?: string; version?: string; stage?: string;
  accuracy?: number | null; run?: string; model?: string; metric?: string; duration?: string;
  label?: string; current?: number | string; unit?: string; trend?: string; severity?: string;
  description?: string; source?: string; time?: string; environment?: string; provider?: string;
  latency_ms?: number; endpoint?: string | null; region?: string; amount_usd?: number; change_pct?: number;
  limit_usd?: number; spent_usd?: number; scope?: string; generated_at?: string; findings?: string[];
  saving_pct?: number; risk?: string; target?: string; current_config?: string; recommended?: string;
  monthly_before_usd?: number; monthly_after_usd?: number; [key: string]: unknown;
};
export type TeamMember = { id: string; name: string; email?: string | null; role: string; joined_at: string };
export type AuditEvent = { id: string; action: string; detail: Record<string, unknown>; source: string; created_at: string };
export type SettingsData = { organization: { id: string; name: string } | null; role: string; integrations: Array<{ name: string; category: string; status: string; capability: string }>; mode: string; database: string; live_cloud_actions_enabled: boolean };
export type DashboardData = { source: string; is_demo: boolean; summary: { workloads: number; deployments: number; pipelines: number; cpu_percent: number; memory_percent: number; gpu_percent: number; estimated_monthly_spend_usd: number; actual_spend_usd: number | null; allocation_efficiency: number; optimization_opportunities: number; open_alerts: number }; resource_series: Array<{ day: string; cpu: number; memory: number; cost: number }>; cost_series: Array<{ day: string; cpu: number; memory: number; cost: number }>; workload_mix: Array<{ name: string; value: number }>; provider_mix: Array<{ name: string; value: number }>; recent_activity: RecordItem[] };
