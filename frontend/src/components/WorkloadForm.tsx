import { useEffect, useState } from 'react';
import { api, type Project, type WorkloadInput } from '../api';

export const emptyWorkload: WorkloadInput = {
  name: '', task_type: 'Training', framework: 'PyTorch', dataset_gb: 48,
  training_samples: 250000, training_hours: 8, cpu_cores: 4, memory_gb: 16,
  gpu_count: 0, storage_gb: 100, latency_ms: 250, inference_rps: 0,
  provider: 'No preference', budget_usd: 0, availability: 'Standard',
};

const numericFields: Array<{ key: keyof WorkloadInput; label: string; min: number; step?: number; hint?: string }> = [
  { key: 'dataset_gb', label: 'Dataset size', min: 0.1, step: 0.1, hint: 'GB' },
  { key: 'training_samples', label: 'Training samples', min: 1 },
  { key: 'training_hours', label: 'Training duration', min: 0.1, step: 0.5, hint: 'hours' },
  { key: 'cpu_cores', label: 'CPU cores', min: 1 },
  { key: 'memory_gb', label: 'Memory', min: 1, hint: 'GB' },
  { key: 'gpu_count', label: 'GPU count', min: 0 },
  { key: 'storage_gb', label: 'Storage', min: 1, hint: 'GB' },
  { key: 'latency_ms', label: 'Latency target', min: 1, hint: 'ms' },
  { key: 'inference_rps', label: 'Inference requests', min: 0, hint: 'req/sec' },
  { key: 'budget_usd', label: 'Run budget', min: 0, step: 5, hint: 'USD · 0 = no cap' },
];

export function WorkloadForm({ initial, onSubmit, onCancel, submitLabel = 'Save workload', compact = false }: {
  initial?: WorkloadInput; onSubmit: (value: WorkloadInput) => Promise<void> | void;
  onCancel?: () => void; submitLabel?: string; compact?: boolean;
}) {
  const [form, setForm] = useState<WorkloadInput>(initial || emptyWorkload);
  const [projects, setProjects] = useState<Project[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { if (initial) setForm(initial); }, [initial]);
  useEffect(() => { api.projects().then(result => setProjects(result.items)).catch(() => setProjects([])); }, []);
  const set = (key: keyof WorkloadInput, value: string) => setForm(current => ({ ...current, [key]: key === 'name' || key === 'task_type' || key === 'framework' || key === 'provider' || key === 'availability' ? value : Number(value) }));
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (form.name.trim().length < 2) { setError('Give this workload a name of at least two characters.'); return; }
    setSubmitting(true); setError('');
    try { await onSubmit({ ...form, name: form.name.trim() }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save workload.'); }
    finally { setSubmitting(false); }
  };
  return <form className={`workload-form ${compact ? 'workload-form-compact' : ''}`} onSubmit={submit}>
    <div className="form-section-title"><span>01</span><b>Workload context</b><small>Shape your resource estimate</small></div>
    <div className="form-grid form-grid-3">
      <label className="field field-span-2"><span>Workload name <i>Required</i></span><input value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. Vision defect classifier" required minLength={2} maxLength={180} /></label>
      <label className="field"><span>Project</span><select value={form.project_id || ''} onChange={e => setForm(current => ({ ...current, project_id: e.target.value || undefined }))}><option value="">Default project</option>{projects.map(project => <option value={project.id} key={project.id}>{project.name}</option>)}</select></label>
      <label className="field"><span>ML task type</span><select value={form.task_type} onChange={e => set('task_type', e.target.value)}>{['Training', 'Model inference', 'Batch prediction', 'Data preprocessing', 'Computer vision training', 'Natural language processing', 'Deep learning', 'Traditional ML training', 'Real-time prediction', 'Large-scale data processing'].map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Framework</span><select value={form.framework} onChange={e => set('framework', e.target.value)}>{['PyTorch', 'TensorFlow', 'XGBoost', 'scikit-learn', 'ONNX Runtime', 'JAX', 'Other'].map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Preferred provider</span><select value={form.provider} onChange={e => set('provider', e.target.value)}>{['No preference', 'AWS', 'Azure', 'GCP'].map(x => <option key={x}>{x}</option>)}</select></label>
      <label className="field"><span>Availability</span><select value={form.availability} onChange={e => set('availability', e.target.value)}>{['Standard', 'High availability', 'Mission critical'].map(x => <option key={x}>{x}</option>)}</select></label>
    </div>
    <div className="form-section-title form-section-spaced"><span>02</span><b>Compute & constraints</b><small>Estimates only · validate before production</small></div>
    <div className="form-grid form-grid-5">
      {numericFields.map(field => <label className="field" key={field.key}><span>{field.label}</span><div className="input-suffix"><input type="number" min={field.min} step={field.step || 1} value={form[field.key] as number} onChange={e => set(field.key, e.target.value)} /><small>{field.hint}</small></div></label>)}
    </div>
    {error && <div className="form-error">{error}</div>}
    <div className="form-footer"><span><i className="form-lock" /> Requirements stay within your organization</span><div>{onCancel && <button type="button" className="button button-quiet" onClick={onCancel}>Cancel</button>}<button className="button button-primary" type="submit" disabled={submitting}>{submitting ? 'Working…' : submitLabel}<span>→</span></button></div></div>
  </form>;
}
