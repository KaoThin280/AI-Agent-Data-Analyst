import React, { useRef, useState, useEffect, useMemo } from 'react';
import { Maximize2, Minimize2, Loader2 } from 'lucide-react';

/**
 * PlotlyHtmlRenderer — Safely render Plotly HTML inside an isolated iframe.
 *
 * === GI\u1EA2I PH\u00C1P iframe + srcDoc ===
 * D\u00F9ng iframe v\u1EDBi thu\u1ED9c t\u00EDnh sandbox="allow-scripts allow-same-origin":
 * - C\u00c1CH LY ho\u00E0n to\u00E0n CSS/JS c\u1EE7a Plotly kh\u1ECFi React app (kh\u00F4ng b\u1ECB \u0111\u00E8 style)
 * - Plotly t\u1EF1 resize khi window thay \u0111\u1ED5i k\u00EDch th\u01B0\u1EDBc
 * - Kh\u00F4ng g\u00E2y \u00F4 nhi\u1EC5m global namespace
 * - Kh\u00F4ng c\u1EA7n network request (srcDoc = inline HTML)
 *
 * Tuy nhi\u00EAn iframe c\u00F3 m\u1ED9t nh\u01B0\u1EE3c \u0111i\u1EC3m: kh\u00F4ng t\u1EF1 \u0111\u1ED9ng co gi\u00E3n theo chi\u1EC1u cao n\u1ED9i dung.
 * Gi\u1EA3i ph\u00E1p: inject script postMessage \u0111\u1EC3 g\u1EEDi chi\u1EC1u cao th\u1EF1c t\u1EBF v\u1EC1 React window.
 */

/** Script injected vào iframe để tự động resize */
const RESIZE_SCRIPT = `
<script>
  (function() {
    function sendHeight() {
      var height = document.documentElement.scrollHeight;
      // Add minimal padding (8px), cap at 1000px to prevent excessive height
      window.parent.postMessage({ type: 'plotly-resize', height: Math.min(height + 8, 1000) }, '*');
    }
    window.addEventListener('load', sendHeight);
    window.addEventListener('resize', sendHeight);
    if (window.MutationObserver) {
      var obs = new MutationObserver(sendHeight);
      obs.observe(document.body, { childList: true, subtree: true, attributes: true });
    }
    document.addEventListener('plotly_relayout', sendHeight);
    document.addEventListener('plotly_redraw', sendHeight);
    // Initial send after short delay
    setTimeout(sendHeight, 100);
  })();
</script>
`;

export default function PlotlyHtmlRenderer({ htmlContent, title }) {
  const iframeRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeHeight, setIframeHeight] = useState(350);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const handler = (event) => {
      if (event.data?.type === 'plotly-resize' && typeof event.data.height === 'number') {
        setIframeHeight(event.data.height);
        setIsLoading(false);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  const fullHtml = useMemo(() => {
    if (!htmlContent) return '';
    let content = htmlContent;

    if (!content.includes('<html')) {
      content = `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;padding:2px;font-family:system-ui,sans-serif}</style></head><body>${content}</body></html>`;
    }

    content = content.replace('</body>', RESIZE_SCRIPT + '</body>');
    return content;
  }, [htmlContent]);

  useEffect(() => {
    setIsLoading(true);
    setIframeHeight(350);
  }, [htmlContent]);

  if (!htmlContent) return null;

  // --- Fullscreen mode ---
  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
        <div className="relative w-full h-full max-w-[98vw] max-h-[96vh] bg-white rounded-xl overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b shrink-0">
            <span className="text-sm font-medium text-gray-700 truncate">{title || 'Chart'}</span>
            <button onClick={() => setIsFullscreen(false)} className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors">
              <Minimize2 size={18} />
            </button>
          </div>
          <iframe
            srcDoc={fullHtml}
            title={title || 'Plotly Fullscreen'}
            className="w-full flex-1 border-0"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
      </div>
    );
  }

  // --- Normal mode ---
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-50 border-b">
        <span className="text-xs font-medium text-gray-600 truncate">
          {title || 'Interactive Chart'}
        </span>
        <button
          onClick={() => setIsFullscreen(true)}
          className="p-1 hover:bg-gray-200 rounded transition-colors"
          title="View fullscreen"
        >
          <Maximize2 size={14} className="text-gray-500" />
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-[300px] bg-gray-50">
          <div className="text-center">
            <Loader2 size={24} className="animate-spin text-blue-500 mx-auto mb-2" />
            <p className="text-xs text-gray-400">Loading chart...</p>
          </div>
        </div>
      )}

      <iframe
        ref={iframeRef}
        srcDoc={fullHtml}
        title={title || 'Plotly Chart'}
        className={`w-full border-0 transition-all duration-300 ${isLoading ? 'opacity-0 h-0 overflow-hidden' : 'opacity-100'}`}
        style={{ height: iframeHeight }}
        sandbox="allow-scripts allow-same-origin"
        scrolling="no"
      />
    </div>
  );
}