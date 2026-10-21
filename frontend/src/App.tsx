import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import GreenCodeAuditorApp from './GreenCodeAuditorApp';
import Login from './pages/Login';
import Terms from './pages/Terms';
import Privacy from './pages/Privacy';
import { useAuth } from './context/AuthContext';

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return children;
}

function PublicAuthRoute({ children }: { children: React.ReactElement }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <FullScreenLoader />;
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicAuthRoute>
            <Login />
          </PublicAuthRoute>
        }
      />
      <Route path="/terms" element={<Terms />} />
      <Route path="/privacy" element={<Privacy />} />

      {/* Enterprise-Grade GreenCode Auditor Platform (Clean Mint + Slate Workspace) */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <GreenCodeAuditorApp />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <GreenCodeAuditorApp />
          </ProtectedRoute>
        }
      />
      <Route
        path="/scan"
        element={
          <ProtectedRoute>
            <GreenCodeAuditorApp />
          </ProtectedRoute>
        }
      />
      <Route
        path="/issues"
        element={
          <ProtectedRoute>
            <GreenCodeAuditorApp />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-10 h-10 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin"
          role="status"
          aria-label="Loading"
        />
        <span className="text-xs font-mono font-semibold text-slate-700">Loading GreenCode...</span>
      </div>
    </div>
  );
}

export default App;
