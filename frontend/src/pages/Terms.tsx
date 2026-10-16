import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Scale, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function Terms() {
  return (
    <div className="min-h-screen bg-[#fbfcfa] text-slate-800 font-sans py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl border border-slate-200/90 shadow-xl p-6 sm:p-10">
        
        {/* Navigation & Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-6 mb-8">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-xs sm:text-sm font-semibold text-emerald-800 hover:text-emerald-950 transition"
          >
            <ArrowLeft size={16} />
            <span>Back to Sign In</span>
          </Link>

          <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
            <span>Version 2.4</span>
            <span>·</span>
            <span>Effective Oct 2026</span>
          </div>
        </div>

        <div className="flex items-center gap-3.5 mb-6">
          <div className="w-10 h-10 rounded-xl bg-emerald-100/80 border border-emerald-300 flex items-center justify-center text-emerald-900">
            <Scale size={22} />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Terms of Service
            </h1>
            <p className="text-xs sm:text-sm text-slate-500">
              GreenCode Technologies Inc. Enterprise Software & API Agreement
            </p>
          </div>
        </div>

        <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 text-xs sm:text-sm text-emerald-950 flex items-start gap-3 mb-8">
          <CheckCircle2 size={18} className="text-emerald-700 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-emerald-900">Zero-Retention Code Architecture: </strong>
            GreenCode processes your source code and AST representations ephemerally in volatile memory. Customer source code is never stored on disk or used to train public machine learning foundation models.
          </div>
        </div>

        {/* Content sections */}
        <div className="space-y-6 text-xs sm:text-sm text-slate-600 leading-relaxed">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">1. Acceptance of Terms & Enterprise Authority</h2>
            <p>
              These Terms of Service ("Agreement") govern your access to and use of the GreenCode platform, APIs, dynamic execution profiler, and command-line interfaces operated by GreenCode Technologies Inc. ("GreenCode", "we", "us", or "our"). By authenticating via email, GitHub, Google, or Enterprise Single Sign-On (SSO), you agree to be bound by these terms on behalf of yourself and the organization you represent.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">2. Description of GreenCode Services</h2>
            <p className="mb-2">
              GreenCode delivers an enterprise-grade Green Software Engineering platform that measures, benchmarks, and optimizes the computational energy consumption and carbon intensity of software workloads. Core capabilities include:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
              <li><strong>Static AST Energy Audits:</strong> Multi-language static syntax analysis identifying algorithmic inefficiencies, redundant compute cycles, non-vectorized operations, and wasteful network round-trips.</li>
              <li><strong>Dynamic RAPL Sandboxed Profiling:</strong> Empirical hardware execution measurement via Running Average Power Limit (RAPL) energy counters and Linux kernel telemetry within isolated sandboxes.</li>
              <li><strong>Software Carbon Intensity (SCI) Calculation:</strong> Operational and embodied emissions quantification adhering to the Green Software Foundation SCI Specification (ISO/IEC standard track).</li>
              <li><strong>Cloud Telemetry Integration:</strong> Carbon footprint accounting across AWS, Azure, and Google Cloud workloads using read-only least-privilege telemetry scopes.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">3. Intellectual Property & Zero Code Retention</h2>
            <p>
              You retain all right, title, and interest in and to your source code, repositories, and build artifacts. GreenCode asserts zero ownership over customer code. All code analysis occurs ephemerally in isolated volatile sandboxes. Once the analysis completes and the audit summary metrics are delivered, code buffers are purged. We never store raw code in our database, nor do we disclose customer intellectual property to third parties or use it to train public AI models.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">4. User Authentication & Token Custody</h2>
            <p>
              Users must maintain the confidentiality of their credentials. When providing GitHub Personal Access Tokens (PATs) or cloud API keys, tokens are stored solely in your browser's runtime memory session under our Zero-Knowledge security architecture and forwarded via encrypted TLS headers per request. The GreenCode server does not persist your third-party provider access tokens in persistent relational storage.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">5. Acceptable Use Policy</h2>
            <p className="mb-2">You agree not to:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
              <li>Attempt to compromise the security, container isolation, or sandboxing mechanisms of the runtime execution profiler.</li>
              <li>Submit malicious code, ransomware, or cryptocurrency mining payloads to execution queues.</li>
              <li>Use GreenCode's calculation models to generate intentionally deceptive or misleading ESG/sustainability disclosures.</li>
              <li>Reverse engineer, decompile, or disassemble proprietary AST optimization algorithms or SCI calculation engines.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">6. Carbon Accounting Disclaimers</h2>
            <p>
              Carbon emission estimates and SCI scores are calculated based on peer-reviewed Green Software Foundation standards, the GHG Protocol Corporate Standard, and regional grid carbon intensity datasets (e.g., WattTime, ElectricityMaps). While GreenCode strives for high scientific precision, estimations depend on cloud vendor operational transparency and grid reporting frequencies. GreenCode carbon scores are provided "as is" for operational engineering and sustainability optimization.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">7. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by applicable law, GreenCode and its suppliers shall not be liable for any indirect, incidental, punitive, or consequential damages, including loss of profits, data corruption, or downtime. GreenCode's aggregate liability under this agreement shall not exceed the total fees paid by you to GreenCode in the twelve (12) months preceding the claim.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">8. Termination & Workspace Purge</h2>
            <p>
              You may terminate your account at any time via Settings. Upon termination, all tenant configurations, carbon budgets, policies, and audit logs are queued for permanent cryptographic erasure in accordance with SOC 2 Type II retention cycles.
            </p>
          </div>

          <div className="pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
            <span>© 2026 GreenCode Technologies Inc. All rights reserved.</span>
            <Link to="/privacy" className="text-emerald-800 hover:underline">
              View Privacy Policy
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
