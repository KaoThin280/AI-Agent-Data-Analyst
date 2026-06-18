// src/services/api.js
// API Client Layer - built on top of axiosClient

import axiosClient from '../api/axiosClient';

// ---- Upload file -----------------------------------------------------
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axiosClient.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  });
  return response.data;
};

// ---- Chat with AI (supports workflow events for the status panel) ---
export const chatWithAI = async (query, tables = [], files = [], options = {}) => {
  let queryStr = query;
  let tableList = tables;
  let fileList = files;

  if (typeof query === 'object' && query !== null) {
    queryStr = query.query || '';
    tableList = query.tables || [];
    fileList = query.files || [];
  }

  const includeEvents = options.includeEvents !== false;

  const response = await axiosClient.post(
    '/chat',
    { tables: tableList, files: fileList },
    {
      params: {
        query: queryStr,
        include_events: includeEvents,
      },
      timeout: 300_000,
    }
  );
  return response.data;
};

// ---- List files ------------------------------------------------------
export const getFilesList = async () => {
  const response = await axiosClient.get('/files');
  return response.data;
};

// ---- Download file as blob -------------------------------------------
export const fetchFileBlob = async (fileName) => {
  const response = await axiosClient.get(`/files/${encodeURIComponent(fileName)}`, {
    responseType: 'blob',
  });
  return URL.createObjectURL(response.data);
};

// ---- Get HTML file content as text (for Plotly charts) ---------------
export const fetchFileContent = async (fileName) => {
  const response = await axiosClient.get(`/files/${encodeURIComponent(fileName)}`, {
    responseType: 'text',
  });
  return response.data;
};

// ---- Get table data for manual charting or preview -------------------
export const getTableData = async (tableName) => {
  const response = await axiosClient.get(`/tables/${encodeURIComponent(tableName)}`);
  return response.data;
};

export const fetchFilePreview = async (fileName) => {
  try {
    const data = await getTableData(fileName);
    return {
      columns: data.columns || {},
      rows: (data.data || []).slice(0, 5),
      totalRows: data.num_rows || 0,
    };
  } catch {
    return null;
  }
};

// ---- Submit review ---------------------------------------------------
export const submitReview = async (reviewData) => {
  const response = await axiosClient.post('/reviews', reviewData);
  return response.data;
};

// ---- Health check ----------------------------------------------------
export const checkHealth = async () => {
  try {
    const response = await axiosClient.get('/health', { timeout: 5000 });
    return response.data?.status === 'healthy';
  } catch {
    return false;
  }
};

// ---- Public info / status endpoints (no API key required) -----------

// Get landing greeting + sample-data description.
export const getIntro = async () => {
  const response = await axiosClient.get('/api/intro', { timeout: 15_000 });
  return response.data;
};

// Lightweight status ping for the connection badge.
export const getStatus = async () => {
  try {
    const response = await axiosClient.get('/api/status', { timeout: 10_000 });
    return response.data;
  } catch (err) {
    return {
      ok: false,
      connection_state: 'error',
      message: 'Unable to reach backend.',
      database: { ready: false, counts: {}, error: null },
      free_tier_notes: '',
    };
  }
};

// Pre-built query for the "Tell me about this data" button.
export const getTellMeQuery = async () => {
  const response = await axiosClient.get('/api/sample-data/tell-me', { timeout: 5_000 });
  return response.data;
};

// ---- Legacy namespace ------------------------------------------------
export const api = {
  uploadFile,
  chatWithAI,
  getFilesList,
  fetchFileBlob,
  fetchFileContent,
  getTableData,
  submitReview,
  fetchFilePreview,
  getIntro,
  getStatus,
  getTellMeQuery,
};
