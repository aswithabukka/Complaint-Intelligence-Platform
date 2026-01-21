import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useComplaintPolling } from '../hooks/useComplaintPolling';
import { downloadDocument, regenerateSummary, updateComplaint } from '../services/api';
import SummaryCard from '../components/SummaryCard';
import './ComplaintDetail.css';

function ComplaintDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { complaint, loading, error, refetch } = useComplaintPolling(id);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  const handleDownload = async (documentId, filename) => {
    try {
      const blob = await downloadDocument(id, documentId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert('Failed to download document: ' + err.message);
    }
  };

  const handleRegenerateSummary = async (documentId = null) => {
    try {
      await regenerateSummary(id, documentId);
      alert('Summary regeneration started. Please wait...');
    } catch (err) {
      alert('Failed to regenerate summary: ' + err.message);
    }
  };

  const handleStatusChange = async (newStatus) => {
    if (newStatus === complaint.status) return;

    setIsUpdatingStatus(true);
    try {
      await updateComplaint(id, { status: newStatus });
      // Trigger refetch to get updated data
      if (refetch) {
        await refetch();
      }
      alert(`Status updated to ${newStatus.replace('_', ' ').toUpperCase()}`);
    } catch (err) {
      alert('Failed to update status: ' + err.message);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleSendCustomerUpdate = () => {
    if (!complaint.overall_summary) {
      alert('No summary available to generate customer update');
      return;
    }

    let summary = null;
    try {
      summary = JSON.parse(complaint.overall_summary);
    } catch (e) {
      alert('Unable to parse summary for customer update');
      return;
    }

    const subject = `Update on Your Complaint: ${complaint.title}`;
    const body = `Dear Valued Customer,

Thank you for bringing this matter to our attention. We wanted to provide you with an update on your complaint.

Complaint Reference: ${complaint.title}
Status: ${complaint.status.replace('_', ' ').toUpperCase()}
Category: ${summary.category || 'N/A'}
Assigned Team: ${summary.responsible_team || 'Unassigned'}

Summary:
${summary.executive_summary || 'We are actively reviewing your complaint.'}

${summary.recommended_actions && summary.recommended_actions.length > 0 ? `Next Steps:
${summary.recommended_actions.map((action, i) => `${i + 1}. ${action}`).join('\n')}` : ''}

We appreciate your patience and will continue to keep you informed of any developments.

If you have any questions, please don't hesitate to reach out.

Best regards,
Customer Support Team`;

    const mailtoLink = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailtoLink;
  };

  const handleCreateJiraTicket = () => {
    if (!complaint.overall_summary) {
      alert('No summary available to generate Jira ticket');
      return;
    }

    let summary = null;
    try {
      summary = JSON.parse(complaint.overall_summary);
    } catch (e) {
      alert('Unable to parse summary for Jira ticket');
      return;
    }

    const jiraSummary = `[${summary.severity?.toUpperCase() || 'MEDIUM'}] ${complaint.title}`;
    const jiraDescription = `*Complaint ID:* ${complaint.id}
*Category:* ${summary.category || 'N/A'}
*Severity:* ${summary.severity?.toUpperCase() || 'MEDIUM'}
*Sentiment:* ${summary.sentiment?.toUpperCase() || 'NEUTRAL'}
*Assigned Team:* ${summary.responsible_team || 'Unassigned'}

h2. Executive Summary
${summary.executive_summary || 'No summary available'}

${summary.core_issues && summary.core_issues.length > 0 ? `h2. Core Issues
${summary.core_issues.map((issue, i) => `* ${issue}`).join('\n')}` : ''}

${summary.recommended_actions && summary.recommended_actions.length > 0 ? `h2. Recommended Actions
${summary.recommended_actions.map((action, i) => `# ${action}`).join('\n')}` : ''}

${summary.timeline && summary.timeline.length > 0 ? `h2. Timeline
${summary.timeline.map((event, i) => `* ${event}`).join('\n')}` : ''}

*Created:* ${new Date(complaint.created_at).toLocaleString()}
*Documents:* ${complaint.documents?.length || 0}`;

    // Copy to clipboard
    navigator.clipboard.writeText(`Summary: ${jiraSummary}\n\nDescription:\n${jiraDescription}`).then(() => {
      alert('Jira ticket details copied to clipboard!\n\nSummary: ' + jiraSummary);
    }).catch(() => {
      alert('Failed to copy to clipboard. Here are the details:\n\nSummary: ' + jiraSummary + '\n\nDescription:\n' + jiraDescription);
    });
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      pending: 'badge-gray',
      extracting: 'badge-blue',
      extracted: 'badge-blue',
      processing: 'badge-blue',
      summarizing: 'badge-purple',
      pending_action: 'badge-yellow',
      in_progress: 'badge-blue',
      resolved: 'badge-green',
      completed: 'badge-green',
      failed: 'badge-red',
    };
    const displayText = status.replace('_', ' ').toUpperCase();
    return <span className={`badge ${statusClasses[status] || 'badge-gray'}`}>{displayText}</span>;
  };

  const getProgressPercentage = () => {
    if (!complaint) return 0;

    if (complaint.status === 'completed') return 100;
    if (complaint.status === 'failed') return 100;
    if (complaint.status === 'summarizing') return 75;
    if (complaint.status === 'processing') return 50;
    if (complaint.status === 'pending') return 10;
    return 0;
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'badge-gray',
      processing: 'badge-blue',
      summarizing: 'badge-purple',
      pending_action: 'badge-yellow',
      in_progress: 'badge-blue',
      resolved: 'badge-green',
      completed: 'badge-green',
      failed: 'badge-red',
    };
    return colors[status] || 'badge-gray';
  };

  if (loading && !complaint) {
    return <div className="loading">Loading complaint details...</div>;
  }

  if (error) {
    return (
      <div className="error-page">
        <h2>Error</h2>
        <p>{error}</p>
        <Link to="/" className="btn btn-primary">Back to Dashboard</Link>
      </div>
    );
  }

  if (!complaint) {
    return <div className="loading">Complaint not found</div>;
  }

  const isProcessing = ['processing', 'summarizing'].includes(complaint.status);
  const isActionable = ['pending_action', 'in_progress'].includes(complaint.status);

  return (
    <div className="complaint-detail">
      <div className="page-header">
        <div>
          <Link to="/" className="back-link">← Back to Dashboard</Link>
          <h2>{complaint.title}</h2>
          {getStatusBadge(complaint.status)}
        </div>
      </div>

      {isProcessing && (
        <div className="processing-indicator">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${getProgressPercentage()}%` }}
            ></div>
          </div>
          <p className="processing-text">
            🔄 Processing documents and generating AI summaries... This may take a few minutes.
          </p>
        </div>
      )}

      <div className="detail-grid">
        <div className="detail-section">
          <h3>Complaint Information</h3>
          <div className="info-item">
            <strong>Created:</strong>
            <span>{new Date(complaint.created_at).toLocaleString()}</span>
          </div>
          <div className="info-item">
            <strong>Last Updated:</strong>
            <span>{new Date(complaint.updated_at).toLocaleString()}</span>
          </div>
          <div className="info-item">
            <strong>Status:</strong>
            <div className="status-control">
              {getStatusBadge(complaint.status)}
              {isActionable && (
                <select
                  value={complaint.status}
                  onChange={(e) => handleStatusChange(e.target.value)}
                  disabled={isUpdatingStatus}
                  className="status-dropdown"
                >
                  <option value="pending_action">Pending Action</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                  <option value="completed">Completed</option>
                </select>
              )}
            </div>
          </div>
          {complaint.description && (
            <div className="info-item description">
              <strong>Description:</strong>
              <p>{complaint.description}</p>
            </div>
          )}
        </div>

        {complaint.overall_summary && (
          <>
            <SummaryCard
              summary={complaint.overall_summary}
              onRegenerate={() => handleRegenerateSummary()}
              isProcessing={isProcessing}
            />

            {/* Action Buttons */}
            <div className="action-buttons">
              <button
                onClick={handleSendCustomerUpdate}
                className="btn btn-primary action-btn"
                disabled={isProcessing}
              >
                📧 Send Customer Update
              </button>
              <button
                onClick={handleCreateJiraTicket}
                className="btn btn-secondary action-btn"
                disabled={isProcessing}
              >
                🎫 Create Jira Ticket
              </button>
            </div>
          </>
        )}

        <div className="detail-section">
          <h3>Documents ({complaint.documents?.length || 0})</h3>
          {complaint.documents && complaint.documents.length > 0 ? (
            <div className="documents-list">
              {complaint.documents.map((doc) => (
                <div key={doc.id} className="document-card">
                  <div className="document-header">
                    <div>
                      <h4>{doc.original_filename}</h4>
                      <span className="document-meta">
                        {doc.file_type?.toUpperCase()} • {(doc.file_size / 1024).toFixed(2)} KB
                      </span>
                    </div>
                    <div className="document-actions">
                      {getStatusBadge(doc.processing_status)}
                      <button
                        onClick={() => handleDownload(doc.id, doc.original_filename)}
                        className="btn btn-sm btn-secondary"
                        title="Download"
                      >
                        ⬇
                      </button>
                    </div>
                  </div>

                  {doc.processing_status === 'failed' && doc.error_message && (
                    <div className="document-error">
                      <strong>Error:</strong> {doc.error_message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="no-documents">No documents uploaded yet</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default ComplaintDetail;
