import React, { useState } from 'react';
import { X, ShieldCheck, FileText, Download, CheckCircle2, ChevronRight, Scale } from 'lucide-react';

interface LegalModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'terms' | 'privacy';
}

export default function LegalModal({ isOpen, onClose, initialTab = 'terms' }: LegalModalProps) {
  const [activeTab, setActiveTab] = useState<'terms' | 'privacy'>(initialTab);

  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      
      {/* Modal Dialog Container */}
      <div 
        className="bg-white rounded-2xl border border-slate-200/90 shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden text-slate-800"
        role="dialog"
        aria-modal="true"
      >
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-100/70 border border-emerald-200 flex items-center justify-center text-emerald-800">
              <Scale size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                GreenCode Legal & Compliance Portal
              </h3>
              <p className="text-xs text-slate-500">
                Global Standards: ISO 14064 · GHG Protocol · GSF SCI v1.0 · SOC 2 · GDPR/CCPA
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              type="button"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
              title="Print or Save as PDF"
            >
              <Download size={16} />
            </button>
            <button
              onClick={onClose}
              type="button"
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 px-6 bg-white shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('terms')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'terms'
                ? 'border-emerald-600 text-emerald-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <FileText size={14} />
            <span>Terms of Service</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
              v2.4
            </span>
          </button>
          
          <button
            type="button"
            onClick={() => setActiveTab('privacy')}
            className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition cursor-pointer ${
              activeTab === 'privacy'
                ? 'border-emerald-600 text-emerald-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <ShieldCheck size={14} />
            <span>Privacy Policy</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-mono">
              Zero-Retention
            </span>
          </button>
        </div>

        {/* Modal Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6 text-xs sm:text-sm text-slate-600 leading-relaxed font-sans">
          
          {activeTab === 'terms' ? (
            <div className="space-y-6 animate-in fade-in duration-150">
              
              <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4 text-xs text-emerald-950 flex items-start gap-3">
                <CheckCircle2 size={16} className="text-emerald-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold text-emerald-900">Zero-Retention Code Architecture: </strong>
                  GreenCode processes your source code and AST representations ephemerally in volatile memory. Customer source code is never retained on disk or used to train public machine learning foundation models.
                </div>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">1. Acceptance of Terms & Enterprise Authority</h4>
                <p>
                  These Terms of Service ("Agreement") govern your access to and use of the GreenCode platform, APIs, dynamic execution profiler, and command-line interfaces operated by GreenCode Technologies Inc. ("GreenCode", "we", "us", or "our"). By authenticating via email, GitHub, Google, or Enterprise Single Sign-On (SSO), you agree to be bound by these terms on behalf of yourself and the organization you represent.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">2. Description of GreenCode Services</h4>
                <p className="mb-2">
                  GreenCode delivers an enterprise-grade Green Software Engineering platform that measures, benchmarks, and optimizes the computational energy consumption and carbon intensity of software workloads. Core capabilities include:
                </p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>Static AST Energy Audits:</strong> Multi-language static syntax analysis identifying algorithmic inefficiencies, redundant compute cycles, non-vectorized operations, and wasteful network round-trips.</li>
                  <li><strong>Dynamic RAPL Sandboxed Profiling:</strong> Empirical hardware execution measurement via Running Average Power Limit (RAPL) energy counters and Linux kernel telemetry within isolated sandboxes.</li>
                  <li><strong>Software Carbon Intensity (SCI) Calculation:</strong> Operational and embodied emissions quantification adhering to the Green Software Foundation SCI Specification (ISO/IEC standard track).</li>
                  <li><strong>Cloud Telemetry Integration:</strong> Carbon footprint accounting across AWS, Azure, and Google Cloud workloads using read-only least-privilege telemetry scopes.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">3. Intellectual Property & Zero Code Retention</h4>
                <p>
                  You retain all right, title, and interest in and to your source code, repositories, and build artifacts. GreenCode asserts zero ownership over customer code. All code analysis occurs ephemerally in isolated volatile sandboxes. Once the analysis completes and the audit summary metrics are delivered, code buffers are purged. We never store raw code in our database, nor do we disclose customer intellectual property to third parties or use it to train public AI models.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">4. User Authentication & Token Custody</h4>
                <p>
                  Users must maintain the confidentiality of their credentials. When providing GitHub Personal Access Tokens (PATs) or cloud API keys, tokens are stored solely in your browser's runtime memory session under our Zero-Knowledge security architecture and forwarded via encrypted TLS headers per request. The GreenCode server does not persist your third-party provider access tokens in persistent relational storage.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">5. Acceptable Use Policy</h4>
                <p className="mb-2">You agree not to:</p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li>Attempt to compromise the security, container isolation, or sandboxing mechanisms of the runtime execution profiler.</li>
                  <li>Submit malicious code, ransomware, or cryptocurrency mining payloads to execution queues.</li>
                  <li>Use GreenCode's calculation models to generate intentionally deceptive or misleading ESG/sustainability disclosures.</li>
                  <li>Reverse engineer, decompile, or disassemble proprietary AST optimization algorithms or SCI calculation engines.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">6. Carbon Accounting Disclaimers</h4>
                <p>
                  Carbon emission estimates and SCI scores are calculated based on peer-reviewed Green Software Foundation standards, the GHG Protocol Corporate Standard, and regional grid carbon intensity datasets (e.g., WattTime, ElectricityMaps). While GreenCode strives for high scientific precision, estimations depend on cloud vendor operational transparency and grid reporting frequencies. GreenCode carbon scores are provided "as is" for operational engineering and sustainability optimization.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">7. Limitation of Liability</h4>
                <p>
                  To the maximum extent permitted by applicable law, GreenCode and its suppliers shall not be liable for any indirect, incidental, punitive, or consequential damages, including loss of profits, data corruption, or downtime. GreenCode's aggregate liability under this agreement shall not exceed the total fees paid by you to GreenCode in the twelve (12) months preceding the claim.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">8. Termination & Workspace Purge</h4>
                <p>
                  You may terminate your account at any time via Settings. Upon termination, all tenant configurations, carbon budgets, policies, and audit logs are queued for permanent cryptographic erasure in accordance with SOC 2 Type II retention cycles.
                </p>
              </div>

              <div className="pt-4 border-t border-slate-100 text-xs text-slate-400">
                Last updated: October 2026 · GreenCode Technologies Inc. Legal & Compliance Division
              </div>

            </div>
          ) : (
            <div className="space-y-6 animate-in fade-in duration-150">
              
              <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-4 text-xs text-emerald-950 flex items-start gap-3">
                <ShieldCheck size={16} className="text-emerald-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold text-emerald-900">GDPR & CCPA/CPRA Compliance Guarantee: </strong>
                  We adhere to strict data minimization principles. We do not sell your personal information, monetize usage data, or share developer telemetry with data brokers.
                </div>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">1. Data Controller & Scope</h4>
                <p>
                  This Privacy Policy outlines how GreenCode Technologies Inc. ("GreenCode") collects, processes, and protects personal information through our platform, developer portal, and APIs. GreenCode acts as the Data Controller for account management data, and as a Data Processor regarding enterprise customer team configurations.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">2. Information We Collect</h4>
                <p className="mb-2">We collect only information essential to providing the service:</p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>Account Identity:</strong> Email address, username, full name, encrypted password hash (bcrypt with salted rounds), and organization affiliation.</li>
                  <li><strong>OAuth Identity:</strong> GitHub or Google public user ID, username, and public avatar URL when signing in via social or SSO identity providers.</li>
                  <li><strong>Security & Operational Telemetry:</strong> IP addresses, browser user-agent, session timestamps, and cryptographic audit logs recorded for SOC 2 Type II compliance.</li>
                  <li><strong>Audit Metadata:</strong> Repository names, branch names, commit hashes, green scores, and SCI numerical indicators. (Source code contents are never stored).</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">3. Zero-Knowledge Token & Code Privacy</h4>
                <p>
                  GreenCode employs a Zero-Knowledge architecture for external repository credentials. GitHub Personal Access Tokens and cloud credentials are kept exclusively in volatile browser session memory and transmitted via TLS-encrypted HTTPS headers. Our database never stores customer GitHub PATs. Repository code extracted during automated audits is processed in ephemeral memory and discarded upon completion of the AST analysis.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">4. Legal Bases for Processing (GDPR Article 6)</h4>
                <p className="mb-2">We process personal data under the following lawful bases:</p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>Contractual Necessity (Art. 6(1)(b)):</strong> To provide, operate, and maintain your GreenCode account and deliver carbon calculation metrics.</li>
                  <li><strong>Legitimate Interests (Art. 6(1)(f)):</strong> To safeguard infrastructure against abuse, enforce rate limits, and ensure network security.</li>
                  <li><strong>Legal Obligation (Art. 6(1)(c)):</strong> To maintain audit ledgers and compliance records required under financial, corporate governance, and data protection statutes.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">5. Data Retention & Erasure Schedule</h4>
                <p>
                  Account credentials and organization records are retained for the duration of your active subscription. Access tokens expire after 15 minutes. Refresh tokens expire after 7 days and undergo cryptographic rotation on each use. If an account is deleted, all associated personal identifiers and audit records are hard-purged within 30 days.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">6. Your Rights under GDPR, CCPA & Global Regulations</h4>
                <p className="mb-2">Regardless of your geographic location, GreenCode grants you full data autonomy:</p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>Right to Access & Portability:</strong> Request an export of your account profile and associated telemetry in JSON format.</li>
                  <li><strong>Right to Rectification:</strong> Update or correct your profile details anytime in the Settings view.</li>
                  <li><strong>Right to Erasure ("Right to Be Forgotten"):</strong> Request immediate and irreversible deletion of your account and personal records.</li>
                  <li><strong>Right to Restrict or Object:</strong> Restrict processing or opt-out of non-essential communications.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">7. Security Controls & Encryption at Rest</h4>
                <p>
                  GreenCode implements defense-in-depth security including TLS 1.3 encryption in transit, Fernet AES-128/256 encryption at rest for sensitive configuration tables, role-based access control (RBAC), and strict network segmentation.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-2">8. Contact Information & Data Protection Officer</h4>
                <p>
                  For privacy inquiries, Data Subject Access Requests (DSAR), or compliance audits, contact our Data Protection Office at: <a href="mailto:privacy@greencode.io" className="text-emerald-800 underline font-medium">privacy@greencode.io</a>.
                </p>
              </div>

              <div className="pt-4 border-t border-slate-100 text-xs text-slate-400">
                Last updated: October 2026 · GreenCode Technologies Inc. Data Protection Office
              </div>

            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
            <ShieldCheck size={14} className="text-emerald-700" />
            <span>Strict Zero-Retention Code Guarantee</span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="py-1.5 px-4 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs font-semibold transition shadow-xs cursor-pointer"
          >
            I Understand & Accept
          </button>
        </div>

      </div>

    </div>
  );
}

