import {
  ShieldCheck, Terminal,
  X, Layers
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Modal } from '../primitives/Modal';
import { translateStatic as t } from '../../i18n/I18nContext';

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
      ? t('modals.aws.statusChecking')
      : t('modals.aws.statusFormat', {
          status: health.status || 'UNKNOWN',
          accounts: String(connectedAccounts ?? 0),
          plural: connectedAccounts === 1 ? '' : 's',
        });

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
                 {t('modals.aws.title')}
                 <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-700/60 text-zinc-200 border border-zinc-600 font-mono">
                   {headerStatus}
                 </span>
               </h3>
               <p className="text-[11px] text-slate-400">
                 {t('modals.aws.subtitle')}
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
              {t('modals.aws.summary')}
            </div>
            <p className="text-xs text-slate-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: t('modals.aws.summaryDesc') }} />
          </div>

          {/* Product Grid */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              {t('modals.aws.tecStackTitle')}
            </h4>
            <div className="space-y-2.5">
              {AMAZON_TECH_STACK.map((item, idx) => (
                <div 
                  key={idx}
                  className="p-3.5 rounded-lg border border-slate-200 bg-white dark:bg-zinc-800 hover:border-amber-400 hover:shadow-xs transition-all space-y-1.5"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-amber-100 text-[#FF9900] flex items-center justify-center font-bold text-xs shrink-0">
                        {idx + 1}
                      </span>
                      <span className="font-bold text-xs text-slate-900 dark:text-zinc-100">{item.name}</span>
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-zinc-700 text-slate-600 dark:text-zinc-300 border border-slate-200 dark:border-zinc-600 font-semibold self-start sm:self-auto">
                      {item.category}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600 dark:text-zinc-300 pl-7">
                    {item.role}
                  </p>

                  <div className="pl-7 pt-1 flex items-center gap-2 text-[10px] font-mono text-slate-400 dark:text-zinc-400">
                    <Terminal size={11} className="text-slate-500 dark:text-zinc-500" />
                    <span>{t('modals.aws.codeLocation', { location: item.codeLocation })}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Architecture Pipeline Flow */}
          <div className="p-4 rounded-xl border border-slate-200 bg-slate-900 text-white space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center gap-2">
              <Layers size={14} />
              {t('modals.aws.flowTitle')}
            </h4>
            <div className="text-xs font-mono text-slate-300 space-y-2 leading-relaxed">
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">{t('modals.aws.flowStep1')}</span>
                <span>Developer asks Alexa (&quot;Alexa, ask GreenCode to audit our repository&quot;)</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">{t('modals.aws.flowStep2')}</span>
                <span>Alexa invokes /mcp tool <code className="text-blue-300">audit_and_score</code> {t('modals.aws.flowStep2Desc')}</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">{t('modals.aws.flowStep3')}</span>
                <span>{t('modals.aws.flowStep3Desc')}</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">{t('modals.aws.flowStep4')}</span>
                <span>{t('modals.aws.flowStep4Desc')}</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold shrink-0">{t('modals.aws.flowStep5')}</span>
                <span>{t('modals.aws.flowStep5Desc')}</span>
              </div>
            </div>
          </div>
        </div>
      </Modal>
    );
}

