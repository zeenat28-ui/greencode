import React, { useState } from 'react';
import { X, ShieldCheck, FileText, Download, CheckCircle2, Scale, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

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
            <div className="w-8 h-8 rounded-lg bg-emerald-100/70 border border-emerald-200 flex items-center justify-center text-emerald-800 shrink-0">
              <Scale size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                GreenCode Legal & Compliance Portal
              </h3>
              <p className="text-xs text-slate-500">
                Global Enterprise Standards: ISO 14064 · GSF SCI v1.0 · SOC 2 · GDPR / CCPA
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
            <span>Master Services Agreement (Terms)</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
              v3.0
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
            <span>Global Privacy Policy</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-mono">
              Zero-Retention
            </span>
          </button>
        </div>

        {/* Modal Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-6 text-xs sm:text-sm text-slate-600 leading-relaxed font-sans">
          
          {activeTab === 'terms' ? (
            <div className="space-y-6 animate-in fade-in duration-150">
              
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-950 flex items-start gap-3">
                <CheckCircle2 size={16} className="text-emerald-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold text-emerald-900">Enterprise Zero-Code Retention Covenant: </strong>
                  GreenCode processes your source code and Abstract Syntax Tree (AST) representations exclusively in volatile, ephemeral container memory (RAM). Customer source code is never written to persistent disk storage, never retained in databases, and never used to train or fine-tune public or commercial machine learning foundation models.
                </div>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">Preamble & Binding Legal Authority</h4>
                <p>
                  This Master Services Agreement ("Agreement") is entered into by and between GreenCode Technologies Inc. ("GreenCode", "Provider", "we", "us", or "our") and the corporate legal entity or individual accessing or using the Services ("Customer", "User", "you", or "your"). By authenticating, executing an Order Form, or accessing the Services, you agree to be bound by this Agreement.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">1. Defined Terms</h4>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>"Authorized User"</strong> means Customer's employees, contractors, and agents authorized to access the Services under Customer's credentials.</li>
                  <li><strong>"Customer Data"</strong> means electronic metadata, repository references, configurations, and logs submitted to the Services, excluding Source Materials.</li>
                  <li><strong>"Source Materials"</strong> means source code, abstract syntax trees (ASTs), commit differentials, and scripts temporarily evaluated for computational energy profiling.</li>
                  <li><strong>"Derived Telemetry"</strong> means aggregated, non-reconstructible computational benchmarks, energy consumption ratings (in Joules/Watt-hours), and Software Carbon Intensity (SCI) scores.</li>
                  <li><strong>"Service Level Objective (SLO)"</strong> means Provider's commitment of 99.9% monthly platform availability across core API ingestion endpoints.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">2. License Grant & Provision of Services</h4>
                <p>
                  GreenCode grants Customer a non-exclusive, non-transferable, non-sublicensable, worldwide right and license during the active Subscription Term to access and utilize the Services solely for Customer's internal engineering, code quality benchmarking, cloud infrastructure optimization, and carbon emissions auditing.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">3. Intellectual Property Rights & Zero-Code Retention Covenant</h4>
                <p className="mb-2">
                  Customer retains all right, title, and interest in and to Customer's Source Materials, repositories, and Customer Data. Provider expressly covenants and warrants that:
                </p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li>All AST parsing, static analysis, and dynamic RAPL energy quantification are executed strictly in volatile ephemeral container memory (RAM).</li>
                  <li>Upon completion of the analytical session, all memory buffers containing Source Materials are immediately destroyed and unmapped.</li>
                  <li>Source Materials are <strong>never</strong> written to non-volatile disk storage, object stores, or persistent databases.</li>
                  <li>Source Materials will <strong>never</strong> be used to train or fine-tune public or commercial AI models or LLMs.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">4. Acceptable Use Policy & Restrictions</h4>
                <p className="mb-1">Customer shall not, and shall ensure Authorized Users do not:</p>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li>Sublicense, resell, or distribute the Services to unauthorized third parties;</li>
                  <li>Reverse engineer, decompile, or disassemble proprietary platform bytecode or binaries;</li>
                  <li>Circumvent security controls, sandboxing isolation boundaries, or rate limits;</li>
                  <li>Submit malicious code, worms, trojan horses, or cryptocurrency mining scripts;</li>
                  <li>Utilize GreenCode calculation models to produce knowingly fraudulent or misleading ESG disclosures.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">5. Credential Handling & Encryption</h4>
                <p>
                  GitHub credentials may be retained for authenticated repository operations and are encrypted at rest when the deployment has a valid SECRETS_ENCRYPTION_KEY. Per-request GitHub headers are not separately persisted. If you explicitly pair an Alexa account, GreenCode stores a separate encrypted copy so Alexa can audit the selected repository; it is retained until you say “unlink my GreenCode account.” Alexa pairing is blocked unless encryption is configured. Other cloud-provider credentials remain in the browser session and are sent over TLS only when needed.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">6. Scientific Standards & Carbon Accounting Disclaimers</h4>
                <p>
                  GreenCode calculates energy and carbon metrics adhering to the Green Software Foundation Software Carbon Intensity (GSF SCI v1.0) Specification, ISO/IEC standards track, and the GHG Protocol Corporate Standard. Calculations represent mathematical modeling based on hardware counters and regional grid factors, provided for operational optimization and not statutory financial audit certifications.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">7. Mutual Indemnification & Limitation of Liability</h4>
                <p>
                  To the maximum extent permitted by applicable law, neither party shall be liable for indirect, incidental, or consequential damages (including lost profits or business downtime). Each party's aggregate liability under this agreement shall not exceed the total fees paid by Customer to GreenCode in the twelve (12) months preceding the claim.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">8. Governing Law & Jurisdiction</h4>
                <p>
                  This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, United States, without regard to conflict of law principles. The parties consent to exclusive jurisdiction and venue in the courts located in New Castle County, Delaware.
                </p>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>Version 3.0 · Last updated: October 2026 · GreenCode Technologies Inc.</span>
                <Link to="/terms" target="_blank" className="text-emerald-800 hover:underline inline-flex items-center gap-1 font-semibold">
                  <span>Open standalone page</span>
                  <ExternalLink size={12} />
                </Link>
              </div>

            </div>
          ) : (
            <div className="space-y-6 animate-in fade-in duration-150">
              
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs text-emerald-950 flex items-start gap-3">
                <ShieldCheck size={16} className="text-emerald-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="font-semibold text-emerald-900">GDPR & CCPA/CPRA Compliance Guarantee: </strong>
                  We adhere to strict data minimization principles. We do not sell your personal information, monetize usage data, or share developer telemetry with data brokers or advertising exchanges.
                </div>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">1. Data Controller & Data Protection Officer</h4>
                <p>
                  GreenCode Technologies Inc. acts as a Data Controller for user accounts and corporate subscriptions, and as a Data Processor regarding enterprise organization team configurations. Inquiries or Data Subject Access Requests (DSAR) may be directed to our Data Protection Office at: <a href="mailto:dpo@greencode.io" className="text-emerald-800 underline font-medium">dpo@greencode.io</a>.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">2. Categories of Personal Data Collected</h4>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>Account Identity:</strong> Business email, full name, organization name, encrypted password hash (bcrypt with 12 salted rounds), and multi-factor authentication metadata.</li>
                  <li><strong>OAuth Identity:</strong> Public user ID, username, and public avatar URL from GitHub or Google Cloud Identity.</li>
                  <li><strong>Operational Telemetry:</strong> IP addresses, browser user-agents, cryptographic session tokens, and access logs recorded for SOC 2 Type II audit compliance.</li>
                  <li><strong>Derived Metrics:</strong> Repository names, branch names, commit hashes, green scores, and SCI numerical indicators. (Customer source code is never stored).</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">3. Lawful Bases for Processing (GDPR Art. 6)</h4>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>Contractual Necessity (Art. 6(1)(b)):</strong> To operate, provision, and maintain your account and deliver computational energy analytics.</li>
                  <li><strong>Legitimate Interests (Art. 6(1)(f)):</strong> To safeguard infrastructure against abuse, DDoS attacks, and enforce rate limits.</li>
                  <li><strong>Legal Obligation (Art. 6(1)(c)):</strong> To maintain audit ledgers and compliance records required by law.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">4. Zero-Code Retention & Memory-Only Processing</h4>
                <p>
                  Repository code extracted during energy audits is processed exclusively in volatile container RAM and permanently purged upon completion of the AST evaluation. Customer source code is never written to non-volatile disk storage, object stores, or relational databases, and is never used to train machine learning models.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">5. Technical & Organizational Measures (TOMs)</h4>
                <ul className="list-disc pl-5 space-y-1 text-slate-600">
                  <li><strong>In-Transit:</strong> TLS 1.3 encryption with Perfect Forward Secrecy and HSTS enforcement.</li>
                  <li><strong>At-Rest:</strong> AES-256 standard encryption for relational tables and sensitive configuration secrets.</li>
                  <li><strong>Access Controls:</strong> Role-Based Access Controls (RBAC), multi-factor hardware keys, and continuous SOC 2 vulnerability assessments.</li>
                </ul>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">6. Data Retention & Erasure Schedule</h4>
                <p>
                  Session tokens expire after 15 minutes. Refresh tokens expire after 7 days with mandatory rotation. Audit logs are retained for 90 days for SOC 2 security review. Upon account termination, all associated personal identifiers are hard-purged within thirty (30) days.
                </p>
              </div>

              <div>
                <h4 className="text-sm sm:text-base font-bold text-slate-900 mb-1.5">7. Your Rights under GDPR & California CCPA/CPRA</h4>
                <p>
                  You hold full rights of Access, Rectification, Erasure ("Right to Be Forgotten"), Restriction, Objection, and Data Portability. California residents may exercise CCPA rights without discrimination. GreenCode does not sell, rent, or share personal data. Submit DSAR inquiries to <a href="mailto:privacy@greencode.io" className="text-emerald-800 underline font-medium">privacy@greencode.io</a>.
                </p>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>Version 3.0 · Last updated: October 2026 · GreenCode Technologies Inc.</span>
                <Link to="/privacy" target="_blank" className="text-emerald-800 hover:underline inline-flex items-center gap-1 font-semibold">
                  <span>Open standalone page</span>
                  <ExternalLink size={12} />
                </Link>
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
