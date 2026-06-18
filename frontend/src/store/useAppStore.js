import { create } from 'zustand';
import {
  uploadFile as apiUpload,
  chatWithAI as apiChat,
  getIntro as apiGetIntro,
  getStatus as apiGetStatus,
  getTellMeQuery as apiGetTellMeQuery,
} from '../services/api';

const generateSessionId = () =>
  'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 8);

// Theme persistence
const getInitialTheme = () => {
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {}
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
};

// Initial pre-loaded sample tables (registered on the backend).
// These are not "uploaded" by the user — they are loaded automatically
// when the backend starts. The frontend treats them like normal files
// in the sidebar so the user can interact with them right away.
const PRELOADED_SAMPLES = [
  {
    id: 'sample_timeseries.csv',
    name: 'sample_timeseries.csv',
    path: 'sample_timeseries.csv',
    size: 0,
    rows: 0,
    columns: 0,
    source: 'sample',
    selected: true,
  },
  {
    id: 'db.games',
    name: 'db.games',
    path: 'db.games',
    size: 0,
    rows: 0,
    columns: 0,
    source: 'db',
    selected: true,
  },
  {
    id: 'db.users',
    name: 'db.users',
    path: 'db.users',
    size: 0,
    rows: 0,
    columns: 0,
    source: 'db',
    selected: true,
  },
  {
    id: 'db.reviews',
    name: 'db.reviews',
    path: 'db.reviews',
    size: 0,
    rows: 0,
    columns: 0,
    source: 'db',
    selected: true,
  },
];

const useAppStore = create((set, get) => {
  const initialTheme = getInitialTheme();
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', initialTheme === 'dark');
  }

  return {
    // ---- State -----------------------------------------------------
    sessionId: null,
    files: [...PRELOADED_SAMPLES],       // pre-loaded samples
    messages: [],
    selectedFiles: PRELOADED_SAMPLES.map((f) => f.name),
    activeView: 'chat',                  // 'chat' | 'data' | 'charts'
    theme: initialTheme,
    isLoading: false,
    error: null,

    // ---- Landing / status ------------------------------------------
    intro: null,                         // payload from /api/intro
    serverStatus: null,                  // payload from /api/status
    serverStatusCheckedAt: 0,
    isCheckingStatus: false,

    // ---- Workflow progress (live) ----------------------------------
    // List of small step objects for the in-flight chat request.
    // Each item: { id, stage, label, status: 'pending'|'active'|'done'|'error', detail }
    workflowSteps: [],

    // Legacy compatibility
    get uploadedFiles() { return get().files; },
    get selectedFileNames() { return get().selectedFiles; },
    get chatHistory() { return get().messages; },

    currentDataContext: null,
    filePreviews: {},
    selectedColumns: {},

    // ---- Session ---------------------------------------------------
    ensureSession: () => {
      const { sessionId } = get();
      if (!sessionId) set({ sessionId: generateSessionId() });
    },

    // ---- Landing info ----------------------------------------------
    loadIntro: async () => {
      try {
        const data = await apiGetIntro();
        set({ intro: data });
        // Update sample rows from the database overview.
        if (data?.sample_data?.database?.row_counts) {
          const counts = data.sample_data.database.row_counts;
          set((state) => ({
            files: state.files.map((f) => {
              if (f.name === 'db.games') return { ...f, rows: counts.games || 0 };
              if (f.name === 'db.users') return { ...f, rows: counts.users || 0 };
              if (f.name === 'db.reviews') return { ...f, rows: counts.reviews || 0 };
              return f;
            }),
          }));
        }
        if (data?.sample_data?.local?.name) {
          // Fetch preview for the bundled CSV sample.
          try {
            const { fetchFilePreview } = await import('../services/api');
            const preview = await fetchFilePreview(data.sample_data.local.name);
            if (preview) {
              set((state) => ({
                filePreviews: { ...state.filePreviews, [data.sample_data.local.name]: preview },
                files: state.files.map((f) =>
                  f.name === data.sample_data.local.name
                    ? { ...f, rows: preview.totalRows, columns: Object.keys(preview.columns || {}).length }
                    : f
                ),
              }));
            }
          } catch {
            // Preview is optional
          }
        }
        return data;
      } catch (err) {
        console.warn('loadIntro failed', err);
        return null;
      }
    },

    checkServerStatus: async () => {
      const now = Date.now();
      const { serverStatusCheckedAt, isCheckingStatus } = get();
      // Avoid spamming the endpoint — only re-check every 5 s.
      if (isCheckingStatus) return get().serverStatus;
      if (now - serverStatusCheckedAt < 5_000) return get().serverStatus;

      set({ isCheckingStatus: true });
      try {
        const status = await apiGetStatus();
        set({
          serverStatus: status,
          serverStatusCheckedAt: Date.now(),
          isCheckingStatus: false,
        });
        return status;
      } catch (err) {
        set({ isCheckingStatus: false });
        return get().serverStatus;
      }
    },

    // ---- File Actions ----------------------------------------------
    uploadFile: async (file) => {
      const { ensureSession } = get();
      ensureSession();
      set({ isLoading: true, error: null });

      try {
        const data = await apiUpload(file);
        const fileInfo = {
          id: data.file_name || file.name,
          name: data.file_name || file.name,
          path: data.file_name || file.name,
          size: file.size,
          rows: data.num_rows || 0,
          columns: data.num_columns || 0,
          preview: null,
          source: 'upload',
          selected: true,
        };

        set((state) => ({
          files: [...state.files, fileInfo],
          selectedFiles: [...state.selectedFiles, fileInfo.name],
          currentDataContext: data.data_context || state.currentDataContext,
          isLoading: false,
          messages: data.ai_analysis
            ? [...state.messages, {
                id: Date.now() + 1,
                role: 'ai',
                content: data.ai_analysis,
                files: [fileInfo.name],
                logs: null,
                error: null,
              }]
            : state.messages,
        }));

        try {
          const previewData = await import('../services/api').then((m) => m.fetchFilePreview(fileInfo.name));
          if (previewData) {
            set((state) => ({
              filePreviews: { ...state.filePreviews, [fileInfo.name]: previewData },
            }));
          }
        } catch { /* preview non-critical */ }

        return fileInfo;
      } catch (err) {
        set({ isLoading: false, error: err.message || 'Upload failed' });
        throw err;
      }
    },

    removeFile: (fileId) =>
      set((state) => {
        const { [fileId]: _drop, ...restPreviews } = state.filePreviews;
        const { [fileId]: _drop2, ...restCols } = state.selectedColumns;
        return {
          files: state.files.filter((f) => f.id !== fileId),
          selectedFiles: state.selectedFiles.filter((n) => n !== fileId),
          filePreviews: restPreviews,
          selectedColumns: restCols,
          currentDataContext: state.files.length <= 1 ? null : state.currentDataContext,
        };
      }),

    toggleFileSelection: (fileId) =>
      set((state) => {
        const isSelected = state.selectedFiles.includes(fileId);
        return {
          selectedFiles: isSelected
            ? state.selectedFiles.filter((n) => n !== fileId)
            : [...state.selectedFiles, fileId],
        };
      }),

    selectAllFiles: () =>
      set((state) => ({ selectedFiles: state.files.map((f) => f.id || f.name) })),

    deselectAllFiles: () => set({ selectedFiles: [] }),

    // ---- Workflow progress helpers ---------------------------------
    _setWorkflowSteps: (steps) => set({ workflowSteps: steps }),
    _appendWorkflowStep: (step) =>
      set((state) => ({ workflowSteps: [...state.workflowSteps, step] })),
    _updateWorkflowStep: (id, patch) =>
      set((state) => ({
        workflowSteps: state.workflowSteps.map((s) =>
          s.id === id ? { ...s, ...patch } : s
        ),
      })),
    _clearWorkflowSteps: () => set({ workflowSteps: [] }),

    // ---- Chat / Message Actions ------------------------------------
    sendMessage: async (query, retryMessage = null) => {
      const { selectedFiles, files, ensureSession, messages } = get();
      ensureSession();
      set({ isLoading: true, error: null });

      if (!retryMessage && query) {
        const userMsg = { id: Date.now(), role: 'user', content: query };
        set((state) => ({ messages: [...state.messages, userMsg] }));
      }

      const queryStr = retryMessage || query;
      // Reset workflow steps for the new request.
      set({ workflowSteps: [] });

      try {
        const payload = {
          query: queryStr,
          tables: selectedFiles.length > 0 ? selectedFiles : files.map((f) => f.name),
          files: selectedFiles.length > 0 ? selectedFiles : files.map((f) => f.name),
        };

        const response = await apiChat(payload, { includeEvents: true });

        // Merge workflow events into our step list for the panel.
        const events = Array.isArray(response.workflow_events) ? response.workflow_events : [];
        const steps = events.map((ev, idx) => ({
          id: `ev-${idx}`,
          stage: ev.stage || 'unknown',
          label: ev.message || ev.stage || 'Working...',
          status: ev.type === 'done' ? 'done' : (ev.type === 'error' || ev.type === 'tool_giveup' ? 'error' : 'done'),
          detail: ev.preview || null,
          type: ev.type,
        }));
        if (steps.length) set({ workflowSteps: steps });

        const aiMsg = {
          id: Date.now() + 1,
          role: 'ai',
          content: response.user_response || 'No response from AI.',
          code: response.code_executed || null,
          logs: response.logs || null,
          files: (response.artifacts_created || []) || [],
          retries: response.retries_used || 0,
          error: null,
        };

        set((state) => ({ messages: [...state.messages, aiMsg], isLoading: false }));

        const newFiles = response.artifacts_created || [];
        if (newFiles.length > 0) {
          newFiles.forEach(async (fName) => {
            if (fName.toLowerCase().endsWith('.csv')) {
              try {
                const previewData = await import('../services/api').then((m) => m.fetchFilePreview(fName));
                if (previewData) {
                  set((state) => ({
                    filePreviews: { ...state.filePreviews, [fName]: previewData },
                  }));
                }
              } catch { /* ignore */ }
            }
          });
        }

        return aiMsg;
      } catch (err) {
        const errorMessage = err.message || 'An unexpected error occurred.';
        set({ isLoading: false, error: errorMessage });

        const errorMsg = {
          id: Date.now() + 1,
          role: 'ai',
          content: `Error: ${errorMessage}`,
          code: null,
          logs: null,
          files: [],
          retries: 0,
          error: errorMessage,
          _originalQuery: queryStr,
        };

        set((state) => ({ messages: [...state.messages, errorMsg] }));
        return errorMsg;
      }
    },

    // Send the pre-built "Tell me about this data" prompt to /chat.
    tellMeAboutSample: async () => {
      try {
        const { query } = await apiGetTellMeQuery();
        return await get().sendMessage(query);
      } catch (err) {
        const message = err.message || 'Failed to load sample prompt.';
        set({ error: message });
        throw err;
      }
    },

    addMessage: (message) =>
      set((state) => ({ messages: [...state.messages, message] })),

    clearChat: () => set({ messages: [], workflowSteps: [] }),

    // ---- View & Theme ----------------------------------------------
    setActiveView: (view) => set({ activeView: view }),

    toggleTheme: () =>
      set((state) => {
        const newTheme = state.theme === 'light' ? 'dark' : 'light';
        try { localStorage.setItem('theme', newTheme); } catch {}
        document.documentElement.classList.toggle('dark', newTheme === 'dark');
        return { theme: newTheme };
      }),

    // ---- Legacy actions (kept for compatibility) -------------------
    addUploadedFile: (fileInfo) => {
      const { files, selectedFiles } = get();
      set({
        files: [...files, { id: fileInfo.name, ...fileInfo }],
        selectedFiles: [...selectedFiles, fileInfo.name],
      });
    },
    removeUploadedFile: (fileName) => get().removeFile(fileName),
    clearChatHistory: () => get().clearChat(),
    setFilePreview: (fileName, previewData) =>
      set((state) => ({ filePreviews: { ...state.filePreviews, [fileName]: previewData } })),
    setSelectedColumns: (fileName, cols) =>
      set((state) => ({ selectedColumns: { ...state.selectedColumns, [fileName]: cols } })),
    clearUploadedFiles: () =>
      set({ files: [], selectedFiles: [], currentDataContext: null, filePreviews: {}, selectedColumns: {} }),
    setLoading: (loading) => set({ isLoading: loading }),
    setError: (error) => set({ error }),
    clearError: () => set({ error: null }),
    setDataContext: (context) => set({ currentDataContext: context }),

    // ---- Reset -----------------------------------------------------
    reset: () =>
      set({
        sessionId: null,
        files: [...PRELOADED_SAMPLES],
        messages: [],
        selectedFiles: PRELOADED_SAMPLES.map((f) => f.name),
        activeView: 'chat',
        theme: initialTheme,
        isLoading: false,
        error: null,
        currentDataContext: null,
        filePreviews: {},
        selectedColumns: {},
        workflowSteps: [],
      }),
  };
});

export default useAppStore;
