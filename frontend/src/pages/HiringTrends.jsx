import { useEffect, useState, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts';
import { fetchApi, formatNumber, CHART_COLORS } from '../api';
import Loading from '../components/Loading';

export default function HiringTrends() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [category, setCategory] = useState('');
  const [year, setYear] = useState('');
  const [allCategories, setAllCategories] = useState([]);

  // Load once for dropdown options
  useEffect(() => {
    fetchApi('hiring-trends', { limit: 1000 }).then(d => {
      let cats = [...new Set(d.map(r => r.category_name).filter(Boolean))].sort();
      if (cats.includes('Other')) {
        cats = cats.filter(c => c !== 'Other');
        cats.push('Other');
      }
      setAllCategories(cats);
    });
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchApi('hiring-trends', { category, year: year || undefined, limit: 1000 })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, year]);

  useEffect(() => { load(); }, [load]);

  // Build chart data: x = "Month Year", series = one line per category
  let categories = [...new Set(data.map(r => r.category_name).filter(Boolean))];
  if (categories.includes('Other')) {
    categories = categories.filter(c => c !== 'Other');
    categories.push('Other');
  }

  // Pivot: { "Jun 2026": { "Data Engineering": 5, ... } }
  const pivot = {};
  data.forEach(row => {
    const label = `${row.month_name?.substring(0, 3)} ${row.year}`;
    if (!pivot[label]) pivot[label] = { label };
    pivot[label][row.category_name] = (pivot[label][row.category_name] || 0) + (row.postings || 0);
  });

  // Sort chronologically
  const chartData = Object.values(pivot).sort((a, b) => {
    const [am, ay] = a.label.split(' ');
    const [bm, by] = b.label.split(' ');
    return (Number(ay) * 12 + monthIndex(am)) - (Number(by) * 12 + monthIndex(bm));
  });

  function monthIndex(abbr) {
    return ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].indexOf(abbr);
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)', borderRadius: 8, padding: '12px 16px', minWidth: 200 }}>
        <p style={{ color: 'var(--text-primary)', fontWeight: 700, marginBottom: 8 }}>{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color, fontSize: '0.82rem', marginBottom: 2 }}>
            {p.name}: {formatNumber(p.value)}
          </p>
        ))}
      </div>
    );
  };

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  return (
    <div>
      <div className="page-header">
        <h2>📈 Hiring Trends</h2>
        <p>Monthly hiring activity over time — spot when demand spikes and which roles are growing.</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Category</label>
          <select className="filter-select" value={category} onChange={e => setCategory(e.target.value)}>
            <option value="">All Categories</option>
            {allCategories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Year</label>
          <select className="filter-select" value={year} onChange={e => setYear(e.target.value)}>
            <option value="">All Years</option>
            {years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>

      {loading ? <Loading /> : error ? (
        <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>
      ) : chartData.length === 0 ? (
        <div className="empty-state"><div className="empty-icon">📊</div><p>No trend data for selected filters.</p></div>
      ) : (
        <>
          {/* Line chart */}
          <div className="card chart-container" style={{ marginBottom: 24 }}>
            <h3 className="chart-title">📈 Monthly Postings Over Time</h3>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={chartData} margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: 'var(--text-secondary)', fontSize: '0.8rem', paddingTop: 12 }} />
                {categories.slice(0, 8).map((cat, i) => (
                  <Line
                    key={cat}
                    type="monotone"
                    dataKey={cat}
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4, fill: CHART_COLORS[i % CHART_COLORS.length] }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Raw table */}
          <div className="card">
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Year</th>
                    <th>Month</th>
                    <th>Category</th>
                    <th>Postings</th>
                    <th>Companies Hiring</th>
                    <th>Avg Salary Mid</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((r, i) => (
                    <tr key={i}>
                      <td className="number">{r.year}</td>
                      <td>{r.month_name}</td>
                      <td style={{ fontWeight: 500 }}>{r.category_name || '—'}</td>
                      <td className="number" style={{ color: 'var(--accent-1)' }}>{formatNumber(r.postings)}</td>
                      <td className="number">{formatNumber(r.hiring_companies)}</td>
                      <td className="number" style={{ color: 'var(--accent-4)' }}>{r.avg_salary_mid ? formatNumber(r.avg_salary_mid) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
