const fs = require("fs");

const content = `import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/layouts/AppLayout";
import Dashboard from "./pages/Dashboard";
import ScanRepository from "./pages/ScanRepository";
import Issues from "./pages/Issues";
import Profiler from "./pages/Profiler";
import CloudCarbon from "./pages/CloudCarbon";
import History from "./pages/History";
import Settings from "./pages/Settings";
import Overview from "./pages/Overview";
import Budgets from "./pages/Budgets";
import Policies from "./pages/Policies";
import Reports from "./pages/Reports";
import Deployments from "./pages/Deployments";
import Login from "./pages/Login";
import Terms from "./pages/Terms";
import Privacy from "./pages/Privacy";
import { useAuth } from "./context/AuthContext";

function ProtectedRoute({ children }: { children: React.ReactElement }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicAuthRoute({ children }: { children: React.ReactElement }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <FullScreenLoader />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicAuthRoute><Login /></PublicAuthRoute>} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/scan" element={<ScanRepository />} />
        <Route path="/issues" element={<Issues />} />
        <Route path="/profiler" element={<Profiler />} />
        <Route path="/cloud-carbon" element={<CloudCarbon />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/overview" element={<Overview />} />
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
    <div className="min-h-screen flex items-center justify-center bg-[#090b0a]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-mono text-emerald-400">Loading GreenCode...</span>
      </div>
    </div>
  );
}

export default App;
`;

fs.writeFileSync("frontend/src/App.tsx", content, { encoding: "utf8" });
console.log("Written App.tsx, size:", content.length);
console.log("First 4 bytes:", Buffer.from(content).slice(0, 4).toString());
