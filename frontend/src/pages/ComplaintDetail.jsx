import { useParams, useNavigate, Link } from 'react-router-dom';
import { useComplaintPolling } from '../hooks/useComplaintPolling';
import { downloadDocument, regenerateSummary } from '../services/api';
import SummaryCard from '../components/SummaryCard';
import './ComplaintDetail.css';

function ComplaintDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { complaint, loading, error } = useComplaintPolling(id);

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
            {getStatusBadge(complaint.status)}
          </div>
          {complaint.description && (
            <div className="info-item description">
              <strong>Description:</strong>
              <p>{complaint.description}</p>
            </div>
          )}
        </div>

        {complaint.overall_summary && (
          <SummaryCard
            summary={complaint.overall_summary}
            onRegenerate={() => handleRegenerateSummary()}
            isProcessing={isProcessing}
          />
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
