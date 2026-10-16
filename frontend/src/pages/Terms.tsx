import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Scale, ShieldCheck, CheckCircle2, FileText, Download } from 'lucide-react';

export default function Terms() {
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
              <span>Version 3.0</span>
              <span>·</span>
              <span>Effective Oct 2026</span>
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="flex items-center gap-3.5 mb-6">
          <div className="w-10 h-10 rounded-xl bg-emerald-100/80 border border-emerald-300 flex items-center justify-center text-emerald-900 shrink-0">
            <Scale size={22} />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
              Master Services Agreement & Terms of Service
            </h1>
            <p className="text-xs sm:text-sm text-slate-500">
              GreenCode Technologies Inc. Enterprise Software & API Terms
            </p>
          </div>
        </div>

        {/* Zero-Retention Guarantee Banner */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs sm:text-sm text-emerald-950 flex items-start gap-3 mb-8">
          <CheckCircle2 size={18} className="text-emerald-700 shrink-0 mt-0.5" />
          <div>
            <strong className="font-semibold text-emerald-900">Enterprise Zero-Code Retention Covenant: </strong>
            GreenCode processes your source code and Abstract Syntax Tree (AST) representations exclusively in volatile, ephemeral container memory (RAM). Customer source code is never written to persistent disk storage, never retained in databases, and never used to train or fine-tune public or commercial machine learning foundation models.
          </div>
        </div>

        {/* Formal Legal Sections */}
        <div className="space-y-7 text-xs sm:text-sm text-slate-600 leading-relaxed">

          {/* Preamble */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">Preamble & Binding Legal Authority</h2>
            <p>
              This Master Services Agreement ("Agreement") is entered into by and between <strong>GreenCode Technologies Inc.</strong> ("GreenCode", "Provider", "we", "us", or "our") and the corporate legal entity or individual accessing or using the Services ("Customer", "User", "you", or "your"). By creating an account, authenticating via OAuth or Single Sign-On (SSO), executing an Order Form, or accessing the GreenCode Software-as-a-Service platform, APIs, command-line interfaces, or CI/CD integrations (collectively, the "Services"), you agree to be bound by the terms and conditions set forth herein. If you are accepting on behalf of an employer, enterprise, or corporate entity, you represent and warrant that you possess full legal authority to bind that entity to this Agreement.
            </p>
          </div>

          {/* Section 1 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">1. Defined Terms</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>"Authorized User"</strong> means an employee, independent contractor, or designated agent of Customer who is granted access to the Services under Customer's corporate subscription.</li>
              <li><strong>"Customer Data"</strong> means electronic metadata, repository references, configuration parameters, team member directories, and operational audit logs submitted to the Services by Customer, excluding Source Materials.</li>
              <li><strong>"Source Materials"</strong> means source code, abstract syntax trees (ASTs), commit differentials, script files, and repository contents temporarily provided to the Services for computational energy quantification.</li>
              <li><strong>"Derived Telemetry"</strong> means aggregated, non-reconstructible computational benchmarks, energy consumption ratings (in Joules/Watt-hours), Software Carbon Intensity (SCI) scores, and static rule violation counts outputted by the platform.</li>
              <li><strong>"Order Form"</strong> means any digital self-service subscription tier or executed enterprise statement of work referencing this Agreement.</li>
              <li><strong>"Service Level Objective (SLO)"</strong> means GreenCode's operational commitment to maintain 99.9% monthly availability for core API ingestion endpoints, excluding scheduled maintenance.</li>
            </ul>
          </div>

          {/* Section 2 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">2. License Grant & Provision of Services</h2>
            <p className="mb-2">
              <strong>2.1 Limited Subscription License.</strong> Subject to compliance with this Agreement and timely payment of applicable fees, GreenCode grants Customer a non-exclusive, non-transferable, non-sublicensable, worldwide right and license during the active Subscription Term to access and utilize the Services solely for Customer's internal engineering, code quality benchmarking, cloud infrastructure optimization, and carbon emissions auditing.
            </p>
            <p>
              <strong>2.2 Platform Availability & Service Modifications.</strong> GreenCode continuously improves the platform. We reserve the right to deploy updates, security patches, algorithmic performance enhancements, and API revisions, provided that such modifications do not materially reduce the core functional capabilities of the Services during an active Subscription Term.
            </p>
          </div>

          {/* Section 3 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">3. Intellectual Property Rights & Zero-Code Retention Covenant</h2>
            <p className="mb-2">
              <strong>3.1 Customer Intellectual Property Ownership.</strong> As between Provider and Customer, Customer retains all right, title, and interest (including all patent, copyright, trademark, trade secret, and proprietary rights) in and to Customer's Source Materials, repositories, and Customer Data. No title or ownership in Customer Source Materials is transferred or licensed to GreenCode under this Agreement.
            </p>
            <p className="mb-2">
              <strong>3.2 Strict Zero-Code Retention Undertaking.</strong> Provider formally covenants, warrants, and agrees that:
            </p>
            <ul className="list-disc pl-5 space-y-1.5 mb-2">
              <li>All computational evaluation of Source Materials (including AST parsing, static rule evaluation, dynamic profiler execution, and RAPL energy quantification) is executed strictly in volatile ephemeral container memory (RAM).</li>
              <li>Upon completion of the analytical session and transmission of Derived Telemetry to Customer, all ephemeral memory buffers containing Source Materials are immediately destroyed and unmapped.</li>
              <li>Customer Source Materials are <strong>never</strong> written to non-volatile disk storage, object storage (e.g., S3), or relational databases.</li>
              <li>Customer Source Materials will <strong>never</strong> be disclosed to third parties, monetized, or utilized to train, fine-tune, or benchmark any commercial or public machine learning foundation models, large language models (LLMs), or neural networks.</li>
            </ul>
            <p>
              <strong>3.3 Provider Proprietary Rights.</strong> GreenCode and its licensors retain all right, title, and interest in and to the Services, proprietary AST energy heuristics, Software Carbon Intensity calculation engines, web dashboards, documentation, and all underlying algorithms, including any modifications and derivative works thereof.
            </p>
          </div>

          {/* Section 4 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">4. Acceptable Use Policy & Negative Covenants</h2>
            <p className="mb-2">Customer shall not, and shall ensure that Authorized Users do not:</p>
            <ul className="list-disc pl-5 space-y-1.5">
              <li>Sublicense, resell, lease, distribute, or provide time-sharing or service bureau access to the Services to any unauthorized third party;</li>
              <li>Reverse engineer, decompile, disassemble, or attempt to derive source code, algorithms, or proprietary trade secrets from the GreenCode platform or binaries (except to the minimal extent expressly permitted by mandatory applicable law);</li>
              <li>Circumvent, disable, or tamper with any authentication controls, sandboxing isolation boundaries, rate-limiting parameters, or security features of the Services;</li>
              <li>Submit malicious code, worms, trojan horses, cryptocurrency mining scripts, or unauthorized exploit payloads to the execution queues or sandboxes;</li>
              <li>Use the Services to conduct competitive performance benchmarking or comparative testing for public publication without GreenCode's express prior written consent;</li>
              <li>Utilize GreenCode calculation models to produce knowingly fraudulent or materially misleading environmental, social, and governance (ESG) or regulatory disclosures.</li>
            </ul>
          </div>

          {/* Section 5 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">5. User Authentication & Zero-Knowledge Token Custody</h2>
            <p className="mb-2">
              <strong>5.1 Account Security.</strong> Customer is solely responsible for maintaining the confidentiality of its Authorized User credentials, passwords, and multi-factor authentication tokens. Customer agrees to promptly notify GreenCode of any suspected unauthorized access or compromise.
            </p>
            <p>
              <strong>5.2 Zero-Knowledge Token Custody.</strong> When Customer provides third-party access credentials (such as GitHub Personal Access Tokens or cloud service provider API keys), such credentials are held solely within the client browser session memory under our Zero-Knowledge architecture and delivered via encrypted TLS headers per operational request. GreenCode's relational databases do not persist unencrypted third-party API secret keys.
            </p>
          </div>

          {/* Section 6 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">6. Scientific Standards & Carbon Accounting Disclaimers</h2>
            <p className="mb-2">
              <strong>6.1 Scientific Methodological Framework.</strong> GreenCode calculates computational energy and carbon metrics adhering to the Green Software Foundation Software Carbon Intensity (GSF SCI v1.0) Specification, ISO/IEC international standards track, and the Greenhouse Gas Protocol Corporate Standard (GHG Protocol Scope 2 and Scope 3 Guidance).
            </p>
            <p>
              <strong>6.2 Mathematical Modeling Notice.</strong> Energy and emissions estimations incorporate hardware thermal telemetry (Intel RAPL, AMD Energy, ARM Telemetry) combined with regional marginal grid emissions factors (e.g., eGRID, ENTSO-E, and real-time grid feeds). Customer acknowledges that emissions metrics represent rigorous mathematical modeling for operational software optimization and do not constitute certified statutory financial or tax audit certifications.
            </p>
          </div>

          {/* Section 7 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">7. Fees, Invoicing & Tax Obligations</h2>
            <p>
              Customer shall pay all fees specified in applicable Order Forms. Except as expressly provided herein, all payment obligations are non-cancelable and fees paid are non-refundable. Pricing excludes all applicable sales, use, excise, or value-added taxes (VAT), which Customer is responsible for remitting, excluding taxes based on Provider's net corporate income.
            </p>
          </div>

          {/* Section 8 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">8. Warranties & Disclaimers</h2>
            <p className="mb-2">
              <strong>8.1 Mutual Representations.</strong> Each party represents and warrants that it is duly organized, validly existing, and in good standing under the laws of its jurisdiction of formation, and has the requisite corporate authority to enter into this Agreement.
            </p>
            <p>
              <strong>8.2 Express Disclaimer.</strong> EXCEPT AS EXPRESSLY PROVIDED HEREIN, THE SERVICES, PLATFORM, AND DERIVED METRICS ARE PROVIDED ON AN "AS IS" AND "AS AVAILABLE" BASIS. GREENCODE AND ITS AFFILIATES AND LICENSORS EXPRESSLY DISCLAIM ALL OTHER WARRANTIES, WHETHER EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, INCLUDING WITHOUT LIMITATION WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT.
            </p>
          </div>

          {/* Section 9 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">9. Mutual Indemnification</h2>
            <p className="mb-2">
              <strong>9.1 Provider IP Indemnification.</strong> GreenCode shall defend Customer against any third-party claim, suit, or proceeding alleging that Customer's authorized use of the Services infringes or misappropriates any third party's valid patent or copyright, and shall indemnify Customer against damages finally awarded by a court of competent jurisdiction.
            </p>
            <p>
              <strong>9.2 Customer Indemnification.</strong> Customer shall defend and indemnify GreenCode against any third-party claim arising out of or related to Customer's Source Materials, Customer Data, or Customer's violation of the Acceptable Use Policy.
            </p>
          </div>

          {/* Section 10 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">10. Limitation of Liability</h2>
            <p className="mb-2">
              <strong>10.1 Consequential Damages Waiver.</strong> IN NO EVENT SHALL EITHER PARTY BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, PUNITIVE, OR EXEMPLARY DAMAGES, INCLUDING LOSS OF PROFITS, REVENUE, DATA, OR BUSINESS INTERRUPTION, REGARDLESS OF THE THEORY OF LIABILITY (WHETHER IN CONTRACT, TORT, STRICT LIABILITY, OR OTHERWISE).
            </p>
            <p>
              <strong>10.2 Aggregate Liability Cap.</strong> EXCEPT FOR LIABILITIES ARISING FROM A PARTY'S INDEMNIFICATION OBLIGATIONS UNDER SECTION 9 OR A BREACH OF SECTION 4 (RESTRICTIONS), EACH PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL BE LIMITED TO THE TOTAL AMOUNT PAID OR PAYABLE BY CUSTOMER TO GREENCODE IN THE TWELVE (12) MONTH PERIOD PRECEDING THE EVENT GIVING RISE TO LIABILITY.
            </p>
          </div>

          {/* Section 11 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">11. Term, Termination & Cryptographic Purge</h2>
            <p className="mb-2">
              <strong>11.1 Term.</strong> This Agreement commences on the date Customer first registers or accesses the Services and continues until all subscriptions expire or are terminated.
            </p>
            <p className="mb-2">
              <strong>11.2 Termination for Cause.</strong> Either party may terminate this Agreement upon thirty (30) days' written notice if the other party materially breaches this Agreement and fails to cure such breach within the thirty-day cure period.
            </p>
            <p>
              <strong>11.3 Cryptographic Purge upon Termination.</strong> Within thirty (30) days following the effective date of termination, GreenCode permanently deletes and purges Customer account records, telemetry history, and configurations from production databases in accordance with SOC 2 Type II retention protocols.
            </p>
          </div>

          {/* Section 12 */}
          <div>
            <h2 className="text-base sm:text-lg font-bold text-slate-900 mb-2">12. Governing Law, Jurisdiction & General Provisions</h2>
            <p className="mb-2">
              <strong>12.1 Governing Law & Jurisdiction.</strong> This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, United States, without regard to its conflict of law principles. The parties consent to exclusive personal jurisdiction and venue in the state and federal courts located in New Castle County, Delaware.
            </p>
            <p className="mb-2">
              <strong>12.2 Export Controls.</strong> The Services may be subject to U.S. and international export control laws. Customer represents that it is not located in any embargoed destination or identified on any government denied-party list.
            </p>
            <p>
              <strong>12.3 Entire Agreement & Severability.</strong> This Agreement constitutes the complete and exclusive statement of the agreement between the parties with respect to its subject matter and supersedes all prior agreements, proposals, and discussions. If any provision is held invalid, the remaining provisions shall remain in full force and effect.
            </p>
          </div>

          {/* Footer */}
          <div className="pt-6 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
            <span>© 2026 GreenCode Technologies Inc. All corporate rights reserved.</span>
            <Link to="/privacy" className="text-emerald-800 hover:underline font-semibold">
              View Privacy Policy &rarr;
            </Link>
          </div>

        </div>

      </div>
    </div>
  );
}
