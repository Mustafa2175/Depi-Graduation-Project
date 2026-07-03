import { useEffect, useState, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { fetchApi, formatSalary, formatNumber, CHART_COLORS, sortWithOtherLast } from '../api';
import Loading from '../components/Loading';

export default function SalaryExplorer() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [category, setCategory] = useState('');
  const [seniority, setSeniority] = useState('');
  const [governorate, setGovernorate] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchApi('salary-intelligence', { category, seniority, governorate, limit: 200 })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, seniority, governorate]);

  useEffect(() => { load(); }, [load]);

  // Build chart — avg salary by category (top 10)
  const chartDataRaw = Object.values(
    data.reduce((acc, row) => {
      const key = row.category_name || 'Unknown';
      if (!acc[key]) acc[key] = { name: key, count: 0, totalMid: 0 };
      acc[key].count += 1;
      acc[key].totalMid += row.avg_salary_mid || 0;
      return acc;
    }, {})
  )
    .sort((a, b) => (b.count ? b.totalMid / b.count : 0) - (a.count ? a.totalMid / a.count : 0))
    .slice(0, 12);

  const chartData = sortWithOtherLast(chartDataRaw, 'name')
    .map(r => ({ name: r.name.length > 18 ? r.name.substring(0, 16) + '…' : r.name, avg_salary_mid: r.count ? Math.round(r.totalMid / r.count) : 0 }));

  const SENIORITIES = ['Senior', 'Mid', 'Junior', 'Unspecified'];

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)', borderRadius: 8, padding: '10px 14px' }}>
        <p style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: 4 }}>{label}</p>
        <p style={{ color: CHART_COLORS[0], fontSize: '0.82rem' }}>Avg Salary Mid: {formatNumber(payload[0]?.value)}</p>
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h2>💰 Salary Explorer</h2>
        <p>Explore salary ranges across roles, seniority levels, and Egyptian governorates.</p>
      </div>

      {/* Filters */}
      <div className="filters-bar">
        <div className="filter-group">
          <label>Category</label>
          <input className="filter-input" placeholder="e.g. Data Engineer" value={category}
            onChange={e => setCategory(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} />
        </div>
        <div className="filter-group">
          <label>Seniority</label>
          <select className="filter-select" value={seniority} onChange={e => setSeniority(e.target.value)}>
            <option value="">All</option>
            {SENIORITIES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="filter-group">
          <label>Governorate</label>
          <input className="filter-input" placeholder="e.g. Cairo" value={governorate}
            onChange={e => setGovernorate(e.target.value)} onKeyDown={e => e.key === 'Enter' && load()} />
        </div>
        <div className="filter-group" style={{ justifyContent: 'flex-end' }}>
          <label>&nbsp;</label>
          <button className="filter-select" onClick={load} style={{ cursor: 'pointer', background: 'var(--accent-1)', border: 'none', color: '#fff', fontWeight: 600 }}>
            Apply
          </button>
        </div>
      </div>

      {/* Chart */}
      {!loading && !error && chartData.length > 0 && (
        <div className="card chart-container" style={{ marginBottom: 24 }}>
          <h3 className="chart-title">📊 Avg Salary by Category (filtered view)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 40, top: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => formatNumber(v)} />
              <YAxis type="category" dataKey="name" width={150} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="avg_salary_mid" name="Avg Mid Salary" radius={[0, 6, 6, 0]}>
                {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div className="card">
        {loading ? <Loading /> : error ? (
          <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>
        ) : data.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">🔍</div><p>No results for these filters.</p></div>
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Seniority</th>
                  <th>Governorate</th>
                  <th>Postings w/ Salary</th>
                  <th>Floor</th>
                  <th>Avg Min</th>
                  <th>Avg Mid</th>
                  <th>Avg Max</th>
                  <th>Ceiling</th>
                  <th>Currency</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i}>
                    <td>{row.category_name || '—'}</td>
                    <td>
                      <span className={`pill pill-${row.seniority === 'Senior' ? 'indigo' : row.seniority === 'Mid' ? 'cyan' : row.seniority === 'Junior' ? 'emerald' : 'amber'}`}>
                        {row.seniority || '—'}
                      </span>
                    </td>
                    <td>{row.governorate || '—'}</td>
                    <td className="number">{formatNumber(row.postings_with_salary)}</td>
                    <td className="number">{formatNumber(row.salary_floor)}</td>
                    <td className="number">{formatNumber(row.avg_salary_min)}</td>
                    <td className="number" style={{ color: 'var(--accent-4)', fontWeight: 600 }}>{formatNumber(row.avg_salary_mid)}</td>
                    <td className="number">{formatNumber(row.avg_salary_max)}</td>
                    <td className="number">{formatNumber(row.salary_ceiling)}</td>
                    <td><span className="pill pill-rose">{row.currency || '—'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
