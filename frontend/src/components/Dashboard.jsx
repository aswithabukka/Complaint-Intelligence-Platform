import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getComplaints } from '../services/api';
import './Dashboard.css';

function Dashboard() {
  const [complaints, setComplaints] = useState([]);
  const [filteredComplaints, setFilteredComplaints] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    pending_action: 0,
    in_progress: 0,
    resolved: 0,
    failed: 0,
    processing: 0,
    byCategory: {},
    bySeverity: {},
    byTeam: {},
  });
  const [urgentComplaints, setUrgentComplaints] = useState([]);
  const [overdueComplaints, setOverdueComplaints] = useState([]);
  const [recurringIssues, setRecurringIssues] = useState([]);
  const [filters, setFilters] = useState({
    status: 'all',
    severity: 'all',
    category: 'all',
    team: 'all',
  });
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('darkMode') === 'true';
  });
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // Apply dark mode
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark-mode');
      document.body.classList.add('dark-mode');
    } else {
      document.documentElement.classList.remove('dark-mode');
      document.body.classList.remove('dark-mode');
    }
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const data = await getComplaints(1, 100);
      setComplaints(data.items);
      setFilteredComplaints(data.items);
      calculateStats(data.items);
      calculateUrgentComplaints(data.items);
      calculateOverdueComplaints(data.items);
      calculateRecurringIssues(data.items);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch complaints:', err);
      setLoading(false);
    }
  };

  // Apply filters whenever complaints or filters change
  useEffect(() => {
    let filtered = [...complaints];

    // Filter by status
    if (filters.status !== 'all') {
      filtered = filtered.filter(c => c.status === filters.status);
    }

    // Filter by severity, category, team (from summary)
    if (filters.severity !== 'all' || filters.category !== 'all' || filters.team !== 'all') {
      filtered = filtered.filter(complaint => {
        if (!complaint.overall_summary) return false;

        try {
          const summary = JSON.parse(complaint.overall_summary);

          if (filters.severity !== 'all' && summary.severity !== filters.severity) {
            return false;
          }
          if (filters.category !== 'all' && summary.category !== filters.category) {
            return false;
          }
          if (filters.team !== 'all' && summary.responsible_team !== filters.team) {
            return false;
          }

          return true;
        } catch (e) {
          return false;
        }
      });
    }

    setFilteredComplaints(filtered);
  }, [complaints, filters]);

  const calculateStats = (items) => {
    const stats = {
      total: items.length,
      pending_action: 0,
      in_progress: 0,
      resolved: 0,
      failed: 0,
      processing: 0,
      byCategory: {},
      bySeverity: {},
      byTeam: {},
    };

    items.forEach((complaint) => {
      // Count by status
      if (complaint.status === 'pending_action') stats.pending_action++;
      else if (complaint.status === 'in_progress') stats.in_progress++;
      else if (complaint.status === 'resolved') stats.resolved++;
      else if (complaint.status === 'failed') stats.failed++;
      else if (['processing', 'summarizing'].includes(complaint.status)) stats.processing++;

      // Parse summary for category/severity/team
      if (complaint.overall_summary) {
        try {
          const summary = JSON.parse(complaint.overall_summary);

          // By category
          const category = summary.category || 'Unknown';
          stats.byCategory[category] = (stats.byCategory[category] || 0) + 1;

          // By severity
          const severity = summary.severity || 'unknown';
          stats.bySeverity[severity] = (stats.bySeverity[severity] || 0) + 1;

          // By team
          const team = summary.responsible_team || 'Unassigned';
          stats.byTeam[team] = (stats.byTeam[team] || 0) + 1;
        } catch (e) {
          // Old format or invalid JSON
        }
      }
    });

    setStats(stats);
  };

  const calculateUrgentComplaints = (items) => {
    // Multi-criteria urgency scoring system
    const now = new Date();
    const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);

    const scored = items
      .filter(complaint => !['resolved', 'completed'].includes(complaint.status))
      .map(complaint => {
        let urgencyScore = 0;
        let summary = null;

        // Try to parse summary
        if (complaint.overall_summary) {
          try {
            summary = JSON.parse(complaint.overall_summary);
          } catch (e) {
            // Ignore parse errors
          }
        }

        // Score by severity (AI-determined)
        if (summary) {
          if (summary.severity === 'critical') urgencyScore += 100;
          else if (summary.severity === 'high') urgencyScore += 50;
          else if (summary.severity === 'medium') urgencyScore += 20;

          // Score by sentiment
          if (summary.sentiment === 'critical') urgencyScore += 30;
          else if (summary.sentiment === 'negative') urgencyScore += 10;
        }

        // Score by status - pending_action needs immediate attention
        if (complaint.status === 'pending_action') urgencyScore += 40;
        else if (complaint.status === 'pending') urgencyScore += 20;

        // Score by age - old pending complaints are urgent
        const ageInDays = (now - new Date(complaint.created_at)) / (1000 * 60 * 60 * 24);
        if (complaint.status === 'pending' && ageInDays > 1) {
          urgencyScore += Math.min(ageInDays * 15, 60); // Up to 60 points for old pending
        }

        // Unprocessed complaints older than 24 hours are urgent
        if (!summary && new Date(complaint.created_at) < oneDayAgo) {
          urgencyScore += 35;
        }

        return { complaint, urgencyScore, summary };
      })
      .filter(item => item.urgencyScore > 0)
      .sort((a, b) => b.urgencyScore - a.urgencyScore)
      .slice(0, 10);

    setUrgentComplaints(scored.map(item => item.complaint));
  };

  const calculateOverdueComplaints = (items) => {
    // Dynamic SLA based on severity and status
    const now = new Date();

    // SLA thresholds in hours
    const SLA_BY_SEVERITY = {
      critical: 24,      // 24 hours
      high: 72,          // 3 days
      medium: 168,       // 7 days
      low: 336,          // 14 days
      default: 168       // 7 days for unknown severity
    };

    const SLA_BY_STATUS = {
      pending: 48,           // 2 days to start processing
      pending_action: 48,    // 2 days to take action
      in_progress: 120,      // 5 days to resolve
      default: 168           // 7 days default
    };

    const overdue = items
      .filter(complaint => {
        if (['resolved', 'completed'].includes(complaint.status)) return false;

        const createdAt = new Date(complaint.created_at);
        const ageInHours = (now - createdAt) / (1000 * 60 * 60);

        // Determine SLA threshold
        let slaThreshold = SLA_BY_STATUS.default;

        // First priority: SLA by severity if we have AI summary
        if (complaint.overall_summary) {
          try {
            const summary = JSON.parse(complaint.overall_summary);
            slaThreshold = SLA_BY_SEVERITY[summary.severity] || SLA_BY_SEVERITY.default;
          } catch (e) {
            // If no summary, use status-based SLA
            slaThreshold = SLA_BY_STATUS[complaint.status] || SLA_BY_STATUS.default;
          }
        } else {
          // No summary yet, use status-based SLA
          slaThreshold = SLA_BY_STATUS[complaint.status] || SLA_BY_STATUS.default;
        }

        return ageInHours > slaThreshold;
      })
      .map(complaint => {
        const createdAt = new Date(complaint.created_at);
        const ageInHours = (now - createdAt) / (1000 * 60 * 60);
        let slaThreshold = SLA_BY_STATUS.default;

        if (complaint.overall_summary) {
          try {
            const summary = JSON.parse(complaint.overall_summary);
            slaThreshold = SLA_BY_SEVERITY[summary.severity] || SLA_BY_SEVERITY.default;
          } catch (e) {
            slaThreshold = SLA_BY_STATUS[complaint.status] || SLA_BY_STATUS.default;
          }
        } else {
          slaThreshold = SLA_BY_STATUS[complaint.status] || SLA_BY_STATUS.default;
        }

        const overdueHours = ageInHours - slaThreshold;
        return { ...complaint, overdueHours };
      })
      .sort((a, b) => b.overdueHours - a.overdueHours) // Most overdue first
      .slice(0, 10);

    setOverdueComplaints(overdue);
  };

  const calculateRecurringIssues = (items) => {
    // Enhanced recurring issue detection with team-based grouping
    const now = new Date();
    const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const fourteenDaysAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);

    // Get recent complaints (last 7 days)
    const recentComplaints = items.filter(
      complaint => new Date(complaint.created_at) > sevenDaysAgo
    );

    // Get previous week complaints for trend comparison
    const previousWeekComplaints = items.filter(
      complaint => {
        const createdAt = new Date(complaint.created_at);
        return createdAt > fourteenDaysAgo && createdAt <= sevenDaysAgo;
      }
    );

    // Group by category + team combination for better pattern detection
    const categoryTeamCounts = {};
    const categoryTeamDetails = {};

    recentComplaints.forEach(complaint => {
      if (complaint.overall_summary) {
        try {
          const summary = JSON.parse(complaint.overall_summary);
          const category = summary.category || 'Unknown';
          const team = summary.responsible_team || 'Unassigned';
          const key = `${category}|${team}`;

          if (!categoryTeamCounts[key]) {
            categoryTeamCounts[key] = 0;
            categoryTeamDetails[key] = { category, team, complaints: [] };
          }
          categoryTeamCounts[key]++;
          categoryTeamDetails[key].complaints.push(complaint);
        } catch (e) {
          // Ignore parse errors
        }
      }
    });

    // Count previous week for trend
    const previousWeekCounts = {};
    previousWeekComplaints.forEach(complaint => {
      if (complaint.overall_summary) {
        try {
          const summary = JSON.parse(complaint.overall_summary);
          const category = summary.category || 'Unknown';
          const team = summary.responsible_team || 'Unassigned';
          const key = `${category}|${team}`;
          previousWeekCounts[key] = (previousWeekCounts[key] || 0) + 1;
        } catch (e) {
          // Ignore
        }
      }
    });

    // Calculate recurring issues with trend
    const recurring = Object.entries(categoryTeamCounts)
      .filter(([, count]) => count >= 2) // 2+ complaints = recurring
      .map(([key, count]) => {
        const details = categoryTeamDetails[key];
        const previousCount = previousWeekCounts[key] || 0;
        const trend = count - previousCount; // Positive = increasing, negative = decreasing

        // Calculate resolution rate for this category+team
        const resolved = details.complaints.filter(
          c => ['resolved', 'completed'].includes(c.status)
        ).length;
        const resolutionRate = details.complaints.length > 0
          ? Math.round((resolved / details.complaints.length) * 100)
          : 0;

        return {
          category: details.category,
          team: details.team,
          count,
          trend,
          resolutionRate,
          severity: details.complaints.length >= 5 ? 'critical' :
                    details.complaints.length >= 3 ? 'high' : 'medium'
        };
      })
      .sort((a, b) => {
        // Sort by: 1) count (descending), 2) trend (ascending - worse trends first)
        if (b.count !== a.count) return b.count - a.count;
        return b.trend - a.trend;
      });

    setRecurringIssues(recurring);
  };

  const getSeverityColor = (severity) => {
    const colors = {
      low: '#10b981',
      medium: '#f59e0b',
      high: '#f97316',
      critical: '#ef4444',
    };
    return colors[severity] || '#6b7280';
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#6b7280',
      processing: '#3b82f6',
      summarizing: '#8b5cf6',
      pending_action: '#f59e0b',
      in_progress: '#3b82f6',
      resolved: '#10b981',
      completed: '#10b981',
      failed: '#ef4444',
    };
    return colors[status] || '#6b7280';
  };

  const formatStatus = (status) => {
    return status.replace('_', ' ').toUpperCase();
  };

  if (loading) {
    return <div className="loading-dashboard">Loading dashboard...</div>;
  }

  return (
    <div className="dashboard">
      {/* Header with action buttons */}
      <div className="dashboard-header">
        <div>
          <h1>Complaint Intelligence Dashboard</h1>
          <p className="dashboard-subtitle">Overview of all complaints and their processing status</p>
        </div>
        <div className="header-actions">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="btn btn-secondary"
            title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
          <button onClick={() => navigate('/create')} className="btn btn-primary btn-lg">
            + New Complaint
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon" style={{ background: '#3b82f6' }}>📊</div>
          <div className="metric-content">
            <div className="metric-label">Total Complaints</div>
            <div className="metric-value">{stats.total}</div>
          </div>
        </div>

        <div className="metric-card clickable" onClick={() => navigate('/')}>
          <div className="metric-icon" style={{ background: '#f59e0b' }}>⏳</div>
          <div className="metric-content">
            <div className="metric-label">Pending Action</div>
            <div className="metric-value">{stats.pending_action}</div>
            <div className="metric-detail">{((stats.pending_action / stats.total) * 100 || 0).toFixed(1)}% of total</div>
          </div>
        </div>

        <div className="metric-card clickable">
          <div className="metric-icon" style={{ background: '#3b82f6' }}>🔄</div>
          <div className="metric-content">
            <div className="metric-label">In Progress</div>
            <div className="metric-value">{stats.in_progress}</div>
            <div className="metric-detail">{((stats.in_progress / stats.total) * 100 || 0).toFixed(1)}% of total</div>
          </div>
        </div>

        <div className="metric-card clickable">
          <div className="metric-icon" style={{ background: '#10b981' }}>✅</div>
          <div className="metric-content">
            <div className="metric-label">Resolved</div>
            <div className="metric-value">{stats.resolved}</div>
            <div className="metric-detail">{((stats.resolved / stats.total) * 100 || 0).toFixed(1)}% resolution rate</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon" style={{ background: '#8b5cf6' }}>⚙️</div>
          <div className="metric-content">
            <div className="metric-label">Processing</div>
            <div className="metric-value">{stats.processing}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon" style={{ background: '#ef4444' }}>❌</div>
          <div className="metric-content">
            <div className="metric-label">Failed</div>
            <div className="metric-value">{stats.failed}</div>
          </div>
        </div>
      </div>

      {/* Analytics Charts */}
      <div className="analytics-grid">
        {/* By Category */}
        <div className="analytics-card">
          <h3>Complaints by Category</h3>
          <div className="chart-container">
            {Object.entries(stats.byCategory).length > 0 ? (
              Object.entries(stats.byCategory)
                .sort(([, a], [, b]) => b - a)
                .map(([category, count]) => (
                  <div key={category} className="chart-bar-row">
                    <div className="chart-label">{category}</div>
                    <div className="chart-bar-container">
                      <div
                        className="chart-bar"
                        style={{
                          width: `${(count / stats.total) * 100}%`,
                          background: '#3b82f6',
                        }}
                      >
                        <span className="chart-bar-value">{count}</span>
                      </div>
                    </div>
                  </div>
                ))
            ) : (
              <div className="empty-chart">No categorized complaints yet</div>
            )}
          </div>
        </div>

        {/* By Severity */}
        <div className="analytics-card">
          <h3>Complaints by Severity</h3>
          <div className="chart-container">
            {Object.entries(stats.bySeverity).length > 0 ? (
              ['critical', 'high', 'medium', 'low']
                .filter((severity) => stats.bySeverity[severity])
                .map((severity) => (
                  <div key={severity} className="chart-bar-row">
                    <div className="chart-label">{severity.toUpperCase()}</div>
                    <div className="chart-bar-container">
                      <div
                        className="chart-bar"
                        style={{
                          width: `${(stats.bySeverity[severity] / stats.total) * 100}%`,
                          background: getSeverityColor(severity),
                        }}
                      >
                        <span className="chart-bar-value">{stats.bySeverity[severity]}</span>
                      </div>
                    </div>
                  </div>
                ))
            ) : (
              <div className="empty-chart">No severity data available</div>
            )}
          </div>
        </div>

        {/* By Team */}
        <div className="analytics-card analytics-card-wide">
          <h3>Complaints by Responsible Team</h3>
          <div className="chart-container">
            {Object.entries(stats.byTeam).length > 0 ? (
              Object.entries(stats.byTeam)
                .sort(([, a], [, b]) => b - a)
                .map(([team, count]) => (
                  <div key={team} className="chart-bar-row">
                    <div className="chart-label">{team}</div>
                    <div className="chart-bar-container">
                      <div
                        className="chart-bar"
                        style={{
                          width: `${(count / stats.total) * 100}%`,
                          background: '#8b5cf6',
                        }}
                      >
                        <span className="chart-bar-value">{count}</span>
                      </div>
                    </div>
                  </div>
                ))
            ) : (
              <div className="empty-chart">No team assignments yet</div>
            )}
          </div>
        </div>
      </div>

      {/* New Alert Sections */}
      <div className="analytics-grid">
        {/* Top 10 Urgent Complaints */}
        <div className="analytics-card">
          <h3>🚨 Top 10 Urgent Complaints</h3>
          <div className="urgent-list">
            {urgentComplaints.length > 0 ? (
              urgentComplaints.map((complaint) => {
                let summary = null;
                try {
                  summary = JSON.parse(complaint.overall_summary);
                } catch (e) {
                  // Ignore
                }

                return (
                  <div
                    key={complaint.id}
                    className="urgent-item"
                    onClick={() => navigate(`/complaints/${complaint.id}`)}
                  >
                    <div className="urgent-header">
                      <span className="urgent-title">{complaint.title}</span>
                      {summary && (
                        <span className={`severity-badge severity-${summary.severity}`}>
                          {summary.severity?.toUpperCase()}
                        </span>
                      )}
                    </div>
                    {summary && (
                      <div className="urgent-category">{summary.category}</div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="empty-chart">No urgent complaints</div>
            )}
          </div>
        </div>

        {/* Overdue SLA Complaints */}
        <div className="analytics-card">
          <h3>⏰ Overdue SLA Complaints</h3>
          <div className="urgent-list">
            {overdueComplaints.length > 0 ? (
              overdueComplaints.map((complaint) => {
                // Format overdue time
                const overdueHours = complaint.overdueHours || 0;
                let overdueText = '';
                if (overdueHours >= 24) {
                  const days = Math.floor(overdueHours / 24);
                  overdueText = `${days}d overdue`;
                } else {
                  overdueText = `${Math.floor(overdueHours)}h overdue`;
                }

                // Get severity badge if available
                let summary = null;
                try {
                  if (complaint.overall_summary) {
                    summary = JSON.parse(complaint.overall_summary);
                  }
                } catch (e) {
                  // Ignore
                }

                return (
                  <div
                    key={complaint.id}
                    className="urgent-item"
                    onClick={() => navigate(`/complaints/${complaint.id}`)}
                  >
                    <div className="urgent-header">
                      <span className="urgent-title">{complaint.title}</span>
                      <span className="overdue-badge">{overdueText}</span>
                    </div>
                    <div className="urgent-category">
                      {summary ? `${summary.category} • ${summary.severity}` : complaint.status}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-chart">No overdue complaints</div>
            )}
          </div>
        </div>

        {/* Recurring Issues This Week */}
        <div className="analytics-card">
          <h3>🔄 Recurring Issues This Week</h3>
          <div className="chart-container">
            {recurringIssues.length > 0 ? (
              recurringIssues.map(({ category, team, count, trend, resolutionRate, severity }) => {
                const maxCount = Math.max(...recurringIssues.map(i => i.count));
                const barColor = severity === 'critical' ? '#ef4444' :
                                 severity === 'high' ? '#f97316' : '#f59e0b';

                return (
                  <div key={`${category}-${team}`} className="chart-bar-row">
                    <div className="chart-label">
                      <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{category}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{team}</div>
                    </div>
                    <div className="chart-bar-container">
                      <div
                        className="chart-bar"
                        style={{
                          width: `${(count / maxCount) * 100}%`,
                          background: barColor,
                        }}
                      >
                        <span className="chart-bar-value">
                          {count} cases
                          {trend > 0 && ` ↑${trend}`}
                          {trend < 0 && ` ↓${Math.abs(trend)}`}
                          {resolutionRate < 50 && ` • ${resolutionRate}% resolved`}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-chart">No recurring issues detected</div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Complaints Table */}
      <div className="recent-complaints">
        <div className="section-header">
          <h2>Recent Complaints</h2>
          <button onClick={() => navigate('/')} className="btn btn-secondary">
            View All
          </button>
        </div>

        <div className="complaints-table">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>
                  <div className="th-filter">
                    <span>Status</span>
                    <select
                      value={filters.status}
                      onChange={(e) => setFilters({...filters, status: e.target.value})}
                      className="table-filter-select"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <option value="all">All</option>
                      <option value="pending">Pending</option>
                      <option value="processing">Processing</option>
                      <option value="summarizing">Summarizing</option>
                      <option value="pending_action">Pending Action</option>
                      <option value="in_progress">In Progress</option>
                      <option value="resolved">Resolved</option>
                      <option value="completed">Completed</option>
                      <option value="failed">Failed</option>
                    </select>
                  </div>
                </th>
                <th>
                  <div className="th-filter">
                    <span>Category</span>
                    <select
                      value={filters.category}
                      onChange={(e) => setFilters({...filters, category: e.target.value})}
                      className="table-filter-select"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <option value="all">All</option>
                      {Object.keys(stats.byCategory).sort().map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                    </select>
                  </div>
                </th>
                <th>
                  <div className="th-filter">
                    <span>Severity</span>
                    <select
                      value={filters.severity}
                      onChange={(e) => setFilters({...filters, severity: e.target.value})}
                      className="table-filter-select"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <option value="all">All</option>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </div>
                </th>
                <th>
                  <div className="th-filter">
                    <span>Assigned Team</span>
                    <select
                      value={filters.team}
                      onChange={(e) => setFilters({...filters, team: e.target.value})}
                      className="table-filter-select"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <option value="all">All</option>
                      {Object.keys(stats.byTeam).sort().map(team => (
                        <option key={team} value={team}>{team}</option>
                      ))}
                    </select>
                  </div>
                </th>
                <th>Documents</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredComplaints.slice(0, 10).map((complaint) => {
                let summary = null;
                try {
                  summary = JSON.parse(complaint.overall_summary);
                } catch (e) {
                  // Ignore
                }

                return (
                  <tr key={complaint.id} onClick={() => navigate(`/complaints/${complaint.id}`)} className="table-row-clickable">
                    <td>
                      <div className="complaint-title-cell">{complaint.title}</div>
                    </td>
                    <td>
                      <span
                        className="status-badge"
                        style={{ background: getStatusColor(complaint.status) }}
                      >
                        {formatStatus(complaint.status)}
                      </span>
                    </td>
                    <td>{summary?.category || '-'}</td>
                    <td>
                      {summary?.severity ? (
                        <span
                          className="severity-badge"
                          style={{ background: getSeverityColor(summary.severity) }}
                        >
                          {summary.severity.toUpperCase()}
                        </span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>{summary?.responsible_team || '-'}</td>
                    <td>{complaint.documents_count || 0}</td>
                    <td>{new Date(complaint.created_at).toLocaleDateString()}</td>
                    <td>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/complaints/${complaint.id}`);
                        }}
                        className="btn btn-sm btn-secondary"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {complaints.length === 0 && (
            <div className="empty-state">
              <p>No complaints yet. Create your first complaint to get started!</p>
              <button onClick={() => navigate('/create')} className="btn btn-primary">
                + Create Complaint
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
