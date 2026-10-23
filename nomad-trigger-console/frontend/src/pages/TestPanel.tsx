import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle, XCircle, ShieldAlert, Shuffle, Users } from 'lucide-react';
import { api } from '../api';
import type { BatchSummary, GoldenRecord, TestResult, Trigger } from '../types';

function VerdictBadge({ verdict }: { verdict: string }) {
  const cls = verdict === 'Pass' ? 'badge-pass' : verdict === 'Blocked' ? 'badge-blocked' : 'badge-fail';
  return <span className={`badge ${cls}`}>{verdict}</span>;
}

export default function TestPanel() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [trigger, setTrigger] = useState<Trigger | null>(null);
  const [profiles, setProfiles] = useState<GoldenRecord[]>([]);
  const [qualifying, setQualifying] = useState<GoldenRecord[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [result, setResult] = useState<TestResult | null>(null);
  const [batch, setBatch] = useState<BatchSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('');

  useEffect(() => {
    if (!id) return;
    api.getTrigger(id).then((r) => setTrigger(r.trigger)).catch(console.error);
    api.getQualifying(id).then((r) => setQualifying(r.profiles)).catch(console.error);
  }, [id]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search) params.search = search;
    if (tierFilter) params.tier = tierFilter;
    api.listProfiles(params).then((r) => setProfiles(r.profiles)).catch(console.error);
  }, [search, tierFilter]);

  const runTest = async () => {
    if (!id || !selectedId) return;
    setLoading(true);
    setBatch(null);
    try {
      const r = await api.testTrigger(id, selectedId);
      setResult(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const pickRandomQualifying = () => {
    if (qualifying.length === 0) return;
    const pick = qualifying[Math.floor(Math.random() * qualifying.length)];
    setSelectedId(pick.account_id);
  };

  const runBatch = async () => {
    if (!id) return;
    setLoading(true);
    setResult(null);
    try {
      const summary = await api.batchTest(id);
      setBatch(summary);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <Link to={`/triggers/${id}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          <ArrowLeft size={14} /> Back to Detail
        </Link>
        <h2>Test / Simulate — {trigger?.name || id}</h2>
        <p>Evaluate this trigger against a golden record and preview generated message copy.</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="detail-section">
            <h3>Select Profile ({profiles.length} available)</h3>
            <div className="filters" style={{ marginBottom: '0.75rem' }}>
              <input placeholder="Search by name or destination…" value={search} onChange={(e) => setSearch(e.target.value)} />
              <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value)}>
                <option value="">All tiers</option>
                <option value="Blue">Blue</option>
                <option value="Silver">Silver</option>
                <option value="Gold">Gold</option>
                <option value="Platinum">Platinum</option>
              </select>
            </div>
            <div className="profile-picker">
              {profiles.map((p) => (
                <div
                  key={p.account_id}
                  className={`profile-option${selectedId === p.account_id ? ' selected' : ''}`}
                  onClick={() => setSelectedId(p.account_id)}
                >
                  <span>
                    <strong>{p.display_first_name}</strong>{' '}
                    <span style={{ color: 'var(--text-muted)' }}>
                      {p.one_key_tier} · {p.travel_archetype}
                    </span>
                  </span>
                  <code style={{ fontSize: '0.6875rem' }}>{p.account_id.slice(0, 8)}…</code>
                </div>
              ))}
            </div>
          </div>

          <div className="actions-row" style={{ marginTop: '1rem' }}>
            <button className="btn btn-secondary btn-sm" onClick={pickRandomQualifying} disabled={qualifying.length === 0}>
              <Shuffle size={14} /> Random qualifying ({qualifying.length})
            </button>
            <button className="btn btn-primary" onClick={runTest} disabled={!selectedId || loading}>
              Run Test
            </button>
            <button className="btn btn-secondary" onClick={runBatch} disabled={loading}>
              <Users size={14} /> Test all 100 profiles
            </button>
          </div>
        </div>

        <div className="card">
          {batch && (
            <>
              <h3 style={{ marginBottom: '1rem' }}>Batch Test Summary</h3>
              <div className="stats-row">
                <div className="stat-card pass"><div className="value">{batch.pass_count}</div><div className="label">Pass</div></div>
                <div className="stat-card fail"><div className="value">{batch.fail_count}</div><div className="label">Fail</div></div>
                <div className="stat-card blocked"><div className="value">{batch.blocked_count}</div><div className="label">Blocked</div></div>
              </div>
            </>
          )}

          {!result && !batch && (
            <div className="empty-state">
              <p>Select a profile and run a test to see results.</p>
            </div>
          )}

          {result && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <VerdictBadge verdict={result.verdict} />
                <span style={{ fontSize: '0.875rem' }}>
                  {result.profile_first_name} · {new Date(result.timestamp).toLocaleString()}
                </span>
              </div>

              <div className="detail-section">
                <h3>Condition Evaluation</h3>
                {result.field_evaluations.map((ev, i) => (
                  <div key={i} className="eval-row">
                    {ev.passed ? (
                      <CheckCircle size={16} className="eval-icon pass" />
                    ) : (
                      <XCircle size={16} className="eval-icon fail" />
                    )}
                    <span><strong>{ev.field}</strong> — expected {ev.expected}, got {ev.actual}</span>
                  </div>
                ))}
              </div>

              {result.verdict === 'Blocked' && (
                <div className="ambiguity-warning">
                  <h4><ShieldAlert size={14} style={{ display: 'inline', marginRight: 4 }} /> Guardrail Blocked</h4>
                  <p>{result.block_reason}</p>
                </div>
              )}

              {result.verdict === 'Pass' && (
                <>
                  <div className="detail-section">
                    <h3>Channel Selection</h3>
                    <p>
                      <span className={`badge badge-${result.selected_channel?.toLowerCase()}`}>{result.selected_channel}</span>{' '}
                      {result.channel_reason}
                    </p>
                  </div>

                  <div className="detail-section">
                    <h3>Generated Message</h3>
                    {result.sms_body && <div className="sms-preview">{result.sms_body}</div>}
                    {result.email_body && (
                      <div className="email-preview">
                        <div className="subject">{result.email_subject}</div>
                        <div style={{ whiteSpace: 'pre-wrap' }}>{result.email_body}</div>
                      </div>
                    )}
                  </div>
                </>
              )}

              <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '1rem' }}>
                {result.explanation}
              </p>

              <button
                className="btn btn-secondary btn-sm"
                style={{ marginTop: '1rem' }}
                onClick={() => navigate('/queue')}
              >
                View in Message Queue →
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
