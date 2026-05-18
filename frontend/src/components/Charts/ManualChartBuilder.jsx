import React, { useState, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer
} from 'recharts';
import { ChartBar, TrendingUp, ScatterChart as ScatterIcon, Table2 } from 'lucide-react';

const CHART_TYPES = [
  { id: 'bar',   label: 'C\u1ED9t',      icon: ChartBar,     color: 'blue' },
  { id: 'line',  label: '\u0110\u01B0\u1EDDng',    icon: TrendingUp,    color: 'green' },
  { id: 'scatter', label: 'Ph\u00E2n t\u00E1n', icon: ScatterIcon, color: 'purple' },
];

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4'];

export default function ManualChartBuilder({ data, columns, tableName }) {
  const [xCol, setXCol] = useState('');
  const [yCol, setYCol] = useState('');
  const [chartType, setChartType] = useState('bar');
  const [colorIdx, setColorIdx] = useState(0);
  const [showData, setShowData] = useState(false);

  const numericCols = useMemo(() => {
    if (!columns) {
      if (!data || data.length === 0) return [];
      return Object.keys(data[0]).filter(k => typeof data[0][k] === 'number');
    }
    return Object.entries(columns)
      .filter(([, v]) => v.dtype?.includes('float') || v.dtype?.includes('int'))
      .map(([k]) => k);
  }, [columns, data]);

  const allCols = useMemo(() => {
    if (columns) return Object.keys(columns);
    if (data?.[0]) return Object.keys(data[0]);
    return [];
  }, [columns, data]);

  const safeX = xCol || allCols[0] || '';
  const safeY = yCol || numericCols[0] || '';
  const chartData = data || [];

  const renderChart = () => {
    if (!safeX || !safeY) {
      return (
        <div className="flex flex-col items-center justify-center h-[400px] text-gray-400">
          <ChartBar size={48} className="mb-3 opacity-30" />
          <p className="text-sm">Ch\u1ECDn c\u1ED9t tr\u1EE5c X v\u00E0 Y \u0111\u1EC3 v\u1EBD bi\u1EC3u \u0111\u1ED3</p>
        </div>
      );
    }

    const commonProps = {
      data: chartData,
      margin: { top: 10, right: 30, left: 0, bottom: 10 },
    };
    const color = COLORS[colorIdx % COLORS.length];

    return (
      <ResponsiveContainer width="100%" height={400}>
        {chartType === 'bar' ? (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey={safeX} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }} />
            <Legend />
            <Bar dataKey={safeY} fill={color} radius={[4, 4, 0, 0]} maxBarSize={60} />
          </BarChart>
        ) : chartType === 'line' ? (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey={safeX} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }} />
            <Legend />
            <Line type="monotone" dataKey={safeY} stroke={color} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 6 }} />
          </LineChart>
        ) : (
          <ScatterChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey={safeX} tick={{ fontSize: 12 }} />
            <YAxis dataKey={safeY} tick={{ fontSize: 12 }} />
            <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }} />
            <Legend />
            <Scatter name={`${safeY} vs ${safeX}`} data={chartData} fill={color} shape="circle" />
          </ScatterChart>
        )}
      </ResponsiveContainer>
    );
  };

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">
            {tableName ? `V\u1EBD bi\u1EC3u \u0111\u1ED3: ${tableName}` : 'V\u1EBD bi\u1EC3u \u0111\u1ED3 th\u1EE7 c\u00F4ng'}
          </h3>
          <span className="text-xs text-gray-400">{chartData.length} d\u00F2ng d\u1EEF li\u1EC7u</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Tr\u1EE5c X</label>
            <select value={safeX} onChange={e => setXCol(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent">
              {allCols.map(col => <option key={col} value={col}>{col}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Tr\u1EE5c Y (s\u1ED1)</label>
            <select value={safeY} onChange={e => setYCol(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent">
              <option value="">-- Ch\u1ECDn c\u1ED9t --</option>
              {numericCols.map(col => <option key={col} value={col}>{col}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Lo\u1EA1i bi\u1EC3u \u0111\u1ED3</label>
            <div className="flex gap-1.5">
              {CHART_TYPES.map(ct => (
                <button key={ct.id} onClick={() => setChartType(ct.id)}
                  className={`flex items-center gap-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                    chartType === ct.id
                      ? 'bg-blue-100 text-blue-600 border border-blue-300'
                      : 'bg-gray-50 text-gray-500 border border-gray-200 hover:bg-gray-100'
                  }`}>
                  <ct.icon size={14} /> {ct.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500">M\u00E0u s\u1EAFc:</label>
            <div className="flex gap-1">
              {COLORS.map((c, i) => (
                <button key={c} onClick={() => setColorIdx(i)}
                  className={`w-5 h-5 rounded-full border-2 transition-all ${
                    colorIdx === i ? 'border-gray-800 scale-110' : 'border-transparent'
                  }`} style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
          <button onClick={() => setShowData(!showData)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 transition-colors">
            <Table2 size={14} /> {showData ? '\u1EA8n d\u1EEF li\u1EC7u' : 'Xem d\u1EEF li\u1EC7u'}
          </button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-4">
        {renderChart()}
      </div>

      {showData && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-4 py-2 bg-gray-50 border-b text-xs font-medium text-gray-500">D\u1EEF li\u1EC7u th\u00F4</div>
          <div className="overflow-x-auto max-h-60 overflow-y-auto">
            <table className="min-w-full text-xs">
              <thead className="bg-gray-50 sticky top-0">
                <tr>{allCols.map(col => <th key={col} className="px-3 py-2 text-left font-medium text-gray-500 border-b">{col}</th>)}</tr>
              </thead>
              <tbody>
                {chartData.slice(0, 50).map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    {allCols.map(col => <td key={col} className="px-3 py-1.5 border-b border-gray-100 text-gray-700">{row[col] == null ? '\u2014' : String(row[col])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}