import {
  ShieldCheck, Terminal,
  X, Layers
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Modal } from '../primitives/Modal';

interface AmazonTechStackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface TechItem {
  name: string;
  category: string;
  role: string;
  codeLocation: string;
}

/**
 * Where each Amazon capability is actually implemented. These are code
 * locations, not runtime claims - the modal never asserts that a service is
 * "Active" or "Verified", because that can only be true for the account that is
 * actually configured. The live connection state is read separately from
 * GET /api/aws/health and shown in the header.
 */
const AMAZON_TECH_STACK: TechItem[] = [
  {
    name: 'Amazon Alexa+ Add-on & Voice MCP',
    category: 'Conversational Voice & MCP Protocol',
    role: 'Implements RFC 9728 & RFC 8414 Model Context Protocol over /mcp for hands-free code auditing and region selection.',
    codeLocation: 'alexa/addon.json · app/mcp_server.py · tests/test_alexa_compliance.py',
  },
  {
    name: 'Amazon Bedrock (Claude Sonnet / Haiku)',
    category: 'Generative AI & Code Synthesis',
    role: 'Orchestrates AST eco-refactoring with strict zero-regression guardrails and algorithmic complexity reduction, via the Bedrock Runtime Converse API.',
    codeLocation: 'app/bedrock_client.py · app/llm_refactor.py',
  },
  {
    name: 'AWS Datacenter Carbon & Grid Telemetry',
    category: 'Cloud Infrastructure & Carbon Arbitrage',
    role: 'Resolves marginal carbon intensity per AWS region via Electricity Maps, falling back to the cited Ember 2024 reference table.',
    codeLocation: 'app/carbon_intensity.py · app/amazon_service.py',
  },
  {
    name: 'AWS STS AssumeRole & Budgets FinOps',
    category: 'Cross-Account Cost & Carbon Attribution',
    role: 'Links an AWS account via STS AssumeRole and reads month-to-date spend with AWS Budgets for physics-calibrated carbon attribution.',
    codeLocation: 'app/amazon_service.py · app/routers/amazon.py',
  },
  {
    name: 'AWS CodeArtifact & alexa-ai CLI Toolchain',
    category: 'Package Distribution & Deployment',
    role: 'Automates add-on packaging, icon generation, and endpoint verification for Alexa+ skills via AWS CodeArtifact.',
    codeLocation: 'alexa/README.md · scripts/gen_alexa_icons.py',
  },
];

interface AwsHealth {
  status?: string;
  connected_accounts?: number;
}

export default function AmazonTechStackModal({
  isOpen,
  onClose,
}: AmazonTechStackModalProps) {
  const [health, setHealth] = useState<AwsHealth | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    const token = localStorage.getItem('greencode_token');
    fetch('/api/aws/health', { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (active && data) setHealth(data);
      })
      .catch(() => {
        if (active) setHealth(null);
      });
    return () => {
      active = false;
    };
  }, [isOpen]);

  const connectedAccounts = health?.connected_accounts;
  const headerStatus =
    health === null
      ? 'Checking…'
      : `${health.status || 'UNKNOWN'} · ${connectedAccounts ?? 0} account${connectedAccounts === 1 ? '' : 's'} linked`;

   return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      showCloseButton={false}
      size="lg"
      overlayClassName="items-center bg-slate-900/60"
      className="!max-w-3xl border-slate-200 overflow-hidden"
      contentClassName="p-0 overflow-visible"
    >
        {/* Header */}
        <div className="bg-[#131921] text-white px-6 py-4 flex items-center justify-between border-b border-[#232F3E]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#FF9900] text-slate-950 font-black flex items-center justify-center text-sm shadow-sm">
              AWS
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                Amazon &amp; AWS Integration Architecture
                <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-700/60 text-zinc-200 border border-zinc-600 font-mono">
                  {headerStatus}
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Where each Amazon capability is implemented in GreenCode. Live status is read from the running backend.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X size={16} />
          </button>
        </div>


        <div className="p-6 space-y-6 text-slate-800 max-h-[82vh] overflow-y-auto">
          {/* Architecture Summary */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-amber-50/70 via-orange-50/50 to-white border border-amber-200/90 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-950 uppercase tracking-wider">
              <ShieldCheck size={16} className="text-[#FF9900]" />
              Amazon &amp; AWS Architecture Summary
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              GreenCode integrates <strong>Amazon Alexa+ (via the Model Context Protocol / MCP)</strong> with <strong>Amazon Bedrock (Claude 3.5 Sonnet)</strong> and <strong>AWS regional telemetry</strong> for voice-driven code auditing, verified AST refactoring, and cloud carbon comparison.
            </p>
          </div>

          {/* Product Grid */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              5 Core Amazon Technologies Integrated:
            </h4>
            <div className="space-y-2.5">
              {AMAZON_TECH_STACK.map((item, idx) => (
                <div 
                  key={idx}
                  className="p-3.5 rounded-lg border border-slate-200 bg-white hover:border-amber-400 hover:shadow-xs transition-all space-y-1.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-amber-100 text-[#FF9900] flex items-center justify-center font-bold text-xs shrink-0">
                        {idx + 1}
                      </span>
                      <span className="font-bold text-xs text-slate-900">{item.name}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 font-semibold self-start sm:self-auto">
                      {item.category}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 pl-7">
                    {item.role}
                  </p>

                  <div className="pl-7 pt-1 flex items-center gap-2 text-[10px] font-mono text-slate-400">
                    <Terminal size={11} className="text-slate-500" />
                    <span>Code location: <strong className="text-slate-700">{item.codeLocation}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Architecture Pipeline Flow */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-900 text-white space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
              <Layers size={14} />
              Amazon End-to-End Execution Flow
            </h4>
            <div className="text-xs font-mono text-slate-300 space-y-2 leading-relaxed">
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">1. Voice Command:</span>
                <span>Developer asks Alexa (&quot;Alexa, ask GreenCode to audit our repository&quot;)</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">2. Alexa+ MCP:</span>
                <span>Alexa invokes /mcp tool <code className="text-blue-300">audit_and_score</code> over RFC 9728 secure transport</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">3. Amazon Bedrock:</span>
                <span>Claude 3.5 Sonnet analyzes AST nodes and synthesizes verified O(N) patch</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">4. AWS Region Arbitrage:</span>
                <span>Telemetry shifts batch jobs to cleanest AWS datacenter (e.g., Ireland eu-west-1)</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">5. Spoken Confirmation:</span>
                <span>Alexa vocalizes the green score, kWh saved, and opens GitHub Pull Request</span>
              </div>
            </div>
          </div>
        </div>
      </Modal>
    );
}

