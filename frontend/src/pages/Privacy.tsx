import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, CheckCircle2, Download, Lock } from 'lucide-react';

export default function Privacy() {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#090b0a] text-slate-300 font-sans py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-2xl p-6 sm:p-10 text-slate-800">
        
        {/* Navigation & Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-6 mb-8">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 text-xs sm:text-sm font-semibold text-emerald-800 hover:text-emerald-950 transition"
          >
            <ArrowLeft size={16} />
            <span>Back to Sign In</span>
          </Link>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePrint}
              type="button"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 transition cursor-pointer"
            >
              <Download size={14} />
              <span>Export PDF</span>
            </button>
            <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
              <span>GDPR · CCPA · SOC 2</span>
              <span>·</span>
              <span>Version 3.0</span>
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="flex items-center gap-3.5 mb-6">
          <div className="w-10 h-10 rounded-xl bg-emerald-100/80 border border-emerald-300 flex items-center justify-center text-emerald-900 shrink-0">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Global Privacy Policy & Data Processing Notice
            </h1>
            <p className="text-xs sm:text-sm text-slate-500">
              Zero-Retention Data Architecture & Worldwide Regulatory Disclosures
            </p>
          </div>
        </div>

        {/* Compliance Guarantee Banner */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs sm:text-sm text-emerald-950 flex items-start gap-3 mb-8">
          <ShieldCheck size={18} className="text-emerald-700 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-emerald-900">GDPR & CCPA/CPRA Compliance Undertaking: </strong>
            GreenCode enforces rigorous data minimization principles. We do not sell, rent, or monetize your personal information or telemetry data. We do not share developer identities with advertising brokers or data exchanges.
          </div>
        </div>

        {/* Content sections */}
        <div className="space-y-7 text-xs sm:text-sm text-slate-600 leading-relaxed">

          {/* Section 1 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">1. Data Controller & Data Protection Officer (DPO)</h2>
            <p className="mb-2">
              This Privacy Policy describes how <strong>GreenCode Technologies Inc.</strong> ("GreenCode", "we", "us", or "our") processes, protects, and handles personal data collected through our software platform, APIs, developer dashboards, and command-line interfaces.
            </p>
            <p className="mb-2">
              GreenCode acts as a <strong>Data Controller</strong> under EU and UK data protection law regarding account registration data, billing records, and direct customer relationships. GreenCode acts as a <strong>Data Processor</strong> with respect to team configurations, workspace memberships, and enterprise organizational data managed by corporate customers.
            </p>
            <p>
              Our appointed Data Protection Officer can be reached directly for inquiries, audits, or regulatory notices at: <a href="mailto:dpo@greencode.io" className="text-emerald-800 underline font-medium">dpo@greencode.io</a>.
            </p>
          </div>

          {/* Section 2 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">2. Categories of Personal Data Collected</h2>
            <p className="mb-2">GreenCode collects only information strictly necessary to provide and secure the Services:</p>
            <ul className="list-disc pl-5 space-y-1.5 mb-2">
              <li><strong>Account Identifiers:</strong> Full legal name, business email address, organization name, enterprise domain, encrypted password hash (bcrypt algorithm with 12 salted rounds), and multi-factor authentication metadata.</li>
              <li><strong>Federated SSO & Identity Provider Data:</strong> Public user ID, username, and public avatar URL transmitted via GitHub OAuth, Google Cloud Identity, or SAML 2.0 / OIDC enterprise connectors.</li>
              <li><strong>Security & Operational Telemetry:</strong> Internet Protocol (IP) addresses, cryptographic session cookies, HTTP user-agent strings, TLS handshake ciphers, and timestamped API access logs collected to maintain SOC 2 Type II audit ledgers and automated DDoS defense.</li>
              <li><strong>Derived Performance Metrics:</strong> Repository names, branch names, commit SHA hashes, green energy scores, and Software Carbon Intensity numerical indicators.</li>
            </ul>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-slate-700">
              <strong>EXPLICIT LEGAL EXCLUSION: CUSTOMER SOURCE CODE IS NOT PERSONAL DATA.</strong> Source code, abstract syntax trees (ASTs), and proprietary build artifacts submitted during energy profiling do not constitute personal data. Source Materials are governed exclusively by our Zero-Retention Architecture (Section 5).
            </div>
          </div>

          {/* Section 3 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">3. Lawful Bases for Processing (GDPR Article 6 & UK GDPR)</h2>
            <p className="mb-2">We process personal data exclusively under legitimate statutory bases established by European and global data protection frameworks:</p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li><strong>Performance of Contract (Art. 6(1)(b)):</strong> To authenticate authorized users, provision workspace instances, deliver computational energy audits, and manage corporate subscriptions.</li>
              <li><strong>Legitimate Interests (Art. 6(1)(f)):</strong> To safeguard infrastructure integrity, mitigate brute-force credential stuffing, enforce rate limits, and prevent fraud.</li>
              <li><strong>Compliance with Legal Obligations (Art. 6(1)(c)):</strong> To comply with statutory financial record-keeping, corporate tax filings, and mandatory export compliance laws.</li>
              <li><strong>Explicit Consent (Art. 6(1)(a)):</strong> Where an individual voluntarily opts in to optional product updates, whitepapers, or beta program announcements.</li>
            </ul>
          </div>

          {/* Section 4 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">4. Credential Handling & Encryption</h2>
            <p>
              GitHub credentials may be retained for authenticated repository operations and are encrypted at rest when the deployment has a valid SECRETS_ENCRYPTION_KEY. Per-request GitHub headers are not separately persisted. If you explicitly pair an Alexa account, GreenCode stores a separate encrypted copy so Alexa can audit the selected repository; it is retained until you say “unlink my GreenCode account.” Alexa pairing is blocked unless encryption is configured. Other cloud-provider credentials remain in the browser session and are sent over TLS only when needed.
            </p>
          </div>

          {/* Section 5 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">5. Zero-Code Retention & Ephemeral Execution Guarantee</h2>
            <p className="mb-2">GreenCode is engineered with strict cryptographic and physical isolation boundaries:</p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li><strong>Volatile Memory Sandboxing:</strong> Source code repositories cloned or streamed for AST parsing and dynamic energy profiling reside exclusively in volatile container RAM.</li>
              <li><strong>Automatic Buffer Erasure:</strong> Upon completion of the analytical session, the ephemeral container runtime is destroyed, and the corresponding memory allocation is unmapped and overwritten.</li>
              <li><strong>Zero Non-Volatile Persistence:</strong> Source code is never written to persistent hard disks, cloud object stores (e.g., S3), or relational databases.</li>
              <li><strong>Zero AI Model Training:</strong> GreenCode formally warrants that customer code repositories are never used to train, evaluate, or tune any public, proprietary, or commercial machine learning foundation models.</li>
            </ul>
          </div>

          {/* Section 6 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">6. Technical & Organizational Security Measures (TOMs)</h2>
            <p className="mb-2">Pursuant to Article 32 of the GDPR, GreenCode maintains enterprise-grade security controls:</p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li><strong>In-Transit Encryption:</strong> All platform traffic is encrypted via Transport Layer Security (TLS 1.3 / TLS 1.2 minimum) with Perfect Forward Secrecy (PFS) and HTTP Strict Transport Security (HSTS).</li>
              <li><strong>At-Rest Encryption:</strong> Relational database records, cloud configurations, and persistent secrets are encrypted using AES-256 standard encryption (Fernet multi-key derivation).</li>
              <li><strong>Least Privilege & Multi-Factor Access:</strong> Role-Based Access Controls (RBAC), mandatory hardware MFA for engineering staff, and zero standing database administrative permissions.</li>
              <li><strong>Independent Auditing:</strong> Regular penetration testing and continuous vulnerability assessments aligned with SOC 2 Type II criteria.</li>
            </ul>
          </div>

          {/* Section 7 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">7. Authorized Sub-processors & International Transfers</h2>
            <p className="mb-2">
              <strong>7.1 Sub-processors.</strong> GreenCode engages trusted enterprise sub-processors to deliver core infrastructure services (e.g., Amazon Web Services for cloud computing, Supabase / PostgreSQL Enterprise for persistent metadata, and Cloudflare for edge routing and DDoS mitigation). Each sub-processor is bound by contractual Data Processing Addenda (DPAs) imposing security obligations no less restrictive than those in this Policy.
            </p>
            <p>
              <strong>7.2 International Data Transfers.</strong> Data may be transferred to and processed in the United States and the European Economic Area. Transfers of personal data from the EU, UK, or Switzerland to jurisdictions without an adequacy decision are governed by the European Commission's approved Standard Contractual Clauses (SCCs) (Commission Implementing Decision (EU) 2021/914) and the UK International Data Transfer Addendum.
            </p>
          </div>

          {/* Section 8 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">8. Data Retention & Cryptographic Disposal Schedule</h2>
            <ul className="list-disc pl-5 space-y-1.5">
              <li><strong>Session Tokens:</strong> Expire after 15 minutes of inactivity.</li>
              <li><strong>Refresh Tokens:</strong> Expire after 7 days and undergo mandatory cryptographic rotation upon each refresh event.</li>
              <li><strong>Operational Audit Logs:</strong> Maintained for 90 days for SOC 2 security log analysis, after which they are permanently expunged.</li>
              <li><strong>Account Deletion:</strong> Upon account termination via Settings or written request, all associated personal identifiers and team associations are permanently purged within thirty (30) calendar days.</li>
            </ul>
          </div>

          {/* Section 9 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">9. Your Global Data Subject Rights (GDPR & CCPA/CPRA)</h2>
            <p className="mb-2">Regardless of your geographic location, you enjoy full data autonomy and rights:</p>
            <ul className="list-disc pl-5 space-y-1.5 mb-2">
              <li><strong>Right to Access & Portability (GDPR Art. 15 & 20):</strong> Obtain a copy of your personal data in a structured, commonly used JSON format.</li>
              <li><strong>Right to Rectification (GDPR Art. 16):</strong> Update or correct your profile details anytime within Settings.</li>
              <li><strong>Right to Erasure ("Right to Be Forgotten") (GDPR Art. 17):</strong> Request irreversible deletion of all personal identifiers.</li>
              <li><strong>Right to Restrict or Object to Processing (GDPR Art. 18 & 21):</strong> Restrict processing or object to processing based on legitimate interests.</li>
              <li><strong>California CCPA/CPRA Rights:</strong> California residents have the right to know what personal information is collected, request deletion, and opt out of the sale or sharing of personal information. GreenCode <strong>does not sell, rent, or share personal information</strong> with third parties for cross-context behavioral advertising.</li>
            </ul>
            <p>
              To exercise any statutory right, submit a Data Subject Access Request (DSAR) to <a href="mailto:privacy@greencode.io" className="text-emerald-800 underline font-medium">privacy@greencode.io</a>. We respond within thirty (30) days without charge.
            </p>
          </div>

          {/* Section 10 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">10. Security Incident Response & Regulatory Recourse</h2>
            <p className="mb-2">
              <strong>Incident Notification:</strong> In the event of a confirmed personal data breach, GreenCode will notify affected customers and competent supervisory authorities without undue delay and, where feasible, within 72 hours of becoming aware of the breach, pursuant to GDPR Articles 33 and 34.
            </p>
            <p>
              <strong>Supervisory Recourse:</strong> EU and UK residents maintain the right to lodge a complaint with their local supervisory authority (e.g., the Data Protection Commission in Ireland, the CNIL in France, or the Information Commissioner's Office (ICO) in the UK).
            </p>
          </div>

          {/* Footer */}
          <div className="pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
            <span>© 2026 GreenCode Technologies Inc. All corporate rights reserved.</span>
            <Link to="/terms" className="text-emerald-800 hover:underline font-semibold">
              View Terms of Service &rarr;
            </Link>
          </div>

        </div>

      </div>
    </div>
  );
}
