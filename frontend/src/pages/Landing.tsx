import { Link } from 'react-router-dom';
import { theme } from '../styles/theme';

export default function Landing() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-mint-50 via-white to-mint-100">
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-40 bg-white/80 backdrop-blur border-b border-mint-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="GreenCode" className="h-9 w-9 rounded-full" />
            <span className="font-black text-xl text-mint-800">GreenCode</span>
            <span className="text-slate-400 text-sm font-medium">Auditor</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-slate-600 hover:text-mint-700 font-medium text-sm">
              Sign In
            </Link>
            <Link to="/signup" className="btn-primary text-sm">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-mint-100/50 rounded-full border border-mint-300 mb-6">
            <span className="text-mint-700 font-medium text-sm">Green Software Foundation SCI v1.0</span>
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-black text-slate-900 mb-6 leading-tight">
            Build Sustainable Code.
            <br />
            <span style={{ color: theme.colors.primary }}>Audit. Optimize. Automate.</span>
          </h1>

          <p className="text-lg text-slate-600 max-w-3xl mx-auto mb-8">
            GreenCode Auditor identifies energy-inefficient patterns, measures real carbon
            emissions, and auto-refactors your code to reduce CPU cycles, memory waste,
            and network overhead — all backed by live grid carbon intensity data.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/signup" className="btn-primary text-lg flex items-center justify-center gap-2">
              Start Auditing Free
            </Link>
            <Link
              to="/login"
              className="btn-secondary text-lg flex items-center justify-center gap-2"
            >
              Sign In to Continue
            </Link>
          </div>
        </div>

        {/* Feature Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          <FeatureCard
            icon="🔍"
            title="Static Analysis"
            desc="500+ language support via Tree-sitter CST and Python AST"
          />
          <FeatureCard
            icon="📊"
            title="Dynamic Profiling"
            desc="Docker-isolated runtime measurement of CPU, RAM, and energy"
          />
          <FeatureCard
            icon="🌍"
            title="Live Grid Data"
            desc="Real-time carbon intensity from Electricity Maps API"
          />
          <FeatureCard
            icon="⚡"
            title="Auto-Refactoring"
            desc="AI-powered or deterministic eco-code optimization"
          />
        </div>

        {/* GSF Patterns */}
        <div className="bg-white rounded-2xl border border-mint-200 p-8 mb-16">
          <h2 className="text-2xl font-black text-center text-slate-900 mb-8">
            Green Software Foundation Patterns Enforced
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <PatternCard
              badge="CRITICAL"
              badgeColor="bg-red-100 text-red-800 border-red-200"
              title="Un-cached Network Call In Loop"
              desc="Synchronous HTTP inside iterations triggers repeated NIC wakeups and TLS handshake overhead."
            />
            <PatternCard
              badge="HIGH"
              badgeColor="bg-amber-100 text-amber-800 border-amber-200"
              title="Deep Nested Iteration (O(N³))"
              desc="3+ level nested loops escalate CPU instruction cycles and thermal power dissipation."
            />
            <PatternCard
              badge="HIGH"
              badgeColor="bg-amber-100 text-amber-800 border-amber-200"
              title="Unmanaged Database Cursor"
              desc="Cursors without context managers risk socket leakage and idle connection persistence."
            />
            <PatternCard
              badge="MEDIUM"
              badgeColor="bg-mint-100 text-mint-800 border-mint-200"
              title="Quadratic String Concatenation"
              desc="+=' string concat in loops causes O(N²) memory reallocations and GC thrashing."
            />
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center text-slate-400 text-sm pt-8 border-t border-mint-200">
          <p>© 2026 GreenCode Auditor — Built for the Green Software Foundation</p>
        </footer>
      </main>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="card p-6 text-center group transition-all duration-300">
      <div className="text-4xl mb-3">{icon}</div>
      <h3 className="font-bold text-lg text-slate-900 mb-2 group-hover:" style={{ color: theme.colors.primary }}>
        {title}
      </h3>
      <p className="text-sm text-slate-600">{desc}</p>
    </div>
  );
}

function PatternCard({ badge, badgeColor, title, desc }: {
  badge: string;
  badgeColor: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="border border-slate-200 rounded-lg p-4">
      <span className={`inline-block px-2.5 py-1 rounded text-xs font-bold mb-2 ${badgeColor}`}>
        {badge}
      </span>
      <h4 className="font-bold text-slate-900 mb-1">{title}</h4>
      <p className="text-sm text-slate-600">{desc}</p>
    </div>
  );
}
