import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Overview from './pages/Overview';
import SalaryExplorer from './pages/SalaryExplorer';
import JobDemand from './pages/JobDemand';
import Companies from './pages/Companies';
import Skills from './pages/Skills';
import Geography from './pages/Geography';
import HiringTrends from './pages/HiringTrends';
import LandingPage from './pages/LandingPage';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <Routes>
        {/* Landing Page Route (Fullscreen, no Sidebar) */}
        <Route path="/" element={<LandingPage />} />

        {/* Dashboard Routes (with Sidebar and Layout) */}
        <Route
          path="/*"
          element={
            <div className="app-layout">
              <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

              {/* Mobile header */}
              <header className="mobile-header">
                <button className="hamburger" onClick={() => setSidebarOpen(o => !o)}>☰</button>
                <span style={{ marginLeft: 12, fontWeight: 700, fontSize: '1rem' }}>Job Market Tracker</span>
              </header>

              <main className="main-content">
                <Routes>
                  <Route path="/dashboard"  element={<Overview />} />
                  <Route path="/salary"     element={<SalaryExplorer />} />
                  <Route path="/demand"     element={<JobDemand />} />
                  <Route path="/companies"  element={<Companies />} />
                  <Route path="/skills"     element={<Skills />} />
                  <Route path="/geography"  element={<Geography />} />
                  <Route path="/trends"     element={<HiringTrends />} />
                </Routes>
              </main>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
