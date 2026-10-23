import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import AppLayout from "./components/layouts/AppLayout";
import Dashboard from "./pages/Overview";
import ScanRepository from "./pages/ScanRepository";
import Issues from "./pages/Issues";
import Profiler from "./pages/Profiler";
import CloudCarbon from "./pages/CloudCarbon";
import History from "./pages/History";
import Settings from "./pages/Settings";
import Budgets from "./pages/Budgets";
import Policies from "./pages/Policies";
import Reports from "./pages/Reports";
import Deployments from "./pages/Deployments";
import Login from "./pages/Login";
import Terms from "./pages/Terms";
import Privacy from "./pages/Privacy";
import AlexaDemo from "./pages/AlexaDemo";
import { useAuth } from "./context/AuthContext";

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <FullScreenLoader />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />;
  }
  return children;
}

function PublicAuthRoute({ children }: { children: React.ReactElement }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  if (isLoading) return <FullScreenLoader />;
  const callbackParams = new URLSearchParams(location.search);
  const isOAuthCallback = callbackParams.has('code') || callbackParams.has('error');
  if (user && !isOAuthCallback) return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicAuthRoute><Login /></PublicAuthRoute>} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/alexa-demo" element={<AlexaDemo />} />
      
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      
      {/* Other pages use AppLayout with dark theme */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/scan" element={<ScanRepository />} />
        <Route path="/issues" element={<Issues />} />
        <Route path="/profiler" element={<Profiler />} />
        <Route path="/cloud-carbon" element={<CloudCarbon />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/overview" element={<Navigate to="/dashboard" replace />} />
        <Route path="/budgets" element={<Budgets />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/deployments" element={<Deployments />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function FullScreenLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f7f6]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-mono text-emerald-600">Loading GreenCode...</span>
      </div>
    </div>
  );
}

export default App;