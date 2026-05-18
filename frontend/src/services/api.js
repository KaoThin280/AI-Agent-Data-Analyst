// src/services/api.js
// API Client Layer — built on top of axiosClient

import axiosClient from '../api/axiosClient';

// ── Upload file ───────────────────────────────────────────────────────
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axiosClient.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  });
  return response.data;
};

// ── Chat with AI ──────────────────────────────────────────────────────
export const chatWithAI = async (query, tables = [], files = []) => {
  // Handle both old-style (string query) and new-style (payload object)
  let queryStr = query;
  let tableList = tables;
  let fileList = files;

  if (typeof query === 'object' && query !== null) {
    // New-style payload: { query, tables, files }
    queryStr = query.query || '';
    tableList = query.tables || [];
    fileList = query.files || [];
  }
  const response = await axiosClient.post(
    '/chat',
    { tables: tableList, files: fileList },
    {
      params: { query: queryStr },
    timeout: 300_000,
    }
  );
  return response.data;
};

// ── List files ────────────────────────────────────────────────────────
export const getFilesList = async () => {
  const response = await axiosClient.get('/files');
  return response.data;
};

// ── Download file as blob ─────────────────────────────────────────────
export const fetchFileBlob = async (fileName) => {
  const response = await axiosClient.get(`/files/${encodeURIComponent(fileName)}`, {
    responseType: 'blob',
  });
  return URL.createObjectURL(response.data);
};

// ── Get HTML file content as text (for Plotly charts) ─────────────────
export const fetchFileContent = async (fileName) => {
  const response = await axiosClient.get(`/files/${encodeURIComponent(fileName)}`, {
    responseType: 'text',
  });
  return response.data;
};

// ── Get table data for manual charting or preview ─────────────────────
export const getTableData = async (tableName) => {
  // Note: the backend expects session_id = filename; we pass the table name
  const response = await axiosClient.get(`/tables/${encodeURIComponent(tableName)}`);
  return response.data;
};

// ── Get first N rows for file preview ─────────────────────────────────
export const fetchFilePreview = async (fileName) => {
  try {
    const data = await getTableData(fileName);
    // Return only first 5 rows for preview
    return {
      columns: data.columns || {},
      rows: (data.data || []).slice(0, 5),
      totalRows: data.num_rows || 0,
    };
  } catch {
    return null;
  }
};

// ── Submit review ─────────────────────────────────────────────────────
export const submitReview = async (reviewData) => {
  const response = await axiosClient.post('/reviews', reviewData);
  return response.data;
};

// ── Health check ──────────────────────────────────────────────────────
export const checkHealth = async () => {
  try {
    const response = await axiosClient.get('/health', { timeout: 5000 });
    return response.data?.status === 'healthy';
  } catch {
    return false;
  }
};

// ── Legacy namespace (compatibility) ───────────────────────────────────
export const api = {
  uploadFile,
  chatWithAI,
  getFilesList,
  fetchFileBlob,
  fetchFileContent,
  getTableData,
  submitReview,
  fetchFilePreview,
};

