import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Wand2, AlertTriangle } from 'lucide-react';
import { api } from '../api';
import type { FieldDef, ParsedDraft } from '../types';

const EXAMPLE =
  "When a Gold or Platinum member's flight is delayed more than 60 minutes, text them a lounge-access offer";

export default function Builder() {
  const navigate = useNavigate();
  const [text, setText] = useState('');
  const [draft, setDraft] = useState<ParsedDraft | null>(null);
  const [fields, setFields] = useState<FieldDef[]>([]);
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    api.listFields().then((r) => setFields(r.fields)).catch(console.error);
  }, []);

  const handleParse = async () => {
    if (!text.trim()) return;
    setParsing(true);
    try {
      const result = await api.parseTrigger(text);
      setDraft(result);
    } catch (e) {
      console.error(e);
    } finally {
      setParsing(false);
    }
  };

  const handleSave = async (activate: boolean) => {
    if (!draft) return;
    setSaving(true);
    try {
      const trigger = await api.createTrigger(draft, activate);
      navigate(`/triggers/${trigger.trigger_id}`);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleTextChange = (val: string) => {
    setText(val);
    const atMatch = val.match(/@(\w*)$/);
    if (atMatch) {
      setShowAutocomplete(true);
      setFilter(atMatch[1].toLowerCase());
    } else {
      setShowAutocomplete(false);
    }
  };

  const insertField = (field: string) => {
    const newText = text.replace(/@\w*$/, `@${field} `);
    setText(newText);
    setShowAutocomplete(false);
  };

  const filteredFields = fields.filter(
    (f) => !filter || f.field.includes(filter) || f.description.toLowerCase().includes(filter)
  );

  return (
    <>
      <div className="page-header">
        <h2>Trigger Builder</h2>
        <p>Describe a trigger in plain language — the system parses it into structured conditions.</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="form-group field-autocomplete">
            <label>Describe your trigger</label>
            <textarea
              value={text}
              onChange={(e) => handleTextChange(e.target.value)}
              placeholder={EXAMPLE}
            />
            {showAutocomplete && filteredFields.length > 0 && (
              <div className="autocomplete-dropdown">
                {filteredFields.slice(0, 8).map((f) => (
                  <div key={f.field} className="autocomplete-item" onClick={() => insertField(f.field)}>
                    <code>@{f.field}</code> — {f.description}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="actions-row">
            <button className="btn btn-primary" onClick={handleParse} disabled={parsing || !text.trim()}>
              <Wand2 size={16} /> {parsing ? 'Parsing…' : 'Parse Trigger'}
            </button>
            <button className="btn btn-secondary" onClick={() => setText(EXAMPLE)}>
              Load example
            </button>
          </div>
        </div>

        <div className="card">
          {!draft ? (
            <div className="empty-state">
              <Wand2 size={32} style={{ opacity: 0.3, marginBottom: '0.75rem' }} />
              <p>Parse a trigger description to see the structured preview.</p>
            </div>
          ) : (
            <>
              <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Parsed Preview — editable before save</h3>

              <div className="form-group">
                <label>Name</label>
                <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Lifecycle Phase</label>
                <input value={draft.lifecycle_phase} onChange={(e) => setDraft({ ...draft, lifecycle_phase: e.target.value })} />
              </div>
              <div className="form-group">
                <label>NBA / Offer</label>
                <input value={draft.nba_offer} onChange={(e) => setDraft({ ...draft, nba_offer: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select
                  value={draft.priority_tier}
                  onChange={(e) => setDraft({ ...draft, priority_tier: e.target.value as ParsedDraft['priority_tier'] })}
                >
                  <option value="Commercial">Commercial</option>
                  <option value="Operational">Operational</option>
                </select>
              </div>
              <div className="form-group">
                <label>Channel</label>
                <select
                  value={draft.suggested_channel}
                  onChange={(e) => setDraft({ ...draft, suggested_channel: e.target.value as ParsedDraft['suggested_channel'] })}
                >
                  <option value="SMS">SMS</option>
                  <option value="Email">Email</option>
                  <option value="SMS if opted in, else Email">SMS if opted in, else Email</option>
                </select>
              </div>

              <div className="detail-section">
                <h3>Structured Conditions</h3>
                <ul className="clause-list">
                  {draft.condition_structured.clauses.map((c, i) => (
                    <li key={i}>
                      <strong>{c.field}</strong> {c.operator} {JSON.stringify(c.value)}
                      <br /><span style={{ color: 'var(--text-muted)' }}>{c.description}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {draft.ambiguities.length > 0 && (
                <div className="ambiguity-warning">
                  <h4><AlertTriangle size={14} style={{ display: 'inline', marginRight: 4 }} /> Ambiguities detected</h4>
                  <ul>
                    {draft.ambiguities.map((a, i) => <li key={i}>{a}</li>)}
                  </ul>
                </div>
              )}

              <div className="actions-row" style={{ marginTop: '1.25rem' }}>
                <button className="btn btn-secondary" onClick={() => handleSave(false)} disabled={saving}>
                  Save as Draft
                </button>
                <button className="btn btn-primary" onClick={() => handleSave(true)} disabled={saving || draft.ambiguities.length > 0}>
                  Activate Trigger
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
