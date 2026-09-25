import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layouts/AppLayout';
import Dashboard from './pages/Dashboard';
import ScanRepository from './pages/ScanRepository';
import Issues from './pages/Issues';
import Profiler from './pages/Profiler';
import History from './pages/History';
import Settings from './pages/Settings';

function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/scan" element={<ScanRepository />} />
        <Route path="/issues" element={<Issues />} />
        <Route path="/profiler" element={<Profiler />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
