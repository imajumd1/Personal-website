import { Fragment, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Inbox } from 'lucide-react';
import { api } from '../api';
import type { TestResult } from '../types';

function VerdictBadge({ verdict }: { verdict: string }) {
  const cls = verdict === 'Pass' ? 'badge-pass' : verdict === 'Blocked' ? 'badge-blocked' : 'badge-fail';
  return <span className={`badge ${cls}`}>{verdict}</span>;
}

export default function MessageQueue() {
  const [entries, setEntries] = useState<TestResult[]>([]);
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true);
  const [triggerFilter, setTriggerFilter] = useState('');
  const [channelFilter, setChannelFilter] = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (triggerFilter) params.trigger_id = triggerFilter;
    if (channelFilter) params.channel = channelFilter;

    setLoading(true);
    api.getQueue(params)
      .then((r) => {
        setEntries(r.entries);
        setNotice(r.simulation_notice);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [triggerFilter, channelFilter]);

  return (
    <>
      <div className="page-header">
        <h2>Message Queue</h2>
        <p>Simulated outbox — every test result lands here. No real messages are sent.</p>
      </div>

      <div className="sim-banner">
        <Inbox size={16} /> {notice || 'SIMULATION ONLY — No messages are sent to real customers.'}
      </div>

      <div className="filters">
        <input placeholder="Filter by trigger ID (e.g. TRG-105)…" value={triggerFilter} onChange={(e) => setTriggerFilter(e.target.value)} />
        <select value={channelFilter} onChange={(e) => setChannelFilter(e.target.value)}>
          <option value="">All channels</option>
          <option value="SMS">SMS</option>
          <option value="Email">Email</option>
          <option value="Blocked">Blocked</option>
        </select>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading">Loading queue…</div>
        ) : entries.length === 0 ? (
          <div className="empty-state">
            <Inbox size={32} style={{ opacity: 0.3, marginBottom: '0.75rem' }} />
            <p>No messages in the queue yet. Run a trigger test to populate this feed.</p>
            <Link to="/" className="btn btn-primary" style={{ marginTop: '1rem' }}>Go to Trigger Explorer</Link>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Trigger</th>
                <th>Profile</th>
                <th>Verdict</th>
                <th>Channel</th>
                <th>Preview</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <Fragment key={e.id}>
                  <tr onClick={() => setExpanded(expanded === e.id ? null : e.id)} style={{ cursor: 'pointer' }}>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                      {new Date(e.timestamp).toLocaleString()}
                    </td>
                    <td>
                      <Link to={`/triggers/${e.trigger_id}`} onClick={(ev) => ev.stopPropagation()}>
                        {e.trigger_name}
                      </Link>
                    </td>
                    <td>{e.profile_first_name}</td>
                    <td><VerdictBadge verdict={e.verdict} /></td>
                    <td>
                      {e.selected_channel ? (
                        <span className={`badge badge-${e.selected_channel.toLowerCase()}`}>{e.selected_channel}</span>
                      ) : e.verdict === 'Blocked' ? (
                        <span className="badge badge-blocked">Blocked</span>
                      ) : '—'}
                    </td>
                    <td style={{ maxWidth: 200, fontSize: '0.8125rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {e.sms_body || e.email_subject || e.block_reason || '—'}
                    </td>
                    <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', maxWidth: 220 }}>
                      {e.explanation}
                    </td>
                  </tr>
                  {expanded === e.id && (
                    <tr>
                      <td colSpan={7} style={{ background: 'var(--bg)', padding: '1rem' }}>
                        {e.sms_body && <div className="sms-preview">{e.sms_body}</div>}
                        {e.email_body && (
                          <div className="email-preview" style={{ marginTop: e.sms_body ? '1rem' : 0 }}>
                            <div className="subject">{e.email_subject}</div>
                            <div style={{ whiteSpace: 'pre-wrap' }}>{e.email_body}</div>
                          </div>
                        )}
                        {e.block_reason && (
                          <div className="ambiguity-warning" style={{ marginTop: 0 }}>
                            <strong>Blocked:</strong> {e.block_reason}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
