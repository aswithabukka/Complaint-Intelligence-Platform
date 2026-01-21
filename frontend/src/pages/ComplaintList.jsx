import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getComplaints, deleteComplaint } from '../services/api';
import './ComplaintList.css';

function ComplaintList() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchComplaints();
  }, [page]);

  const fetchComplaints = async () => {
    try {
      setLoading(true);
      const data = await getComplaints(page, 10);
      setComplaints(data.items);
      setTotalPages(Math.ceil(data.total / data.limit));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this complaint?')) {
      return;
    }

    try {
      await deleteComplaint(id);
      fetchComplaints();
    } catch (err) {
      alert('Failed to delete complaint: ' + err.message);
    }
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      pending: 'badge-gray',
      processing: 'badge-blue',
      summarizing: 'badge-purple',
      completed: 'badge-green',
      failed: 'badge-red',
    };
    return <span className={`badge ${statusClasses[status] || 'badge-gray'}`}>{status}</span>;
  };

  if (loading && complaints.length === 0) {
    return <div className="loading">Loading complaints...</div>;
  }

  if (error) {
    return <div className="error">Error: {error}</div>;
  }

  return (
    <div className="complaint-list">
      <div className="page-header">
        <h2>Complaints Dashboard</h2>
        <Link to="/create" className="btn btn-primary">+ New Complaint</Link>
      </div>

      {complaints.length === 0 ? (
        <div className="empty-state">
          <h3>No complaints yet</h3>
          <p>Create your first complaint to get started</p>
          <Link to="/create" className="btn btn-primary">Create Complaint</Link>
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <div className="stat-card">
              <h4>Total Complaints</h4>
              <p className="stat-number">{complaints.length}</p>
            </div>
            <div className="stat-card">
              <h4>Processing</h4>
              <p className="stat-number">{complaints.filter(c => c.status === 'processing' || c.status === 'summarizing').length}</p>
            </div>
            <div className="stat-card">
              <h4>Completed</h4>
              <p className="stat-number">{complaints.filter(c => c.status === 'completed').length}</p>
            </div>
          </div>

          <div className="complaints-table">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Documents</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {complaints.map((complaint) => (
                  <tr key={complaint.id}>
                    <td>
                      <Link to={`/complaints/${complaint.id}`} className="complaint-title">
                        {complaint.title}
                      </Link>
                    </td>
                    <td>{getStatusBadge(complaint.status)}</td>
                    <td>{complaint.documents_count}</td>
                    <td>{new Date(complaint.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="action-buttons">
                        <Link to={`/complaints/${complaint.id}`} className="btn btn-sm btn-secondary">
                          View
                        </Link>
                        <button
                          onClick={() => handleDelete(complaint.id)}
                          className="btn btn-sm btn-danger"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary"
              >
                Previous
              </button>
              <span className="page-info">Page {page} of {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn btn-secondary"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default ComplaintList;
