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

      {/* Enterprise-Grade GreenCode Auditor Platform (Protected SaaS Workflow) */}
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
        path="/auditor"
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
    <div className="min-h-screen flex items-center justify-center bg-[linear-gradient(135deg,#c3eed0_0%,#d8f5e2_20%,#f0fcf5_38%,#b6e8c5_50%,#e4f9ec_70%,#c8f0d5_100%)]">
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-10 h-10 border-3 border-[#003d20] border-t-transparent rounded-full animate-spin"
          role="status"
          aria-label="Loading"
        />
        <span className="text-xs font-mono font-semibold text-[#003d20]">Loading GreenCode...</span>
      </div>
    </div>
  );
}

export default App;
