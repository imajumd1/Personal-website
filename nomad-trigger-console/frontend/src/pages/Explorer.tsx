import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Play, Eye } from 'lucide-react';
import { api } from '../api';
import type { Trigger } from '../types';

function StatusBadge({ status }: { status: string }) {
  const cls = status === 'Active' ? 'badge-active' : status === 'Draft' ? 'badge-draft' : 'badge-inactive';
  return <span className={`badge ${cls}`}>{status}</span>;
}

function PriorityBadge({ tier }: { tier: string }) {
  const cls = tier === 'Operational' ? 'badge-operational' : 'badge-commercial';
  return <span className={`badge ${cls}`}>{tier}</span>;
}

export default function Explorer() {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('');

  useEffect(() => {
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    if (channelFilter) params.channel = channelFilter;
    if (lifecycleFilter) params.lifecycle = lifecycleFilter;

    setLoading(true);
    api.listTriggers(params)
      .then((r) => setTriggers(r.triggers))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [statusFilter, channelFilter, lifecycleFilter]);

  return (
    <>
      <div className="page-header">
        <h2>Trigger Explorer</h2>
        <p>Review every trigger in the system — seeded catalog and marketer-authored definitions.</p>
      </div>

      <div className="toolbar">
        <div className="filters">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="Active">Active</option>
            <option value="Draft">Draft</option>
            <option value="Inactive">Inactive</option>
          </select>
          <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)}>
            <option value="">All channels</option>
            <option value="SMS">SMS</option>
            <option value="Email">Email</option>
          </select>
          <select value={lifecycleFilter} onChange={(e) => setLifecycleFilter(e.target.value)}>
            <option value="">All lifecycle phases</option>
            <option value="Inspiration">Inspiration / Search</option>
            <option value="Abandonment">Pre-Booking</option>
            <option value="Confirmed">Booking Confirmed</option>
            <option value="Pre-Trip">Pre-Trip</option>
            <option value="Disruption">Day of Travel</option>
            <option value="Arrival">Post-Arrival</option>
            <option value="Post-Trip">Post-Trip</option>
          </select>
        </div>
        <Link to="/builder" className="btn btn-primary">+ New Trigger</Link>
      </div>

      <div className="card table-wrap">
        {loading ? (
          <div className="loading">Loading triggers…</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Lifecycle</th>
                <th>Condition</th>
                <th>Channel</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {triggers.map((t) => (
                <tr key={t.trigger_id}>
                  <td><code>{t.trigger_id}</code></td>
                  <td><strong>{t.name}</strong></td>
                  <td>{t.lifecycle_phase}</td>
                  <td style={{ maxWidth: 260, fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                    {t.condition_human}
                  </td>
                  <td>{t.suggested_channel}</td>
                  <td><PriorityBadge tier={t.priority_tier} /></td>
                  <td><StatusBadge status={t.status} /></td>
                  <td>
                    <div className="actions-row">
                      <Link to={`/triggers/${t.trigger_id}`} className="btn btn-sm btn-secondary">
                        <Eye size={14} /> Detail
                      </Link>
                      <Link to={`/triggers/${t.trigger_id}/test`} className="btn btn-sm btn-primary">
                        <Play size={14} /> Test
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
