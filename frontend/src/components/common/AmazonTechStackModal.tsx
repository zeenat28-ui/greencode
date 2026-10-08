import { 
  Radio, Zap, Cloud, ShieldCheck, Terminal, 
  ExternalLink, CheckCircle2, X, Cpu, Server, Layers 
} from 'lucide-react';

interface AmazonTechStackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface TechItem {
  name: string;
  category: string;
  role: string;
  codeLocation: string;
  status: string;
}

const AMAZON_TECH_STACK: TechItem[] = [
  {
    name: 'Amazon Alexa+ Add-on & Voice MCP',
    category: 'Conversational Voice & MCP Protocol',
    role: 'Implements RFC 9728 & RFC 8414 Model Context Protocol over /mcp for hands-free code auditing and region selection.',
    codeLocation: 'alexa/addon.json · app/mcp_server.py · tests/test_alexa_compliance.py',
    status: 'RFC 9728 Verified & Deployed',
  },
  {
    name: 'Amazon Bedrock (Claude 3.5 Sonnet)',
    category: 'Generative AI & Code Synthesis',
    role: 'Orchestrates AST eco-refactoring with strict zero-regression guardrails and algorithmic complexity reduction.',
    codeLocation: 'app/bedrock_client.py · app/llm_refactor.py',
    status: 'Bedrock Converse API Active',
  },
  {
    name: 'AWS Datacenter Carbon & Grid Telemetry',
    category: 'Cloud Infrastructure & Carbon Arbitrage',
    role: 'Real-time telemetry tracking marginal carbon intensity and compute pricing across AWS global regions (eu-west-1, us-east-1, us-west-2).',
    codeLocation: 'app/carbon_intensity.py · frontend/src/pages/CloudCarbon.tsx',
    status: 'Live Electricity Maps & AWS API',
  },
  {
    name: 'AWS CodeArtifact & alexa-ai CLI Toolchain',
    category: 'Package Distribution & Deployment',
    role: 'Automates add-on packaging, icon generation, and endpoint verification for Alexa+ skills via AWS CodeArtifact.',
    codeLocation: 'alexa/README.md · scripts/gen_alexa_icons.py',
    status: 'Schema 1.0 Compliant',
  },
  {
    name: 'AWS EC2 FinOps Rightsizing Engine',
    category: 'Compute & Cloud Financial Optimization',
    role: 'Calculates infrastructure savings across AWS Graviton (m6g), Compute-Optimized (c6i), and GPU AI (g5) workloads.',
    codeLocation: 'frontend/src/components/common/FinOpsCalculatorModal.tsx',
    status: 'Enterprise ROI Active',
  },
];

export default function AmazonTechStackModal({
  isOpen,
  onClose,
}: AmazonTechStackModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-[#131921] text-white px-6 py-4 flex items-center justify-between border-b border-[#232F3E]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#FF9900] text-slate-950 font-black flex items-center justify-center text-sm shadow-sm">
              AWS
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                Amazon &amp; AWS Ecosystem Architecture
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 font-mono">
                  100% Amazon Qualified
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Full documentation of Amazon products, services, and APIs powering GreenCode
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
          {/* Executive Summary for Hackathon Judges */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-amber-50/70 via-orange-50/50 to-white border border-amber-200/90 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-amber-950 uppercase tracking-wider">
              <ShieldCheck size={16} className="text-[#FF9900]" />
              Official Hackathon Eligibility Statement
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              GreenCode is deeply built upon the <strong>Amazon ecosystem</strong>. It pairs <strong>Amazon Alexa+ (via the Model Context Protocol / MCP)</strong> with <strong>Amazon Bedrock (Claude 3.5 Sonnet)</strong> to deliver hands-free code auditing, automated AST refactoring, and AWS cloud carbon arbitrage.
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
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold self-start sm:self-auto">
                      {item.status}
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
      </div>
    </div>
  );
}

