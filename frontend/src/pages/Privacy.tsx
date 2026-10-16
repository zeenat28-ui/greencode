import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function Privacy() {
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
            <span>GDPR · CCPA · SOC 2</span>
            <span>·</span>
            <span>Effective Oct 2026</span>
          </div>
        </div>

        <div className="flex items-center gap-3.5 mb-6">
          <div className="w-10 h-10 rounded-xl bg-emerald-100/80 border border-emerald-300 flex items-center justify-center text-emerald-900">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Privacy Policy
            </h1>
            <p className="text-xs sm:text-sm text-slate-500">
              Zero-Retention Data Architecture & Global Privacy Disclosures
            </p>
          </div>
        </div>

        <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 text-xs sm:text-sm text-emerald-950 flex items-start gap-3 mb-8">
          <ShieldCheck size={18} className="text-emerald-700 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-emerald-900">GDPR & CCPA/CPRA Compliance Guarantee: </strong>
            We adhere to strict data minimization principles. We do not sell your personal information, monetize usage data, or share developer telemetry with data brokers.
          </div>
        </div>

        {/* Content sections */}
        <div className="space-y-6 text-xs sm:text-sm text-slate-600 leading-relaxed">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">1. Data Controller & Scope</h2>
            <p>
              This Privacy Policy outlines how GreenCode Technologies Inc. ("GreenCode") collects, processes, and protects personal information through our platform, developer portal, and APIs. GreenCode acts as the Data Controller for account management data, and as a Data Processor regarding enterprise customer team configurations.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">2. Information We Collect</h2>
            <p className="mb-2">We collect only information essential to providing the service:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
              <li><strong>Account Identity:</strong> Email address, username, full name, encrypted password hash (bcrypt with salted rounds), and organization affiliation.</li>
              <li><strong>OAuth Identity:</strong> GitHub or Google public user ID, username, and public avatar URL when signing in via social or SSO identity providers.</li>
              <li><strong>Security & Operational Telemetry:</strong> IP addresses, browser user-agent, session timestamps, and cryptographic audit logs recorded for SOC 2 Type II compliance.</li>
              <li><strong>Audit Metadata:</strong> Repository names, branch names, commit hashes, green scores, and SCI numerical indicators. (Source code contents are never stored).</li>
            </ul>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">3. Zero-Knowledge Token & Code Privacy</h2>
            <p>
              GreenCode employs a Zero-Knowledge architecture for external repository credentials. GitHub Personal Access Tokens and cloud credentials are kept exclusively in volatile browser session memory and transmitted via TLS-encrypted HTTPS headers. Our database never stores customer GitHub PATs. Repository code extracted during automated audits is processed in ephemeral memory and discarded upon completion of the AST analysis.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">4. Legal Bases for Processing (GDPR Article 6)</h2>
            <p className="mb-2">We process personal data under the following lawful bases:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
              <li><strong>Contractual Necessity (Art. 6(1)(b)):</strong> To provide, operate, and maintain your GreenCode account and deliver carbon calculation metrics.</li>
              <li><strong>Legitimate Interests (Art. 6(1)(f)):</strong> To safeguard infrastructure against abuse, enforce rate limits, and ensure network security.</li>
              <li><strong>Legal Obligation (Art. 6(1)(c)):</strong> To maintain audit ledgers and compliance records required under financial, corporate governance, and data protection statutes.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">5. Data Retention & Erasure Schedule</h2>
            <p>
              Account credentials and organization records are retained for the duration of your active subscription. Access tokens expire after 15 minutes. Refresh tokens expire after 7 days and undergo cryptographic rotation on each use. If an account is deleted, all associated personal identifiers and audit records are hard-purged within 30 days.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">6. Your Rights under GDPR, CCPA & Global Regulations</h2>
            <p className="mb-2">Regardless of your geographic location, GreenCode grants you full data autonomy:</p>
            <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
              <li><strong>Right to Access & Portability:</strong> Request an export of your account profile and associated telemetry in JSON format.</li>
              <li><strong>Right to Rectification:</strong> Update or correct your profile details anytime in the Settings view.</li>
              <li><strong>Right to Erasure ("Right to Be Forgotten"):</strong> Request immediate and irreversible deletion of your account and personal records.</li>
              <li><strong>Right to Restrict or Object:</strong> Restrict processing or opt-out of non-essential communications.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">7. Security Controls & Encryption at Rest</h2>
            <p>
              GreenCode implements defense-in-depth security including TLS 1.3 encryption in transit, Fernet AES-128/256 encryption at rest for sensitive configuration tables, role-based access control (RBAC), and strict network segmentation.
            </p>
          </div>

          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">8. Contact Information & Data Protection Officer</h2>
            <p>
              For privacy inquiries, Data Subject Access Requests (DSAR), or compliance audits, contact our Data Protection Office at: <a href="mailto:privacy@greencode.io" className="text-emerald-800 underline font-medium">privacy@greencode.io</a>.
            </p>
          </div>

          <div className="pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
            <span>© 2026 GreenCode Technologies Inc. All rights reserved.</span>
            <Link to="/terms" className="text-emerald-800 hover:underline">
              View Terms of Service
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}

