// src/components/data_view/DataTab.jsx
import React, { useState, useEffect } from 'react';
import { api } from '../../services/api.js';
import { RefreshCw } from 'lucide-react';

export default function DataTab() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);

  const fetchFiles = async () => {
    try {
      const data = await api.getFilesList();
      // Only filter chart or output data files
      const outputFiles = data.files.filter(f => f.endsWith('.html') || f.endsWith('.png') || f.endsWith('.csv'));
      setFiles(outputFiles);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  return (
    <div className="h-full bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col overflow-hidden">
      <div className="p-4 border-b flex justify-between items-center bg-gray-50">
        <h2 className="font-bold text-gray-700">Data Visualization</h2>
        <button onClick={fetchFiles} className="text-blue-600 hover:bg-blue-100 p-2 rounded flex items-center text-sm">
          <RefreshCw size={16} className="mr-1" /> Refresh
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File List */}
        <div className="w-1/4 border-r p-4 overflow-y-auto">
          <h3 className="text-sm font-semibold text-gray-500 mb-3">Generated Charts:</h3>
          <ul className="space-y-2">
            {files.map(file => (
              <li 
                key={file} 
                onClick={() => setSelectedFile(file)}
                className={`p-2 rounded cursor-pointer text-sm truncate ${selectedFile === file ? 'bg-blue-600 text-white' : 'hover:bg-gray-100 text-gray-700'}`}
              >
                {file}
              </li>
            ))}
            {files.length === 0 && <p className="text-xs text-gray-400">No charts have been created yet.</p>}
          </ul>
        </div>

        {/* Display Area */}
        <div className="w-3/4 p-4 bg-gray-50">
          {selectedFile ? (
            selectedFile.endsWith('.html') ? (
              <iframe src={api.getFileUrl(selectedFile)} className="w-full h-full border-none bg-white rounded shadow-sm" title="Chart"></iframe>
            ) : selectedFile.endsWith('.png') ? (
              <img src={api.getFileUrl(selectedFile)} alt="Chart" className="max-w-full max-h-full object-contain bg-white p-2 rounded shadow-sm" />
            ) : (
              <div className="p-4 text-gray-500">Please download {selectedFile} directly from the API.</div>
            )
          ) : (
            <div className="h-full flex items-center justify-center text-gray-400">
              Select a chart on the left to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}