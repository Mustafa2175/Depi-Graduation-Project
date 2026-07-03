import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { fetchApi, formatNumber, formatPct, CHART_COLORS } from '../api';
import Loading from '../components/Loading';

export default function Geography() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [region, setRegion] = useState('');

  const allRegions = [...new Set(data.map(r => r.region).filter(Boolean))].sort();

  useEffect(() => {
    setLoading(true);
    fetchApi('geographic-distribution', { region, limit: 200 })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [region]);

  // Aggregate by governorate for chart
  const govChartData = Object.values(
    data.reduce((acc, row) => {
      const key = row.governorate || 'Unknown';
      if (!acc[key]) acc[key] = { name: key, postings: 0, companies: 0 };
      acc[key].postings += row.postings || 0;
      acc[key].companies += row.hiring_companies || 0;
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
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color, fontSize: '0.82rem' }}>{p.name}: {formatNumber(p.value)}</p>
        ))}
      </div>
    );
  };

  return (
    <div>
      <div className="page-header">
        <h2>🗺️ Geographic Distribution</h2>
        <p>Where jobs are concentrated across Egypt's regions and governorates.</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Region</label>
          <select className="filter-select" value={region} onChange={e => setRegion(e.target.value)}>
            <option value="">All Regions</option>
            {allRegions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {loading ? <Loading /> : error ? (
        <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>
      ) : (
        <>
          {/* Stats row */}
          <div className="stats-grid" style={{ marginBottom: 24 }}>
            <div className="card stat-card">
              <div className="stat-icon">📍</div>
              <div className="stat-value">{data.length}</div>
              <div className="stat-label">Governorates</div>
            </div>
            <div className="card stat-card">
              <div className="stat-icon">📋</div>
              <div className="stat-value">{formatNumber(data.reduce((s, r) => s + (r.postings || 0), 0))}</div>
              <div className="stat-label">Total Postings</div>
            </div>
            <div className="card stat-card">
              <div className="stat-icon">🏢</div>
              <div className="stat-value">{formatNumber(data.reduce((s, r) => s + (r.hiring_companies || 0), 0))}</div>
              <div className="stat-label">Hiring Companies</div>
            </div>
            <div className="card stat-card">
              <div className="stat-icon">🏆</div>
              <div className="stat-value" style={{ fontSize: '1.1rem' }}>{govChartData[0]?.name || '—'}</div>
              <div className="stat-label">Top Governorate</div>
            </div>
          </div>

          {/* Bar chart */}
          <div className="card chart-container" style={{ marginBottom: 24 }}>
            <h3 className="chart-title">📊 Postings by Governorate</h3>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={govChartData} layout="vertical" margin={{ left: 20, right: 40, top: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={130} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="postings" name="Postings" radius={[0, 6, 6, 0]}>
                  {govChartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
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
                    <th>Region</th>
                    <th>Governorate</th>
                    <th>Postings</th>
                    <th>Cities</th>
                    <th>Companies</th>
                    <th>Avg Salary Mid</th>
                    <th>Remote</th>
                    <th>Market Share</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((r, i) => (
                    <tr key={i}>
                      <td><span className="pill pill-amber">{r.region || '—'}</span></td>
                      <td style={{ fontWeight: 600 }}>{r.governorate || '—'}</td>
                      <td className="number">{formatNumber(r.postings)}</td>
                      <td className="number">{formatNumber(r.cities)}</td>
                      <td className="number">{formatNumber(r.hiring_companies)}</td>
                      <td className="number" style={{ color: 'var(--accent-4)' }}>{r.avg_salary_mid ? formatNumber(r.avg_salary_mid) : '—'}</td>
                      <td className="number">{formatNumber(r.remote_postings)}</td>
                      <td><span className="pill pill-indigo">{formatPct(r.postings_share_pct)}</span></td>
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
