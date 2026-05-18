import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Loader2, Download, X, Maximize2, Minimize2,
  AlertTriangle, ChevronLeft, ChevronRight, Image as ImageIcon,
} from 'lucide-react';
import { fetchFileContent, fetchFileBlob } from '../../services/api';
import PlotlyHtmlRenderer from '../Renderers/PlotlyHtmlRenderer';

// ── Lightbox for PNG images ──────────────────────────────────────
function Lightbox({ src, alt, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 cursor-zoom-out"
      onClick={onClose}
    >
      <button
        onClick={onClose}
        className="absolute top-4 right-4 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 transition-colors"
      >
        <X size={24} />
      </button>
      <img
        src={src}
        alt={alt}
        className="max-h-[90vh] max-w-[90vw] rounded-lg shadow-2xl object-contain cursor-default"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

// ── Loading Skeleton ──────────────────────────────────────────────
function ChartSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      <div className="h-8 bg-gray-100 dark:bg-gray-700 rounded-t-xl" />
      <div className="h-[300px] bg-gray-50 dark:bg-gray-800 flex items-center justify-center">
        <div className="text-center">
          <Loader2 size={24} className="animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-xs text-gray-400">Loading chart...</p>
        </div>
      </div>
    </div>
  );
}

// ── Error Fallback ────────────────────────────────────────────────
function ChartError({ fileName, error }) {
  return (
    <div className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 flex flex-col items-center justify-center min-h-[200px]">
      <AlertTriangle size={32} className="text-red-400 mb-2" />
      <p className="text-sm font-medium text-red-700 dark:text-red-400 mb-1">
        Failed to load chart
      </p>
      <p className="text-xs text-red-500 dark:text-red-300 text-center max-w-xs">
        {fileName}
      </p>
      {error && (
        <p className="text-xs text-red-400 dark:text-red-500 mt-1 text-center max-w-xs">
          {error}
        </p>
      )}
    </div>
  );
}

// ── Download Button ──────────────────────────────────────────────
function DownloadButton({ fileName }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = useCallback(async () => {
    setDownloading(true);
    try {
      // Fetch file as blob then trigger download
      const blobUrl = await fetchFileBlob(fileName);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      // Revoke blob URL after a delay
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloading(false);
    }
  }, [fileName]);

  return (
    <button
      onClick={handleDownload}
      disabled={downloading}
      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium
        bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300
        hover:bg-gray-200 dark:hover:bg-gray-600
        rounded-lg transition-colors disabled:opacity-50"
      title={`Download ${fileName}`}
    >
      {downloading ? (
        <Loader2 size={12} className="animate-spin" />
      ) : (
        <Download size={12} />
      )}
      <span>Download</span>
    </button>
  );
}

// ── PNG Chart Card ────────────────────────────────────────────────
function PngChartCard({ fileName, caption, onOpenLightbox }) {
  const [imgUrl, setImgUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchFileBlob(fileName)
      .then((url) => {
        if (!cancelled) {
          setImgUrl(url);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load image');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [fileName]);

  if (loading) return <ChartSkeleton />;
  if (error) return <ChartError fileName={fileName} error={error} />;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400 truncate flex-1 mr-2">
          {fileName}
        </span>
        <div className="flex items-center gap-1 shrink-0">
          <DownloadButton fileName={fileName} />
          <button
            onClick={() => onOpenLightbox(imgUrl, fileName)}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            title="View full size"
          >
            <Maximize2 size={14} className="text-gray-500" />
          </button>
        </div>
      </div>

      {/* Image */}
      <div
        className="bg-gray-50 dark:bg-gray-900 p-2 cursor-zoom-in"
        onClick={() => onOpenLightbox(imgUrl, fileName)}
      >
        <img
          src={imgUrl}
          alt={fileName}
          className="max-w-full h-auto mx-auto rounded-lg shadow-sm"
          style={{ maxHeight: '400px' }}
        />
      </div>

      {/* Caption */}
      {caption && (
        <div className="px-3 py-2 border-t border-gray-100 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
            {caption}
          </p>
        </div>
      )}
    </div>
  );
}

// ── HTML Chart Card ───────────────────────────────────────────────
function HtmlChartCard({ fileName, caption }) {
  const [htmlContent, setHtmlContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchFileContent(fileName)
      .then((content) => {
        if (!cancelled) {
          setHtmlContent(content);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load chart');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [fileName]);

  if (loading) return <ChartSkeleton />;
  if (error) return <ChartError fileName={fileName} error={error} />;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* PlotlyHtmlRenderer handles header and fullscreen internally */}
      <PlotlyHtmlRenderer htmlContent={htmlContent} title={fileName} />

      {/* Caption */}
      {caption && (
        <div className="px-3 py-2 border-t border-gray-100 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
            {caption}
          </p>
        </div>
      )}

      {/* Download button below chart */}
      <div className="px-3 pb-2 flex justify-end">
        <DownloadButton fileName={fileName} />
      </div>
    </div>
  );
}

// ── Main VisualizationViewer ──────────────────────────────────────
export default function VisualizationViewer({ files, captions, title }) {
  const [lightboxSrc, setLightboxSrc] = useState(null);
  const [lightboxAlt, setLightboxAlt] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);

  // Separate files by type
  const htmlFiles = (files || []).filter((f) => f.toLowerCase().endsWith('.html'));
  const pngFiles = (files || []).filter((f) => /\.(png|jpg|jpeg|gif|svg|webp)$/i.test(f));
  const otherFiles = (files || []).filter((f) => {
    const lower = f.toLowerCase();
    return !lower.endsWith('.html') && !/\.(png|jpg|jpeg|gif|svg|webp)$/i.test(lower);
  });

  const allChartFiles = [...htmlFiles, ...pngFiles];
  const totalCharts = allChartFiles.length;

  const openLightbox = useCallback((src, alt) => {
    setLightboxSrc(src);
    setLightboxAlt(alt);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightboxSrc(null);
    setLightboxAlt(null);
  }, []);

  // Get caption for a file
  const getCaption = useCallback((fileName) => {
    if (!captions) return null;
    // Try exact match, then basename match
    return captions[fileName] || captions[fileName.split('/').pop()] || null;
  }, [captions]);

  if (totalCharts === 0 && otherFiles.length === 0) return null;

  return (
    <div className="mt-2 space-y-2">
      {/* Title */}
      {title && (
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <ImageIcon size={16} className="text-blue-500" />
          {title}
        </h4>
      )}

      {/* Carousel / Gallery Navigation */}
      {totalCharts > 1 && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
            disabled={currentPage === 0}
            className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400
              hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {currentPage + 1} / {totalCharts}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalCharts - 1, p + 1))}
            disabled={currentPage === totalCharts - 1}
            className="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400
              hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* Gallery Grid (when 4+ charts) or Single/Carousel View */}
      {totalCharts >= 4 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {allChartFiles.map((file, idx) => {
            const isHtml = file.toLowerCase().endsWith('.html');
            return isHtml ? (
              <HtmlChartCard key={idx} fileName={file} caption={getCaption(file)} />
            ) : (
              <PngChartCard
                key={idx}
                fileName={file}
                caption={getCaption(file)}
                onOpenLightbox={openLightbox}
              />
            );
          })}
        </div>
      ) : totalCharts > 1 ? (
        /* Carousel: show current page */
        <div className="transition-all duration-300">
          {(() => {
            const file = allChartFiles[currentPage];
            const isHtml = file.toLowerCase().endsWith('.html');
            return isHtml ? (
              <HtmlChartCard fileName={file} caption={getCaption(file)} />
            ) : (
              <PngChartCard
                fileName={file}
                caption={getCaption(file)}
                onOpenLightbox={openLightbox}
              />
            );
          })()}
        </div>
      ) : totalCharts === 1 ? (
        /* Single chart */
        <div>
          {(() => {
            const file = allChartFiles[0];
            const isHtml = file.toLowerCase().endsWith('.html');
            return isHtml ? (
              <HtmlChartCard fileName={file} caption={getCaption(file)} />
            ) : (
              <PngChartCard
                fileName={file}
                caption={getCaption(file)}
                onOpenLightbox={openLightbox}
              />
            );
          })()}
        </div>
      ) : null}

      {/* Other files (non-chart) - show as simple badges */}
      {otherFiles.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {otherFiles.map((file, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2.5 py-1 rounded-full"
            >
              <Download size={10} />
              {file}
              <DownloadButton fileName={file} />
            </span>
          ))}
        </div>
      )}

      {/* Lightbox */}
      {lightboxSrc && (
        <Lightbox src={lightboxSrc} alt={lightboxAlt} onClose={closeLightbox} />
      )}
    </div>
  );
}