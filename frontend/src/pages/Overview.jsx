import { useEffect, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import { fetchApi, formatNumber, formatPct, formatSalary, CHART_COLORS, sortWithOtherLast } from '../api';
import Loading from '../components/Loading';

export default function Overview() {
  const [roles, setRoles] = useState([]);
  const [workMode, setWorkMode] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchApi('in-demand-roles', { limit: 100 }),
      fetchApi('work-mode-breakdown'),
    ])
      .then(([r, w]) => {
        setRoles(r);
        setWorkMode(w);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (error) return <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>;

  const sortedRoles = sortWithOtherLast(roles, 'category_name');
  const totalPostings = roles.reduce((s, r) => s + (r.postings || 0), 0);
  const topRole = sortedRoles[0];
  const remotePct = workMode.find(w => w.facet === 'work_mode' && w.value === 'remote')?.share_pct;
  const fullTimePct = workMode.find(w => w.facet === 'employment_type' && w.value === 'full-time')?.share_pct;

  const workModePie = workMode
    .filter(w => w.facet === 'work_mode')
    .map(w => ({ name: w.value?.replace(/_/g, ' '), value: w.postings }));

  const employTypePie = workMode
    .filter(w => w.facet === 'employment_type')
    .map(w => ({ name: w.value?.replace(/-/g, ' '), value: w.postings }));

  const topRolesBarRaw = roles.slice(0, 10);
  const topRolesBar = sortWithOtherLast(topRolesBarRaw, 'category_name').map(r => ({
    name: r.category_name?.length > 18 ? r.category_name.substring(0, 16) + '…' : r.category_name,
    postings: r.postings,
    salary: r.avg_salary_mid,
  }));

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
        <h2>📊 Market Overview</h2>
        <p>High-level snapshot of the Egyptian job market from the latest pipeline run.</p>
      </div>

      {/* Stat cards */}
      <div className="stats-grid">
        <div className="card stat-card">
          <div className="stat-icon">📋</div>
          <div className="stat-value">{formatNumber(totalPostings)}</div>
          <div className="stat-label">Total Postings</div>
        </div>
        <div className="card stat-card">
          <div className="stat-icon">🏆</div>
          <div className="stat-value" style={{ fontSize: '1.15rem' }}>{topRole?.category_name || '—'}</div>
          <div className="stat-label">Top Role Category</div>
        </div>
        <div className="card stat-card">
          <div className="stat-icon">🌐</div>
          <div className="stat-value">{formatPct(remotePct)}</div>
          <div className="stat-label">Remote Jobs</div>
        </div>
        <div className="card stat-card">
          <div className="stat-icon">💼</div>
          <div className="stat-value">{formatPct(fullTimePct)}</div>
          <div className="stat-label">Full-Time Roles</div>
        </div>
      </div>

      {/* Charts row */}
      <div className="two-col-grid">
        <div className="card">
          <h3 className="chart-title">🏷️ Work Mode Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={workModePie} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {workModePie.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v) => formatNumber(v)} contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="chart-title">📑 Employment Type Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={employTypePie} cx="50%" cy="50%" outerRadius={90} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {employTypePie.map((_, i) => <Cell key={i} fill={CHART_COLORS[(i + 3) % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v) => formatNumber(v)} contentStyle={{ background: 'var(--bg-secondary)', border: '1px solid var(--glass-border)', borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top roles bar chart */}
      <div className="card chart-container">
        <h3 className="chart-title">🔥 Top 10 In-Demand Roles</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={topRolesBar} layout="vertical" margin={{ left: 20, right: 30, top: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
            <YAxis type="category" dataKey="name" width={140} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="postings" name="Postings" radius={[0, 6, 6, 0]}>
              {topRolesBar.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
