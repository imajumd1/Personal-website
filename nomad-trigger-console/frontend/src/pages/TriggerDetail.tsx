import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Play, ArrowLeft } from 'lucide-react';
import { api } from '../api';
import type { ArbitrationRules, Trigger } from '../types';

export default function TriggerDetail() {
  const { id } = useParams<{ id: string }>();
  const [trigger, setTrigger] = useState<Trigger | null>(null);
  const [rules, setRules] = useState<ArbitrationRules | null>(null);
  const [lastTested, setLastTested] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    api.getTrigger(id)
      .then((r) => {
        setTrigger(r.trigger);
        setRules(r.arbitration_rules);
        setLastTested(r.last_tested);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const toggleStatus = async (status: Trigger['status']) => {
    if (!id || !trigger) return;
    const updated = await api.updateTrigger(id, { status });
    setTrigger(updated);
  };

  if (loading) return <div className="loading">Loading trigger…</div>;
  if (!trigger) return <div className="error">Trigger not found</div>;

  return (
    <>
      <div className="page-header">
        <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          <ArrowLeft size={14} /> Back to Explorer
        </Link>
        <h2>{trigger.name}</h2>
        <p><code>{trigger.trigger_id}</code> · {trigger.lifecycle_phase} · Created by {trigger.created_by}</p>
      </div>

      <div className="toolbar">
        <div className="actions-row">
          <select
            value={trigger.status}
            onChange={(e) => toggleStatus(e.target.value as Trigger['status'])}
            style={{ width: 'auto' }}
          >
            <option value="Draft">Draft</option>
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        </div>
        <Link to={`/triggers/${id}/test`} className="btn btn-primary">
          <Play size={16} /> Test Trigger
        </Link>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="detail-section">
            <h3>Condition (Plain English)</h3>
            <p>{trigger.condition_human}</p>
          </div>

          <div className="detail-section">
            <h3>Structured Condition</h3>
            <ul className="clause-list">
              {trigger.condition_structured.clauses.map((c, i) => (
                <li key={i}>
                  <strong>{c.field}</strong> {c.operator} {JSON.stringify(c.value)}
                  <br /><span style={{ color: 'var(--text-muted)' }}>{c.description}</span>
                </li>
              ))}
            </ul>
            {trigger.condition_structured.time_window && (
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                Time window: {trigger.condition_structured.time_window}
              </p>
            )}
          </div>

          <div className="detail-section">
            <h3>NBA / Offer</h3>
            <p>{trigger.nba_offer}</p>
          </div>
        </div>

        <div className="card">
          <div className="detail-section">
            <h3>Arbitration Rules</h3>
            {rules && (
              <div className="rule-grid">
                <div className="rule-item">
                  <div className="key">Priority Tier</div>
                  <div className="val">{rules.priority_tier}</div>
                </div>
                <div className="rule-item">
                  <div className="key">Priority Rule</div>
                  <div className="val">{rules.priority_rule}</div>
                </div>
                <div className="rule-item">
                  <div className="key">Frequency Cap</div>
                  <div className="val">{rules.frequency_cap_bucket}</div>
                </div>
                <div className="rule-item">
                  <div className="key">Expected Value</div>
                  <div className="val">{rules.expected_value_formula}</div>
                </div>
                <div className="rule-item">
                  <div className="key">Channel Routing</div>
                  <div className="val">{rules.channel_routing}</div>
                </div>
                <div className="rule-item">
                  <div className="key">Offer Value</div>
                  <div className="val">${rules.offer_value}</div>
                </div>
              </div>
            )}
          </div>

          <div className="detail-section">
            <h3>Last Tested</h3>
            {lastTested ? (
              <p style={{ fontSize: '0.875rem' }}>
                {(lastTested as { profile_first_name: string; verdict: string; timestamp: string }).profile_first_name}{' '}
                — {(lastTested as { verdict: string }).verdict}{' '}
                <span style={{ color: 'var(--text-muted)' }}>
                  ({new Date((lastTested as { timestamp: string }).timestamp).toLocaleString()})
                </span>
              </p>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Not yet tested</p>
            )}
          </div>

          <div className="detail-section">
            <h3>Test History</h3>
            {trigger.test_history.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No test runs yet</p>
            ) : (
              <table>
                <thead>
                  <tr><th>Profile</th><th>Verdict</th><th>When</th></tr>
                </thead>
                <tbody>
                  {trigger.test_history.slice(0, 10).map((h, i) => (
                    <tr key={i}>
                      <td>{h.profile_first_name}</td>
                      <td><span className={`badge badge-${h.verdict.toLowerCase()}`}>{h.verdict}</span></td>
                      <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                        {new Date(h.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
