import { useState } from 'react';
import Markdown from 'react-markdown';
import './SummaryCard.css';

function SummaryCard({ summary, onRegenerate, isProcessing }) {
  const [expandedSections, setExpandedSections] = useState({
    executive_summary: true,
    key_facts: false,
    timeline: false,
    core_issues: false,
    parties_involved: false,
    evidence: false,
    recommended_actions: false
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Parse JSON if it's a string
  let parsedSummary;
  try {
    parsedSummary = typeof summary === 'string' ? JSON.parse(summary) : summary;
  } catch (e) {
    // If parsing fails, it's the old markdown format
    return (
      <div className="summary-card legacy-format">
        <div className="summary-header">
          <h3>AI-Generated Summary</h3>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="btn btn-sm btn-secondary"
              disabled={isProcessing}
            >
              🔄 Regenerate
            </button>
          )}
        </div>
        <div className="summary-content">
          <Markdown>{summary}</Markdown>
        </div>
      </div>
    );
  }

  const getSeverityBadge = (severity) => {
    const colors = {
      low: 'badge-green',
      medium: 'badge-yellow',
      high: 'badge-orange',
      critical: 'badge-red'
    };
    return <span className={`badge ${colors[severity] || 'badge-gray'}`}>{severity?.toUpperCase()}</span>;
  };

  const getSentimentBadge = (sentiment) => {
    const colors = {
      positive: 'badge-green',
      neutral: 'badge-gray',
      negative: 'badge-orange',
      critical: 'badge-red'
    };
    return <span className={`badge ${colors[sentiment] || 'badge-gray'}`}>{sentiment?.toUpperCase()}</span>;
  };

  return (
    <div className="summary-card">
      <div className="summary-header-main">
        <div className="summary-title">
          <h3>AI-Generated Summary</h3>
        </div>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="btn btn-sm btn-secondary"
            disabled={isProcessing}
          >
            🔄 Regenerate
          </button>
        )}
      </div>

      {/* Top Summary Header */}
      <div className="summary-metadata">
        <div className="metadata-grid">
          <div className="metadata-item">
            <label>Category</label>
            <span className="badge badge-blue">{parsedSummary.category || 'Unknown'}</span>
          </div>
          <div className="metadata-item">
            <label>Sentiment</label>
            {getSentimentBadge(parsedSummary.sentiment)}
          </div>
          <div className="metadata-item">
            <label>Severity</label>
            {getSeverityBadge(parsedSummary.severity)}
          </div>
          <div className="metadata-item">
            <label>Responsible Team</label>
            <span className="team-badge">{parsedSummary.responsible_team || 'Unassigned'}</span>
          </div>
        </div>
      </div>

      {/* Collapsible Sections */}
      <div className="summary-sections">
        {/* Executive Summary - Always visible by default */}
        <div className="summary-section">
          <div
            className="section-header"
            onClick={() => toggleSection('executive_summary')}
          >
            <h4>Executive Summary</h4>
            <span className="toggle-icon">{expandedSections.executive_summary ? '▼' : '▶'}</span>
          </div>
          {expandedSections.executive_summary && (
            <div className="section-content">
              <p>{parsedSummary.executive_summary}</p>
            </div>
          )}
        </div>

        {/* Key Facts */}
        {parsedSummary.key_facts && parsedSummary.key_facts.length > 0 && (
          <div className="summary-section">
            <div
              className="section-header"
              onClick={() => toggleSection('key_facts')}
            >
              <h4>Key Facts</h4>
              <span className="toggle-icon">{expandedSections.key_facts ? '▼' : '▶'}</span>
            </div>
            {expandedSections.key_facts && (
              <div className="section-content">
                <ul>
                  {parsedSummary.key_facts.map((fact, idx) => {
                    // Handle both old format (string) and new format (object with source)
                    if (typeof fact === 'string') {
                      return <li key={idx}><Markdown>{fact}</Markdown></li>;
                    }
                    return (
                      <li key={idx} className="fact-with-source">
                        <div className="fact-text">
                          <Markdown>{fact.fact}</Markdown>
                        </div>
                        {fact.source && (
                          <div className="source-reference">
                            <span className="source-icon">📄</span>
                            <div className="source-details">
                              <div className="source-filename">{fact.source}</div>
                              {fact.context && (
                                <div className="source-context">"{fact.context}"</div>
                              )}
                            </div>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Timeline */}
        {parsedSummary.timeline && parsedSummary.timeline.length > 0 && (
          <div className="summary-section">
            <div
              className="section-header"
              onClick={() => toggleSection('timeline')}
            >
              <h4>Timeline of Events</h4>
              <span className="toggle-icon">{expandedSections.timeline ? '▼' : '▶'}</span>
            </div>
            {expandedSections.timeline && (
              <div className="section-content">
                <ul className="timeline-list">
                  {parsedSummary.timeline.map((event, idx) => {
                    // Handle both old format (string) and new format (object with source)
                    if (typeof event === 'string') {
                      return <li key={idx}><Markdown>{event}</Markdown></li>;
                    }
                    return (
                      <li key={idx} className="fact-with-source">
                        <div className="fact-text">
                          <Markdown>{event.event}</Markdown>
                        </div>
                        {event.source && (
                          <div className="source-reference">
                            <span className="source-icon">📄</span>
                            <div className="source-details">
                              <div className="source-filename">{event.source}</div>
                              {event.context && (
                                <div className="source-context">"{event.context}"</div>
                              )}
                            </div>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Core Issues */}
        {parsedSummary.core_issues && parsedSummary.core_issues.length > 0 && (
          <div className="summary-section">
            <div
              className="section-header"
              onClick={() => toggleSection('core_issues')}
            >
              <h4>Core Issues</h4>
              <span className="toggle-icon">{expandedSections.core_issues ? '▼' : '▶'}</span>
            </div>
            {expandedSections.core_issues && (
              <div className="section-content">
                <ul>
                  {parsedSummary.core_issues.map((issue, idx) => {
                    // Handle both old format (string) and new format (object with source)
                    if (typeof issue === 'string') {
                      return <li key={idx}><Markdown>{issue}</Markdown></li>;
                    }
                    return (
                      <li key={idx} className="fact-with-source">
                        <div className="fact-text">
                          <Markdown>{issue.issue}</Markdown>
                        </div>
                        {issue.source && (
                          <div className="source-reference">
                            <span className="source-icon">📄</span>
                            <div className="source-details">
                              <div className="source-filename">{issue.source}</div>
                              {issue.context && (
                                <div className="source-context">"{issue.context}"</div>
                              )}
                            </div>
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Parties Involved */}
        {parsedSummary.parties_involved && parsedSummary.parties_involved.length > 0 && (
          <div className="summary-section">
            <div
              className="section-header"
              onClick={() => toggleSection('parties_involved')}
            >
              <h4>Parties Involved</h4>
              <span className="toggle-icon">{expandedSections.parties_involved ? '▼' : '▶'}</span>
            </div>
            {expandedSections.parties_involved && (
              <div className="section-content">
                <ul>
                  {parsedSummary.parties_involved.map((party, idx) => (
                    <li key={idx}><Markdown>{party}</Markdown></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Evidence */}
        {parsedSummary.evidence && parsedSummary.evidence.length > 0 && (
          <div className="summary-section">
            <div
              className="section-header"
              onClick={() => toggleSection('evidence')}
            >
              <h4>Evidence Summary</h4>
              <span className="toggle-icon">{expandedSections.evidence ? '▼' : '▶'}</span>
            </div>
            {expandedSections.evidence && (
              <div className="section-content">
                <ul>
                  {parsedSummary.evidence.map((item, idx) => (
                    <li key={idx}><Markdown>{item}</Markdown></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Recommended Actions */}
        {parsedSummary.recommended_actions && parsedSummary.recommended_actions.length > 0 && (
          <div className="summary-section highlight">
            <div
              className="section-header"
              onClick={() => toggleSection('recommended_actions')}
            >
              <h4>Recommended Actions</h4>
              <span className="toggle-icon">{expandedSections.recommended_actions ? '▼' : '▶'}</span>
            </div>
            {expandedSections.recommended_actions && (
              <div className="section-content">
                <ul>
                  {parsedSummary.recommended_actions.map((action, idx) => (
                    <li key={idx}><Markdown>{action}</Markdown></li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SummaryCard;
