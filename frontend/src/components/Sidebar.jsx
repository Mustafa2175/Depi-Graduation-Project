import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/dashboard',   icon: '📊', label: 'Overview' },
  { to: '/salary',      icon: '💰', label: 'Salary Explorer' },
  { to: '/demand',      icon: '🔥', label: 'Job Demand' },
  { to: '/companies',   icon: '🏢', label: 'Companies' },
  { to: '/skills',      icon: '🛠️', label: 'Skills' },
  { to: '/geography',   icon: '🗺️', label: 'Geography' },
  { to: '/trends',      icon: '📈', label: 'Hiring Trends' },
];

export default function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && <div className="sidebar-overlay" onClick={onClose} style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 99
      }} />}

      <aside className={`sidebar${isOpen ? ' open' : ''}`}>
        <div className="sidebar-brand">
          <div className="brand-icon">📡</div>
          <div>
            <h1>Job Market Tracker</h1>
            <span className="brand-sub">Egypt Analytics</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              onClick={onClose}
            >
              <span className="nav-icon">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        <div style={{ marginTop: 'auto', padding: '12px', borderTop: '1px solid var(--glass-border)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'center' }}>
            Data refreshed every 6 hours
          </div>
        </div>
      </aside>
    </>
  );
}
