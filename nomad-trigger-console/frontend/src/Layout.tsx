import { NavLink, Outlet } from 'react-router-dom';
import { LayoutGrid, PlusCircle, Inbox, Zap } from 'lucide-react';
import './App.css';

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>NOMAD</h1>
          <span>Trigger Console · MVP</span>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <LayoutGrid size={18} /> Trigger Explorer
          </NavLink>
          <NavLink to="/builder" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <PlusCircle size={18} /> New Trigger
          </NavLink>
          <NavLink to="/queue" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            <Inbox size={18} /> Message Queue
          </NavLink>
        </nav>
        <div style={{ padding: '1.25rem', marginTop: 'auto' }}>
          <div className="sim-banner" style={{ marginBottom: 0, fontSize: '0.75rem' }}>
            <Zap size={14} /> Simulation mode — no live sends
          </div>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
