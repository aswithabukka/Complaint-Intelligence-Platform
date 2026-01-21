import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Complaints
export const getComplaints = async (page = 1, limit = 10) => {
  const response = await api.get('/complaints', { params: { page, limit } });
  return response.data;
};

export const getComplaint = async (id) => {
  const response = await api.get(`/complaints/${id}`);
  return response.data;
};

export const createComplaint = async (data) => {
  const response = await api.post('/complaints', data);
  return response.data;
};

export const deleteComplaint = async (id) => {
  const response = await api.delete(`/complaints/${id}`);
  return response.data;
};

export const processComplaint = async (id) => {
  const response = await api.post(`/complaints/${id}/process`);
  return response.data;
};

// Documents
export const uploadDocuments = async (complaintId, files) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post(`/complaints/${complaintId}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getDocuments = async (complaintId) => {
  const response = await api.get(`/complaints/${complaintId}/documents`);
  return response.data;
};

export const getDocument = async (complaintId, documentId) => {
  const response = await api.get(`/complaints/${complaintId}/documents/${documentId}`);
  return response.data;
};

export const downloadDocument = async (complaintId, documentId) => {
  const response = await api.get(`/complaints/${complaintId}/documents/${documentId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};

export const deleteDocument = async (complaintId, documentId) => {
  const response = await api.delete(`/complaints/${complaintId}/documents/${documentId}`);
  return response.data;
};

// Summaries
export const getSummaries = async (complaintId, documentId = null) => {
  const url = documentId
    ? `/complaints/${complaintId}/documents/${documentId}/summaries`
    : `/complaints/${complaintId}/summaries`;
  const response = await api.get(url);
  return response.data;
};

export const regenerateSummary = async (complaintId, documentId = null) => {
  const url = documentId
    ? `/complaints/${complaintId}/documents/${documentId}/summaries/regenerate`
    : `/complaints/${complaintId}/summaries/regenerate`;
  const response = await api.post(url);
  return response.data;
};

export default api;
