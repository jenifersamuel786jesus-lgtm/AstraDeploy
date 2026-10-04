import { useState } from 'react';
import { ArrowRight, Check, CheckCircle2, ChevronRight, CircleHelp, Cloud, Cpu, HardDrive, Info, LockKeyhole, MemoryStick, ShieldCheck, Sparkles, Zap } from 'lucide-react';
import { api, type Recommendation, type SessionInfo, type WorkloadInput } from '../api';
import { WorkloadForm, emptyWorkload } from '../components/WorkloadForm';
import { IntegrationNotice, PageHeader, StatusBadge } from '../components/ui';

type Props = { refresh: () => Promise<void>; notify: (title: string, tone?: 'success' | 'error' | 'info') => void; session: SessionInfo };
export function AdvisorPage({ refresh, notify, session }: Props) {
  const [choices, setChoices] = useState<Recommendation[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState<{ state: string; steps: string[]; estimated_cost_usd: number; real_resources_created: boolean } | null>(null);
  const [analysisNote, setAnalysisNote] = useState('');
  const run = async (input: WorkloadInput) => {
    setBusy(true); setPlan(null);
    try {
      const workload = await api.createWorkload(input);
      await api.analyze(workload.id);
      const result = await api.recommend(workload.id);
      setChoices(result.recommendations);
      setSelected('');
      setAnalysisNote(`${workload.name} was registered and analyzed using transparent rules. Historical telemetry and current provider pricing are not connected.`);
      await refresh();
      notify('Three resource plans are ready', 'success');
    } finally { setBusy(false); }
  };
  const choose = async (item: Recommendation) => {
    try { await api.selectRecommendation(item.id); setSelected(item.id); setChoices(current => current.map(x => ({ ...x, selected: x.id === item.id }))); notify(`${item.tier} plan selected`, 'success'); }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not select the plan.', 'error'); }
  };
  const createPreview = async () => {
    const current = choices.find(x => x.id === selected);
    if (!current) return;
    setBusy(true);
    try { const result = await api.previewPlan(current.id); setPlan(result); notify('Demo plan preview created · no resources changed', 'info'); await refresh(); }
    catch (error) { notify(error instanceof Error ? error.message : 'Could not create the plan preview.', 'error'); }
    finally { setBusy(false); }
  };
  return <div className="page-stack">
    <PageHeader eyebrow="RESOURCE DECISION ENGINE / RULES V1.0" title="AI Resource Advisor" subtitle="Translate workload context into explainable infrastructure options — before anything is provisioned." actions={<div className="engine-ready"><span><i />RULE ENGINE</span><b><Sparkles size={14} />Ready</b></div>} />
    <div className="advisor-intro"><div className="advisor-intro-icon"><Sparkles size={20} /></div><div><b>Start with the workload, not an instance catalog.</b><span>Compare three resource profiles, inspect trade-offs and validate your budget. Estimates use an illustrative demo rate card and are not provider quotes.</span></div><span className="intro-step">1 <i>/</i> 3</span></div>
    <div className="advisor-layout"><section className="panel advisor-form-panel"><div className="advisor-form-head"><div><span className="eyebrow">WORKLOAD INPUT</span><h2>Tell us what you're running</h2><p>Requirements are stored in your organization workspace.</p></div><span className="step-chip"><span>01</span> Define</span></div><WorkloadForm key={choices.length ? 'recommend-again' : 'recommend-first'} initial={emptyWorkload} onSubmit={run} submitLabel={busy ? 'Analyzing…' : 'Analyze & compare'} compact /><div className="advisor-form-foot"><span><LockKeyhole size={14} />Only organization members with write access can save or compare scenarios.</span><span className="rule-version">RULESET 1.0.0</span></div></section>
      <aside className="advisor-context"><div className="context-card context-accent"><div className="context-top"><span className="context-orbit"><Sparkles size={18} /></span><span className="context-mark">ASTRA / AI</span></div><h3>Context engine</h3><p>Deterministic, reproducible recommendations — not a black-box promise.</p><div className="context-factor"><span><Check size={13} />Workload inputs</span><b>Available</b></div><div className="context-factor"><span><Check size={13} />Budget validation</span><b>Rule based</b></div><div className="context-factor context-muted"><span><CircleHelp size={13} />Historical metrics</span><b>Not connected</b></div><div className="context-factor context-muted"><span><CircleHelp size={13} />Live price catalog</span><b>Not connected</b></div></div><div className="context-caveat"><Info size={16} /><span><b>Confidence reflects evidence.</b> Without provider telemetry or historical usage, this is a low-to-moderate rule-based fit — not a performance guarantee.</span></div></aside></div>
    {analysisNote && <div className="analysis-success"><CheckCircle2 size={18} /><div><b>Analysis complete</b><span>{analysisNote}</span></div><StatusBadge tone="demo">DEMO ESTIMATE</StatusBadge></div>}
    {choices.length > 0 && <section className="recommendation-section"><div className="recommendation-heading"><div><span className="eyebrow">02 / COMPARE RESOURCE PROFILES</span><h2>Three ways to provision this workload</h2><p>Compare cost, capacity and the trade-offs behind each option.</p></div><span className="estimate-label"><Info size={14} />Estimates · not live quotes</span></div><div className="recommendation-grid">{choices.map((item, index) => {
      const isSelected = selected === item.id;
      const features = [{ icon: Cpu, value: `${item.cpu_cores} vCPU`, label: 'Compute' }, { icon: MemoryStick, value: `${item.memory_gb} GB`, label: 'Memory' }, { icon: Zap, value: item.gpu_count ? `${item.gpu_count} GPU` : 'CPU only', label: 'Accelerator' }, { icon: HardDrive, value: `${item.storage_gb} GB`, label: 'Storage' }];
      return <article className={`recommendation-card rec-${index} ${isSelected ? 'rec-selected' : ''}`} key={item.id}><div className="rec-topline"><span className={`rec-rank rank-${index}`}>0{index + 1}</span><StatusBadge tone={index === 1 ? 'success' : index === 0 ? 'info' : 'warning'}>{item.tier}</StatusBadge>{index === 1 && <span className="recommended-flag">BEST FIT</span>}</div><div className="rec-cost">${item.estimated_cost_usd.toFixed(2)}<small> / run est.</small></div><div className="rec-subcost">{item.runtime_hours_estimate}h estimated runtime · {item.provider} profile</div><div className="rec-instance"><Cloud size={15} /><b>{item.instance}</b></div><div className="rec-config">{features.map(feature => { const Icon = feature.icon; return <div key={feature.label}><span className="rec-config-icon"><Icon size={15} /></span><span><b>{feature.value}</b><small>{feature.label}</small></span></div>; })}</div><div className="rec-architecture"><b>Deployment pattern</b><p>{item.architecture}</p><ul>{item.rationale.slice(0, 2).map(reason => <li key={reason}>{reason}</li>)}</ul></div><div className="rec-evidence"><span><ShieldCheck size={14} />{item.confidence}</span><span>Budget {item.fits_budget ? 'within range' : 'exceeded'}</span></div><button className={`button ${isSelected ? 'button-selected' : 'button-secondary'} button-wide`} onClick={() => choose(item)} disabled={!item.fits_budget && session.user.role === 'Viewer'}>{isSelected ? <><Check size={16} /> Selected</> : <>Select this plan <ChevronRight size={16} /></>}</button></article>;
    })}</div><div className="recommendation-note"><span><Info size={16} /></span><p><b>Assumptions:</b> USD; illustrative compute/storage rates; single region; no egress, taxes, discounts or managed-service charges. Provider availability and latency are not live-validated.</p></div><div className="plan-actions"><div><b>{selected ? 'Plan selected · review a safe preview next' : 'Choose a plan to continue'}</b><span>Preview generates a simulated infrastructure plan only; it does not create cloud resources.</span></div><button className="button button-primary" disabled={!selected || busy} onClick={createPreview}><ShieldCheck size={16} />Preview infrastructure plan <ArrowRight size={15} /></button></div></section>}
    {plan && <section className="plan-preview"><div className="plan-preview-icon"><CheckCircle2 size={18} /></div><div className="plan-preview-body"><div className="plan-preview-title"><span className="eyebrow">PLAN PREVIEW / {plan.state.toUpperCase()}</span><StatusBadge tone="demo">SIMULATED</StatusBadge></div><h3>Infrastructure preview is ready</h3><p>No cloud resources were created or changed. Estimated run cost: <b>${plan.estimated_cost_usd.toFixed(2)}</b> · real resource creation: <b>No</b>.</p><ol>{plan.steps.map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, '0')}</span>{step}</li>)}</ol></div></section>}
    <IntegrationNotice title="Live provider integrations are not connected" detail="AWS, Azure, GCP, billing and historical monitoring remain unavailable in this workspace. The advisor uses user requirements and a documented demo rate card." />
  </div>;
}
