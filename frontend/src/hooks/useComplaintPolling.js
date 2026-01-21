import { useState, useEffect, useCallback } from 'react';
import { getComplaint, getDocuments } from '../services/api';

export const useComplaintPolling = (complaintId, interval = 3000) => {
  const [complaint, setComplaint] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchComplaint = useCallback(async () => {
    if (!complaintId) return;

    try {
      const [complaintData, documentsData] = await Promise.all([
        getComplaint(complaintId),
        getDocuments(complaintId)
      ]);

      // Merge documents into complaint data
      const enrichedComplaint = {
        ...complaintData,
        documents: documentsData.items || []
      };

      setComplaint(enrichedComplaint);
      setError(null);

      // Stop polling if processing is complete, failed, or pending action
      const finalStatuses = ['completed', 'failed', 'pending_action', 'in_progress', 'resolved'];
      if (finalStatuses.includes(complaintData.status)) {
        return false; // Signal to stop polling
      }
      return true; // Continue polling
    } catch (err) {
      setError(err.message);
      return false; // Stop polling on error
    } finally {
      setLoading(false);
    }
  }, [complaintId]);

  useEffect(() => {
    if (!complaintId) return;

    let intervalId;
    let shouldContinue = true;

    const poll = async () => {
      const continuePolling = await fetchComplaint();
      if (!continuePolling) {
        shouldContinue = false;
        if (intervalId) clearInterval(intervalId);
      }
    };

    // Initial fetch
    poll();

    // Set up polling
    intervalId = setInterval(() => {
      if (shouldContinue) {
        poll();
      }
    }, interval);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [complaintId, interval, fetchComplaint]);

  return { complaint, loading, error, refetch: fetchComplaint };
};
