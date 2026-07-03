import { useEffect, useState, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { fetchApi, formatNumber, CHART_COLORS, sortWithOtherLast } from '../api';
import Loading from '../components/Loading';

export default function Skills() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [category, setCategory] = useState('');
  const [limit, setLimit] = useState(20);

  // Unique categories from data for filter dropdown
  const [allCategories, setAllCategories] = useState([]);

  // Load all once for the dropdown, then filtered view
  useEffect(() => {
    fetchApi('skill-demand', { limit: 500 })
      .then(d => {
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
    fetchApi('skill-demand', { category, limit })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, limit]);

  useEffect(() => { load(); }, [load]);

  // Group by skill_name for chart
  const chartData = Object.values(
    data.reduce((acc, row) => {
      const key = row.skill_name || 'Unknown';
      if (!acc[key]) acc[key] = { name: key, postings: 0 };
      acc[key].postings += row.postings || 0;
      return acc;
    }, {})
  )
    .sort((a, b) => b.postings - a.postings)
    .slice(0, 15);

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)', borderRadius: 8, padding: '10px 14px' }}>
        <p style={{ color: 'var(--text-primary)', fontWeight: 600, marginBottom: 4 }}>{label}</p>
        <p style={{ color: CHART_COLORS[0], fontSize: '0.82rem' }}>Postings: {formatNumber(payload[0]?.value)}</p>
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h2>🛠️ Skills Demand</h2>
        <p>Most requested skills in job postings, by category.</p>
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
          <label>Show Top N</label>
          <select className="filter-select" value={limit} onChange={e => setLimit(Number(e.target.value))}>
            {[10, 20, 50, 100].map(n => <option key={n} value={n}>Top {n}</option>)}
          </select>
        </div>
      </div>

      {loading ? <Loading /> : error ? (
        <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>
      ) : (
        <>
          {/* Chart */}
          <div className="card chart-container" style={{ marginBottom: 24 }}>
            <h3 className="chart-title">📊 Top Skills by Postings</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ left: 10, right: 20, top: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} angle={-40} textAnchor="end" interval={0} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="postings" name="Postings" radius={[6, 6, 0, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <div className="card">
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Skill</th>
                    <th>Type</th>
                    <th>Category</th>
                    <th>Postings</th>
                    <th>Total Postings</th>
                  </tr>
                </thead>
                <tbody>
                  {sortWithOtherLast(data, 'category_name').map((r, i) => (
                    <tr key={i}>
                      <td>
                        <span className={`rank-badge ${r.overall_skill_rank === 1 ? 'rank-1' : r.overall_skill_rank === 2 ? 'rank-2' : r.overall_skill_rank === 3 ? 'rank-3' : 'rank-default'}`}>
                          {r.overall_skill_rank}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{r.skill_name || '—'}</td>
                      <td><span className="pill pill-cyan">{r.skill_category || '—'}</span></td>
                      <td>{r.category_name || '—'}</td>
                      <td className="number" style={{ color: 'var(--accent-1)' }}>{formatNumber(r.postings)}</td>
                      <td className="number">{formatNumber(r.total_postings)}</td>
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
