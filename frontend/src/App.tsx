import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layouts/AppLayout';
import Dashboard from './pages/Dashboard';
import ScanRepository from './pages/ScanRepository';
import Issues from './pages/Issues';
import Profiler from './pages/Profiler';
import CloudCarbon from './pages/CloudCarbon';
import History from './pages/History';
import Settings from './pages/Settings';
import Login from './pages/Login';
import ProtectedRoute from './components/layouts/ProtectedRoute';
import { useAuth } from './context/AuthContext';

/**
 * Enterprise Application Routing
 */
function App() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={isLoading ? <FullScreenLoader /> : isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />}
      />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/scan" element={<ScanRepository />} />
          <Route path="/issues" element={<Issues />} />
          <Route path="/cloud-carbon" element={<CloudCarbon />} />
          <Route path="/profiler" element={<Profiler />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>
      {/* Any unknown path lands on the dashboard; ProtectedRoute bounces to /login if needed. */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-10 h-10 border-[3px] border-emerald-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default App;
