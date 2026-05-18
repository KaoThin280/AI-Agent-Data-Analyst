import { create } from 'zustand';
import { uploadFile as apiUpload, chatWithAI as apiChat } from '../services/api';

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

const useAppStore = create((set, get) => {
  const initialTheme = getInitialTheme();
  // Apply initial theme to root
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', initialTheme === 'dark');
  }

  return {
    // ── State ──────────────────────────────────────────────────────
    sessionId: null,
    files: [],                // { id, name, path, size, rows, columns, preview?, selected? }
    messages: [],             // { id, role, content, code?, files?, logs?, error? }
    selectedFiles: [],        // string[] of file names
    activeView: 'chat',       // 'chat' | 'data' | 'charts'
    theme: initialTheme,
    isLoading: false,
    error: null,

    // Legacy compatibility — computed from new state
    get uploadedFiles() { return get().files; },
    get selectedFileNames() { return get().selectedFiles; },
    get chatHistory() { return get().messages; },

    // Additional data caches (kept for compatibility)
    currentDataContext: null,
    filePreviews: {},
    selectedColumns: {},

    // ── Session ────────────────────────────────────────────────────
    ensureSession: () => {
      const { sessionId } = get();
      if (!sessionId) set({ sessionId: generateSessionId() });
    },

    // ── File Actions ───────────────────────────────────────────────
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
          selected: true,        // auto-select after upload
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

        // Fetch preview in background
        try {
          const previewData = await import('../services/api').then(m => m.fetchFilePreview(fileInfo.name));
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
        const { [fileId]: _, ...restPreviews } = state.filePreviews;
        const { [fileId]: __, ...restCols } = state.selectedColumns;
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
      set((state) => ({ selectedFiles: state.files.map((f) => f.id) })),

    deselectAllFiles: () => set({ selectedFiles: [] }),

    // ── Chat / Message Actions ─────────────────────────────────────
    sendMessage: async (query, retryMessage = null) => {
      const { selectedFiles, files, ensureSession, messages } = get();
      ensureSession();
      set({ isLoading: true, error: null });

      // Add user message (only if not retrying)
      if (!retryMessage && query) {
        const userMsg = { id: Date.now(), role: 'user', content: query };
        set((state) => ({ messages: [...state.messages, userMsg] }));
      }

      const queryStr = retryMessage || query;

      try {
        const payload = {
          query: queryStr,
          tables: selectedFiles.length > 0 ? selectedFiles : files.map((f) => f.name),
          files: selectedFiles.length > 0 ? selectedFiles : files.map((f) => f.name),
        };

        const response = await apiChat(payload);

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

        // Auto-update filePreviews for any new CSV files
        const newFiles = response.artifacts_created || [];
        if (newFiles.length > 0) {
          newFiles.forEach(async (fName) => {
            if (fName.toLowerCase().endsWith('.csv')) {
              try {
                const previewData = await import('../services/api').then(m => m.fetchFilePreview(fName));
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
          content: `❌ **Error:** ${errorMessage}`,
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

    addMessage: (message) =>
      set((state) => ({ messages: [...state.messages, message] })),

    clearChat: () => set({ messages: [] }),

    // ── View & Theme ───────────────────────────────────────────────
    setActiveView: (view) => set({ activeView: view }),

    toggleTheme: () =>
      set((state) => {
        const newTheme = state.theme === 'light' ? 'dark' : 'light';
        try { localStorage.setItem('theme', newTheme); } catch {}
        document.documentElement.classList.toggle('dark', newTheme === 'dark');
        return { theme: newTheme };
      }),

    // ── Legacy actions (keep for compatibility) ────────────────────
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

    // ── Reset ──────────────────────────────────────────────────────
    reset: () =>
      set({
        sessionId: null,
        files: [],
        messages: [],
        selectedFiles: [],
        activeView: 'chat',
        theme: 'light',
        isLoading: false,
        error: null,
        currentDataContext: null,
        filePreviews: {},
        selectedColumns: {},
      }),
  };
});



export default useAppStore;