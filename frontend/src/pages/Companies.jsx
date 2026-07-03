import { useEffect, useState } from 'react';
import { fetchApi, formatNumber } from '../api';
import Loading from '../components/Loading';

export default function Companies() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(50);
  const [governorate, setGovernorate] = useState('');
  const [sortKey, setSortKey] = useState('hiring_rank');
  const [sortDir, setSortDir] = useState('asc');

  useEffect(() => {
    setLoading(true);
    fetchApi('company-insights', { limit, governorate })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [limit, governorate]);

  const sorted = [...data].sort((a, b) => {
    const va = a[sortKey] ?? (sortDir === 'asc' ? Infinity : -Infinity);
    const vb = b[sortKey] ?? (sortDir === 'asc' ? Infinity : -Infinity);
    return sortDir === 'asc' ? va - vb : vb - va;
  });

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>⇅</span>;
    return <span style={{ color: 'var(--accent-1)', marginLeft: 4 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div>
      <div className="page-header">
        <h2>🏢 Company Profiles</h2>
        <p>Top hiring companies in Egypt, sortable by any metric.</p>
      </div>

      <div className="filters-bar">
        <div className="filter-group">
          <label>Governorate</label>
          <input className="filter-input" placeholder="e.g. Cairo" value={governorate}
            onChange={e => setGovernorate(e.target.value)} />
        </div>
        <div className="filter-group">
          <label>Show Top N</label>
          <select className="filter-select" value={limit} onChange={e => setLimit(Number(e.target.value))}>
            {[25, 50, 100].map(n => <option key={n} value={n}>Top {n}</option>)}
          </select>
        </div>
      </div>

      <div className="card">
        {loading ? <Loading /> : error ? (
          <div className="empty-state"><div className="empty-icon">⚠️</div><p>{error}</p></div>
        ) : sorted.length === 0 ? (
          <div className="empty-state"><div className="empty-icon">🔍</div><p>No results found.</p></div>
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => toggleSort('hiring_rank')} style={{ cursor: 'pointer' }}>Rank <SortIcon col="hiring_rank" /></th>
                  <th>Company</th>
                  <th onClick={() => toggleSort('postings')} style={{ cursor: 'pointer' }}>Postings <SortIcon col="postings" /></th>
                  <th onClick={() => toggleSort('distinct_categories')} style={{ cursor: 'pointer' }}>Categories <SortIcon col="distinct_categories" /></th>
                  <th onClick={() => toggleSort('distinct_governorates')} style={{ cursor: 'pointer' }}>Governorates <SortIcon col="distinct_governorates" /></th>
                  <th onClick={() => toggleSort('avg_salary_mid')} style={{ cursor: 'pointer' }}>Avg Salary Mid <SortIcon col="avg_salary_mid" /></th>
                  <th onClick={() => toggleSort('remote_postings')} style={{ cursor: 'pointer' }}>Remote <SortIcon col="remote_postings" /></th>
                  <th>Top Category</th>
                  <th>Top Governorate</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => (
                  <tr key={i}>
                    <td>
                      <span className={`rank-badge ${r.hiring_rank === 1 ? 'rank-1' : r.hiring_rank === 2 ? 'rank-2' : r.hiring_rank === 3 ? 'rank-3' : 'rank-default'}`}>
                        {r.hiring_rank}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{r.company_name || '—'}</td>
                    <td className="number">{formatNumber(r.postings)}</td>
                    <td className="number">{formatNumber(r.distinct_categories)}</td>
                    <td className="number">{formatNumber(r.distinct_governorates)}</td>
                    <td className="number" style={{ color: 'var(--accent-4)' }}>{r.avg_salary_mid ? formatNumber(r.avg_salary_mid) : '—'}</td>
                    <td className="number">{formatNumber(r.remote_postings)}</td>
                    <td><span className="pill pill-indigo">{r.top_category || '—'}</span></td>
                    <td>{r.top_governorate || '—'}</td>
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
