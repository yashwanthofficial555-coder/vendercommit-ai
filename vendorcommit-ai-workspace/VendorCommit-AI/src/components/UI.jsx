import React from 'react';
import { X, CheckCircle2, AlertTriangle, Clock3 } from 'lucide-react';

export function Badge({ children, tone = 'gray', dot = false }) {
  const tones = {
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/10',
    amber: 'bg-amber-50 text-amber-700 ring-amber-600/10',
    red: 'bg-rose-50 text-rose-700 ring-rose-600/10',
    blue: 'bg-blue-50 text-blue-700 ring-blue-600/10',
    purple: 'bg-violet-50 text-violet-700 ring-violet-600/10',
    gray: 'bg-slate-100 text-slate-600 ring-slate-500/10',
  };
  const dots = { green: 'bg-emerald-500', amber: 'bg-amber-500', red: 'bg-rose-500', blue: 'bg-blue-500', purple: 'bg-violet-500', gray: 'bg-slate-400' };
  return <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1 ring-inset ${tones[tone]}`}>{dot && <span className={`h-1.5 w-1.5 rounded-full ${dots[tone]}`} />}{children}</span>;
}

export function RiskBadge({ risk }) { return <Badge tone={risk === 'Low' ? 'green' : risk === 'High' ? 'red' : 'amber'} dot>{risk} risk</Badge>; }
export function StatusBadge({ status }) {
  const tone = status === 'Verified' || status === 'Active' ? 'green' : status === 'At risk' || status === 'Review' ? 'red' : 'amber';
  return <Badge tone={tone} dot>{status}</Badge>;
}

export function Avatar({ name, initials, color = '#2878f0', size = 'md' }) {
  const sizes = { sm: 'h-8 w-8 text-[10px]', md: 'h-10 w-10 text-xs', lg: 'h-14 w-14 text-base' };
  return <div className={`${sizes[size]} flex shrink-0 items-center justify-center rounded-lg font-bold text-white`} style={{ background: `linear-gradient(145deg, ${color}, ${color}bb)` }}>{initials || name?.split(' ').map(n => n[0]).slice(0,2).join('')}</div>;
}

export function PageTitle({ eyebrow, title, description, children }) {
  return <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
    <div>{eyebrow && <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-brand-600">{eyebrow}</div>}<h1 className="text-[26px] font-bold tracking-[-.035em] text-slate-900">{title}</h1>{description && <p className="mt-1.5 text-sm text-slate-500">{description}</p>}</div>
    {children && <div className="flex shrink-0 items-center gap-2.5">{children}</div>}
  </div>;
}

export function Modal({ open, onClose, title, description, children, wide = false }) {
  if (!open) return null;
  return <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 sm:p-6" role="dialog" aria-modal="true">
    <div className="absolute inset-0 bg-navy-950/45 backdrop-blur-[2px]" onClick={onClose} />
    <div className={`relative max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white shadow-float ${wide ? 'max-w-2xl' : 'max-w-lg'}`}>
      <div className="flex items-start justify-between border-b border-slate-100 px-6 py-5"><div><h2 className="text-lg font-bold text-slate-900">{title}</h2>{description && <p className="mt-1 text-sm text-slate-500">{description}</p>}</div><button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"><X size={19}/></button></div>
      {children}
    </div>
  </div>;
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return <div className="flex flex-col items-center justify-center px-6 py-16 text-center"><div className="mb-4 rounded-xl bg-slate-100 p-3 text-slate-500"><Icon size={24}/></div><h3 className="font-semibold text-slate-900">{title}</h3><p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>{action && <div className="mt-5">{action}</div>}</div>;
}

export function Confidence({ value }) {
  const color = value >= 90 ? 'bg-emerald-500' : value >= 75 ? 'bg-amber-500' : 'bg-rose-500';
  return <div className="flex items-center gap-2"><div className="h-1.5 w-14 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${color}`} style={{width: `${value}%`}}/></div><span className="text-xs font-medium text-slate-600">{value}%</span></div>;
}

export const ActivityIcon = ({ type }) => {
  const map = { verified: [CheckCircle2, 'bg-emerald-50 text-emerald-600'], price: [AlertTriangle, 'bg-amber-50 text-amber-600'], meeting: [Clock3, 'bg-blue-50 text-blue-600'], risk: [AlertTriangle, 'bg-rose-50 text-rose-600'] };
  const [Icon, cls] = map[type] || map.meeting;
  return <div className={`rounded-lg p-2 ${cls}`}><Icon size={16}/></div>;
};

export function Toast({ message, onClose }) {
  if (!message) return null;
  return <div className="fixed bottom-5 right-5 z-[90] flex items-center gap-3 rounded-xl bg-navy-950 px-4 py-3 text-sm font-medium text-white shadow-float"><CheckCircle2 size={18} className="text-emerald-400"/>{message}<button onClick={onClose} className="ml-2 text-slate-400 hover:text-white"><X size={16}/></button></div>;
}
