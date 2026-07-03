import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, Legend,
} from 'recharts';
import { fetchApi, formatNumber, formatPct, CHART_COLORS, sortWithOtherLast } from '../api';
import Loading from '../components/Loading';

export default function JobDemand() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(15);

  useEffect(() => {
    setLoading(true);
    fetchApi('in-demand-roles', { limit })
      .then(setRoles)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit]);

  const sortedRoles = sortWithOtherLast(roles, 'category_name');
  
  const chartData = sortedRoles.map(r => ({
    name: r.category_name?.length > 22 ? r.category_name.substring(0, 20) + '…' : r.category_name,
    Postings: r.postings,
    Companies: r.hiring_companies,
    Remote: r.remote_postings,
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const role = sortedRoles.find(r => (r.category_name?.substring(0, 20)) === label.replace('…', '') || r.category_name === label);
    return (
      <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)', borderRadius: 8, padding: '12px 16px', minWidth: 200 }}>
        <p style={{ color: 'var(--text-primary)', fontWeight: 700, marginBottom: 8 }}>{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color, fontSize: '0.82rem', marginBottom: 2 }}>{p.name}: {formatNumber(p.value)}</p>
        ))}
        {role && <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 6 }}>Demand Share: {formatPct(role.demand_share_pct)}</p>}
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h2>🔥 Job Demand</h2>
        <p>Which job categories are hiring most actively right now.</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Show Top N</label>
          <select className="filter-select" value={limit} onChange={e => setLimit(Number(e.target.value))}>
            {[5, 10, 15, 20, 50].map(n => <option key={n} value={n}>Top {n}</option>)}
          </select>
        </div>
      </div>

      {loading ? <Loading /> : error ? (
        <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>
      ) : (
        <>
          <div className="card chart-container" style={{ marginBottom: 24 }}>
            <h3 className="chart-title">📊 Postings by Category</h3>
            <ResponsiveContainer width="100%" height={Math.max(300, roles.length * 38)}>
              <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 40, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={170} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }} />
                <Bar dataKey="Postings" radius={[0, 6, 6, 0]}>
                  {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                </Bar>
                <Bar dataKey="Remote" fill="rgba(16,185,129,0.5)" radius={[0, 6, 6, 0]} />
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
                    <th>Category</th>
                    <th>Postings</th>
                    <th>Companies</th>
                    <th>Remote</th>
                    <th>Demand Share</th>
                    <th>Posts / Company</th>
                    <th>Avg Salary Mid</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRoles.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <span className={`rank-badge ${i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-default'}`}>
                          {r.demand_rank}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{r.category_name}</td>
                      <td className="number">{formatNumber(r.postings)}</td>
                      <td className="number">{formatNumber(r.hiring_companies)}</td>
                      <td className="number">{formatNumber(r.remote_postings)}</td>
                      <td>
                        <span className="pill pill-indigo">{formatPct(r.demand_share_pct)}</span>
                      </td>
                      <td className="number">{r.postings_per_company ? Number(r.postings_per_company).toFixed(1) : '—'}</td>
                      <td className="number">{r.avg_salary_mid ? formatNumber(r.avg_salary_mid) : '—'}</td>
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
