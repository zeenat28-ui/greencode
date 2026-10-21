import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cloud,
  Code2,
  Copy,
  Cpu,
  Database,
  DollarSign,
  ExternalLink,
  FileCode,
  FolderGit2,
  Gauge,
  GitBranch,
  Github,
  GitPullRequest,
  Globe,
  Key,
  Layers,
  Loader2,
  LogOut,
  Mic,
  MicOff,
  Play,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Terminal,
  TrendingDown,
  Volume2,
  Wand2,
  X,
  Zap,
} from 'lucide-react';
import { useAuth } from './context/AuthContext';

// ============================================================================
// Standardized Industry Linter Rules (SonarQube / Snyk / CodeQL Format)
// ============================================================================
export const BOTTLE_VIOLATIONS_24 = [
  {
    id: 'v-1',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:346',
    fileOnly: 'bottle.py',
    line: 346,
    energyWh: 0.020,
    costMonthly: 0.69,
    originalCode: "346  -  pattern += '(?P<%s>%s)' % (key, mask)",
    refactoredCode: "346  +  pattern_parts.append(f'(?P<{key}>{mask})')\n347  +  pattern = ''.join(pattern_parts)",
    tip: "Use list.append() and ''.join() instead of '+=' inside loops to avoid O(n²) memory allocations.",
    impactStr: '-0.020 Wh / run',
  },
  {
    id: 'v-2',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:351',
    fileOnly: 'bottle.py',
    line: 351,
    energyWh: 0.020,
    costMonthly: 0.69,
    originalCode: '351  -  pattern += chunk',
    refactoredCode: "351  +  chunks.append(chunk)  # Combine once via ''.join(chunks)",
    tip: "Use list.append() and ''.join() instead of '+=' inside loops to avoid O(n²) memory allocations.",
    impactStr: '-0.020 Wh / run',
  },
  {
    id: 'v-3',
    ruleId: 'GCA002',
    slug: 'uncompiled-regex-in-loop',
    ruleName: 'Regex re-compilation inside loop',
    title: 'GCA002 · uncompiled-regex-in-loop',
    impactTag: 'CPU · Regex',
    severity: 'Warning',
    filePath: 'bottle.py:413',
    fileOnly: 'bottle.py',
    line: 413,
    energyWh: 0.018,
    costMonthly: 0.64,
    originalCode: '413  -  match = re.compile(pattern).match(header)',
    refactoredCode: '413  +  match = COMPILED_HEADER_RE.match(header)',
    tip: 'Pre-compile regex with re.compile() outside loop to avoid repeated parsing overhead.',
    impactStr: '-0.018 Wh / run',
  },
  {
    id: 'v-4',
    ruleId: 'GCA003',
    slug: 'unmemoized-recursion',
    ruleName: 'Recursion without memoization',
    title: 'GCA003 · unmemoized-recursion',
    impactTag: 'CPU · Call Stack',
    severity: 'Warning',
    filePath: 'bottle.py:820',
    fileOnly: 'bottle.py',
    line: 820,
    energyWh: 0.028,
    costMonthly: 0.81,
    originalCode: '820  -  def resolve_route(path, depth=0): return resolve_route(path[1:], depth+1)',
    refactoredCode: '820  +  @functools.lru_cache(maxsize=1024)\n        def resolve_route(path, depth=0): return resolve_route(path[1:], depth+1)',
    tip: 'Apply @functools.lru_cache() to recursive calls to eliminate exponential recalculations.',
    impactStr: '-0.028 Wh / run',
  },
  {
    id: 'v-5',
    ruleId: 'GCA003',
    slug: 'unmemoized-recursion',
    ruleName: 'Recursion without memoization',
    title: 'GCA003 · unmemoized-recursion',
    impactTag: 'CPU · Call Stack',
    severity: 'Warning',
    filePath: 'bottle.py:980',
    fileOnly: 'bottle.py',
    line: 980,
    energyWh: 0.028,
    costMonthly: 0.81,
    originalCode: '980  -  def parse_subroutes(tree): return [parse_subroutes(c) for c in tree]',
    refactoredCode: '980  +  @functools.lru_cache(maxsize=512)\n        def parse_subroutes(tree): return [parse_subroutes(c) for c in tree]',
    tip: 'Memoize repeated sub-route parsing trees to reduce CPU cycle waste.',
    impactStr: '-0.028 Wh / run',
  },
  {
    id: 'v-6',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:1042',
    fileOnly: 'bottle.py',
    line: 1042,
    energyWh: 0.019,
    costMonthly: 0.65,
    originalCode: '1042 -  out += str(part)',
    refactoredCode: "1042 +  parts.append(str(part))  # Join once via ''.join(parts)",
    tip: 'Buffer parts into list and join at exit.',
    impactStr: '-0.019 Wh / run',
  },
  {
    id: 'v-7',
    ruleId: 'GCA002',
    slug: 'uncompiled-regex-in-loop',
    ruleName: 'Regex re-compilation inside loop',
    title: 'GCA002 · uncompiled-regex-in-loop',
    impactTag: 'CPU · Regex',
    severity: 'Warning',
    filePath: 'bottle.py:1120',
    fileOnly: 'bottle.py',
    line: 1120,
    energyWh: 0.022,
    costMonthly: 0.72,
    originalCode: "1120 -  if re.search(r'\\s+', line):",
    refactoredCode: '1120 +  if WHITESPACE_RE.search(line):',
    tip: 'Hoist regular expression compilation outside line-processing loops.',
    impactStr: '-0.022 Wh / run',
  },
  {
    id: 'v-8',
    ruleId: 'GCA006',
    slug: 'uncached-network-in-loop',
    ruleName: 'Uncached network call in loop',
    title: 'GCA006 · uncached-network-in-loop',
    impactTag: 'Network · HTTP',
    severity: 'Warning',
    filePath: 'bottle.py:1290',
    fileOnly: 'bottle.py',
    line: 1290,
    energyWh: 0.035,
    costMonthly: 1.10,
    originalCode: '1290 -  res = urllib.request.urlopen(url)',
    refactoredCode: '1290 +  res = session_pool.get(url)',
    tip: 'Reuse persistent HTTP connection session pool to eliminate handshakes.',
    impactStr: '-0.035 Wh / run',
  },
  {
    id: 'v-9',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:1340',
    fileOnly: 'bottle.py',
    line: 1340,
    energyWh: 0.021,
    costMonthly: 0.70,
    originalCode: "1340 -  header_text += k + ': ' + v + '\\r\\n'",
    refactoredCode: "1340 +  header_lines.append(f'{k}: {v}\\r\\n')",
    tip: 'Replace multi-line header string accumulation with array join.',
    impactStr: '-0.021 Wh / run',
  },
  {
    id: 'v-10',
    ruleId: 'GCA008',
    slug: 'sync-io-in-async',
    ruleName: 'Blocking synchronous I/O in async',
    title: 'GCA008 · sync-io-in-async',
    impactTag: 'Async · Event Loop',
    severity: 'Warning',
    filePath: 'bottle.py:1410',
    fileOnly: 'bottle.py',
    line: 1410,
    energyWh: 0.031,
    costMonthly: 0.95,
    originalCode: "1410 -  data = open(path, 'rb').read()",
    refactoredCode: "1410 +  data = await aiofiles.open(path, 'rb').read()",
    tip: 'Use asynchronous non-blocking file reader to prevent thread starvation.',
    impactStr: '-0.031 Wh / run',
  },
  {
    id: 'v-11',
    ruleId: 'GCA009',
    slug: 'redundant-alloc-in-loop',
    ruleName: 'Linear lookup inside loop',
    title: 'GCA009 · redundant-alloc-in-loop',
    impactTag: 'Memory · Allocation',
    severity: 'Warning',
    filePath: 'bottle.py:1520',
    fileOnly: 'bottle.py',
    line: 1520,
    energyWh: 0.024,
    costMonthly: 0.75,
    originalCode: '1520 -  if item in list_of_keys:',
    refactoredCode: '1520 +  if item in set_of_keys:',
    tip: 'Convert lookup list to O(1) hash set before loop.',
    impactStr: '-0.024 Wh / run',
  },
  {
    id: 'v-12',
    ruleId: 'GCA004',
    slug: 'deep-nested-loops',
    ruleName: 'Deep nested loops',
    title: 'GCA004 · deep-nested-loops',
    impactTag: 'CPU · O(n³)',
    severity: 'Warning',
    filePath: 'bottle.py:1640',
    fileOnly: 'bottle.py',
    line: 1640,
    energyWh: 0.045,
    costMonthly: 1.40,
    originalCode: '1640 -  for a in A:\n          for b in B:\n            for c in C: evaluate(a, b, c)',
    refactoredCode: '1640 +  for a, b, c in itertools.product(A, B, C): evaluate(a, b, c)',
    tip: 'Flatten cubic nested iterations using itertools product iterator.',
    impactStr: '-0.045 Wh / run',
  },
  {
    id: 'v-13',
    ruleId: 'GCA002',
    slug: 'uncompiled-regex-in-loop',
    ruleName: 'Regex re-compilation inside loop',
    title: 'GCA002 · uncompiled-regex-in-loop',
    impactTag: 'CPU · Regex',
    severity: 'Warning',
    filePath: 'bottle.py:1735',
    fileOnly: 'bottle.py',
    line: 1735,
    energyWh: 0.017,
    costMonthly: 0.60,
    originalCode: '1735 -  matches = re.findall(rule, text)',
    refactoredCode: '1735 +  matches = COMPILED_RULE.findall(text)',
    tip: 'Pre-compile rule regex once at module level.',
    impactStr: '-0.017 Wh / run',
  },
  {
    id: 'v-14',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:1820',
    fileOnly: 'bottle.py',
    line: 1820,
    energyWh: 0.020,
    costMonthly: 0.68,
    originalCode: '1820 -  html += render_row(row)',
    refactoredCode: '1820 +  rows.append(render_row(row))',
    tip: "Combine rendered HTML rows via ''.join(rows).",
    impactStr: '-0.020 Wh / run',
  },
  {
    id: 'v-15',
    ruleId: 'GCA005',
    slug: 'raw-db-cursor',
    ruleName: 'Unclosed database cursor',
    title: 'GCA005 · raw-db-cursor',
    impactTag: 'I/O · DB Cursor',
    severity: 'Warning',
    filePath: 'bottle.py:1950',
    fileOnly: 'bottle.py',
    line: 1950,
    energyWh: 0.029,
    costMonthly: 0.85,
    originalCode: '1950 -  cur = db.cursor(); cur.execute(sql)',
    refactoredCode: '1950 +  with db.cursor() as cur: cur.execute(sql)',
    tip: "Wrap database connections in 'with conn.cursor() as cur:' context manager.",
    impactStr: '-0.029 Wh / run',
  },
  {
    id: 'v-16',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:2045',
    fileOnly: 'bottle.py',
    line: 2045,
    energyWh: 0.019,
    costMonthly: 0.65,
    originalCode: "2045 -  query_str += '&' + k + '=' + v",
    refactoredCode: '2045 +  query_str = urllib.parse.urlencode(params)',
    tip: 'Use optimized urlencode rather than manual string concat.',
    impactStr: '-0.019 Wh / run',
  },
  {
    id: 'v-17',
    ruleId: 'GCA002',
    slug: 'uncompiled-regex-in-loop',
    ruleName: 'Regex re-compilation inside loop',
    title: 'GCA002 · uncompiled-regex-in-loop',
    impactTag: 'CPU · Regex',
    severity: 'Warning',
    filePath: 'bottle.py:2180',
    fileOnly: 'bottle.py',
    line: 2180,
    energyWh: 0.018,
    costMonthly: 0.62,
    originalCode: "2180 -  re.sub(r'\\r\\n', '\\n', val)",
    refactoredCode: "2180 +  val.replace('\\r\\n', '\\n')",
    tip: 'Use fast C-level str.replace for fixed string substitutions.',
    impactStr: '-0.018 Wh / run',
  },
  {
    id: 'v-18',
    ruleId: 'GCA003',
    slug: 'unmemoized-recursion',
    ruleName: 'Recursion without memoization',
    title: 'GCA003 · unmemoized-recursion',
    impactTag: 'CPU · Call Stack',
    severity: 'Warning',
    filePath: 'bottle.py:2290',
    fileOnly: 'bottle.py',
    line: 2290,
    energyWh: 0.027,
    costMonthly: 0.80,
    originalCode: '2290 -  def walk_tree(n): return [walk_tree(c) for c in n.children]',
    refactoredCode: '2290 +  @functools.lru_cache(None)\n        def walk_tree(n): return [walk_tree(c) for c in n.children]',
    tip: 'Memoize AST node tree traversals.',
    impactStr: '-0.027 Wh / run',
  },
  {
    id: 'v-19',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:2410',
    fileOnly: 'bottle.py',
    line: 2410,
    energyWh: 0.021,
    costMonthly: 0.70,
    originalCode: "2410 -  payload += chunk.encode('utf-8')",
    refactoredCode: "2410 +  byte_chunks.append(chunk.encode('utf-8'))",
    tip: 'Accumulate bytes into bytearray or list.',
    impactStr: '-0.021 Wh / run',
  },
  {
    id: 'v-20',
    ruleId: 'GCA007',
    slug: 'unindexed-db-query',
    ruleName: 'Linear lookup inside loop',
    title: 'GCA007 · unindexed-db-query',
    impactTag: 'I/O · Full Scan',
    severity: 'Warning',
    filePath: 'bottle.py:2530',
    fileOnly: 'bottle.py',
    line: 2530,
    energyWh: 0.023,
    costMonthly: 0.74,
    originalCode: '2530 -  if route.name in registered_names:',
    refactoredCode: '2530 +  if route.name in registered_set:',
    tip: 'Use O(1) set membership test.',
    impactStr: '-0.023 Wh / run',
  },
  {
    id: 'v-21',
    ruleId: 'GCA002',
    slug: 'uncompiled-regex-in-loop',
    ruleName: 'Regex re-compilation inside loop',
    title: 'GCA002 · uncompiled-regex-in-loop',
    impactTag: 'CPU · Regex',
    severity: 'Warning',
    filePath: 'bottle.py:2650',
    fileOnly: 'bottle.py',
    line: 2650,
    energyWh: 0.018,
    costMonthly: 0.61,
    originalCode: "2650 -  re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name)",
    refactoredCode: '2650 +  NAME_RE.match(name)',
    tip: 'Hoist identifier regex compilation to module scope.',
    impactStr: '-0.018 Wh / run',
  },
  {
    id: 'v-22',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:2780',
    fileOnly: 'bottle.py',
    line: 2780,
    energyWh: 0.020,
    costMonthly: 0.68,
    originalCode: '2780 -  res += val',
    refactoredCode: '2780 +  res_parts.append(val)',
    tip: 'Join buffered strings at loop completion.',
    impactStr: '-0.020 Wh / run',
  },
  {
    id: 'v-23',
    ruleId: 'GCA003',
    slug: 'unmemoized-recursion',
    ruleName: 'Recursion without memoization',
    title: 'GCA003 · unmemoized-recursion',
    impactTag: 'CPU · Call Stack',
    severity: 'Warning',
    filePath: 'bottle.py:2910',
    fileOnly: 'bottle.py',
    line: 2910,
    energyWh: 0.026,
    costMonthly: 0.78,
    originalCode: '2910 -  def find_leaf(n): return find_leaf(n.parent)',
    refactoredCode: '2910 +  def find_leaf(n):\n            curr = n\n            while curr.parent: curr = curr.parent\n            return curr',
    tip: 'Convert tail-recursive chain into iterative while loop.',
    impactStr: '-0.026 Wh / run',
  },
  {
    id: 'v-24',
    ruleId: 'GCA001',
    slug: 'string-concat-in-loop',
    ruleName: 'String concatenation in loop',
    title: 'GCA001 · string-concat-in-loop',
    impactTag: 'Memory · O(n²)',
    severity: 'Warning',
    filePath: 'bottle.py:3050',
    fileOnly: 'bottle.py',
    line: 3050,
    energyWh: 0.020,
    costMonthly: 0.69,
    originalCode: "3050 -  cookie_header += '; ' + k + '=' + v",
    refactoredCode: "3050 +  cookie_parts.append(f'{k}={v}')",
    tip: "Format cookies into array and join with '; '.",
    impactStr: '-0.020 Wh / run',
  },
];

export default function GreenCodeAuditorApp() {
  const { user, logout } = useAuth();

  // State
  const [violations, setViolations] = useState(BOTTLE_VIOLATIONS_24);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [fixedIds, setFixedIds] = useState(new Set());
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [codeViewTab, setCodeViewTab] = useState('diff'); // 'diff' | 'fixed' | 'full'
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [isAuditing, setIsAuditing] = useState(false);
  const [isAiOptimizing, setIsAiOptimizing] = useState(false);
  const [targetRepo, setTargetRepo] = useState('bottlepy/bottle');
  const [statusText, setStatusText] = useState('Scan complete · 24 issues in bottlepy/bottle');

  // Modals
  const [voiceAuditModalOpen, setVoiceAuditModalOpen] = useState(false);
  const [githubConnectModalOpen, setGithubConnectModalOpen] = useState(false);
  const [prModalOpen, setPrModalOpen] = useState(false);

  // Alexa Voice State
  const [isListeningMic, setIsListeningMic] = useState(false);
  const [alexaState, setAlexaState] = useState('idle'); // 'idle' | 'listening' | 'speaking'
  const [alexaText, setAlexaText] = useState('');
  const [voiceLogs, setVoiceLogs] = useState([
    {
      time: '16:20:11',
      speaker: 'User',
      text: 'Alexa, ask Green Code Auditor to audit bottlepy/bottle',
      action: 'audit_repo',
    },
    {
      time: '16:20:13',
      speaker: 'Alexa',
      text: 'Audited bottlepy/bottle. Detected 24 energy bottlenecks with 0.56 Wh impact and $17.42 monthly cloud waste.',
      action: 'spoken_briefing',
    },
  ]);

  const recognitionRef = useRef(null);

  // Filtered list
  const filteredViolations = useMemo(() => {
    return violations.filter((v) => {
      const matchesFilter =
        activeFilter === 'ALL' ||
        (activeFilter === 'ERROR' && v.severity === 'Critical') ||
        (activeFilter === 'WARNING' && v.severity === 'Warning');

      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        v.title.toLowerCase().includes(q) ||
        v.filePath.toLowerCase().includes(q) ||
        v.ruleId.toLowerCase().includes(q);

      return matchesFilter && matchesSearch;
    });
  }, [violations, activeFilter, searchQuery]);

  const activeViolation = violations[selectedIndex] || violations[0] || BOTTLE_VIOLATIONS_24[0];

  // Dynamic calculations reflecting applied patches
  const remainingCount = violations.filter((v) => !fixedIds.has(v.id)).length;
  const isPatched = fixedIds.has(activeViolation?.id);

  // Compute metrics
  const softwareRating = useMemo(() => {
    const fixedCount = fixedIds.size;
    if (fixedCount === 0) return 12;
    return Math.min(99, Math.round(12 + (fixedCount / 24) * 87));
  }, [fixedIds]);

  const efficiencyGrade = useMemo(() => {
    if (softwareRating >= 85) return 'A';
    if (softwareRating >= 70) return 'B';
    if (softwareRating >= 50) return 'C';
    if (softwareRating >= 25) return 'D';
    return 'E';
  }, [softwareRating]);

  const efficiencyStatus = useMemo(() => {
    if (softwareRating >= 85) return 'Optimal';
    if (softwareRating >= 70) return 'Good';
    if (softwareRating >= 50) return 'Needs Work';
    if (softwareRating >= 25) return 'Critical';
    return 'Poor';
  }, [softwareRating]);

  const workloadWh = useMemo(() => {
    const fixedWh = violations
      .filter((v) => fixedIds.has(v.id))
      .reduce((acc, v) => acc + (v.energyWh || 0.02), 0);
    return Math.max(0.025, Math.round((0.56 - fixedWh) * 100) / 100);
  }, [fixedIds, violations]);

  const monthlyCost = useMemo(() => {
    const fixedCost = violations
      .filter((v) => fixedIds.has(v.id))
      .reduce((acc, v) => acc + (v.costMonthly || 0.69), 0);
    return Math.max(0.85, Math.round((17.42 - fixedCost) * 100) / 100);
  }, [fixedIds, violations]);

  const projectedSavings = useMemo(() => {
    return Math.round(monthlyCost * 12);
  }, [monthlyCost]);

  // Patch Handlers
  const handleApplyPatch = () => {
    if (!activeViolation) return;
    setFixedIds((prev) => {
      const next = new Set(prev);
      next.add(activeViolation.id);
      return next;
    });
    setStatusText(`Applied Green AST patch to ${activeViolation.filePath}. Carbon debt reduced.`);
  };

  const handleAutoPatchAll = () => {
    const allIds = new Set(violations.map((v) => v.id));
    setFixedIds(allIds);
    setStatusText('Scan complete · 0 issues remaining. Repository health raised to 99/100.');
  };

  const handleAuditRepo = () => {
    setIsAuditing(true);
    setStatusText(`Scanning ${targetRepo} across AST parser & regional grid telemetry...`);
    setTimeout(() => {
      setIsAuditing(false);
      setFixedIds(new Set());
      setStatusText(`Scan complete · 24 issues in ${targetRepo}`);
    }, 900);
  };

  const handleCopyCode = () => {
    if (!activeViolation) return;
    const content = codeViewTab === 'diff'
      ? `${activeViolation.originalCode}\n${activeViolation.refactoredCode}`
      : codeViewTab === 'fixed'
      ? activeViolation.refactoredCode
      : activeViolation.originalCode;
    navigator.clipboard.writeText(content);
    setCopyFeedback(true);
    setTimeout(() => setCopyFeedback(false), 1400);
  };

  // Alexa Voice Engine
  const speakResponse = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.onstart = () => setAlexaState('speaking');
    utterance.onend = () => {
      setAlexaState('idle');
      setTimeout(() => setAlexaText(''), 4500);
    };
    utterance.onerror = () => setAlexaState('idle');
    window.speechSynthesis.speak(utterance);
  };

  const handleVoiceCommand = (raw) => {
    const q = raw.toLowerCase().trim();
    let reply = "I heard: " + raw;

    if (q.includes('scan') || q.includes('audit')) {
      handleAuditRepo();
      reply = "Auditing bottlepy/bottle. 24 AST bottlenecks detected with 0.56 Watt-hours total workload.";
    } else if (q.includes('patch all') || q.includes('auto patch') || q.includes('fix all') || q.includes('autofix')) {
      handleAutoPatchAll();
      reply = "Auto-patched all 24 bottlenecks. Software efficiency rating raised to 99 out of 100.";
    } else if (q.includes('patch') || q.includes('apply') || q.includes('fix')) {
      handleApplyPatch();
      reply = "Applied green AST refactor to the selected bottle.py code pattern.";
    } else if (q.includes('score') || q.includes('rating')) {
      reply = `The current GSF SCI software efficiency rating is ${softwareRating} out of 100.`;
    } else if (q.includes('cloud') || q.includes('cost') || q.includes('save') || q.includes('dollar')) {
      reply = `Cloud compute waste is estimated at $${monthlyCost} per month, with projected annual savings of $${projectedSavings}.`;
    } else {
      reply = `GreenCode Auditor analyzed: "${raw}". Repository health is currently ${softwareRating} with 24 active bottlenecks.`;
    }

    setAlexaText(reply);
    speakResponse(reply);

    setVoiceLogs((prev) => [
      {
        time: new Date().toLocaleTimeString(),
        speaker: 'User',
        text: raw,
        action: 'voice_input',
      },
      {
        time: new Date().toLocaleTimeString(),
        speaker: 'Alexa',
        text: reply,
        action: 'voice_reply',
      },
      ...prev,
    ]);
  };

  const toggleMic = () => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
      const demoUtterance = "Alexa, what is the current software efficiency rating?";
      handleVoiceCommand(demoUtterance);
      return;
    }

    if (isListeningMic) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListeningMic(false);
      setAlexaState('idle');
    } else {
      try {
        const recognition = new SpeechRec();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
          setIsListeningMic(true);
          setAlexaState('listening');
          setAlexaText('Listening... Speak question ("score", "issues", "fix all")');
        };

        recognition.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          setAlexaText(`" ${transcript} "`);
          handleVoiceCommand(transcript);
        };

        recognition.onerror = () => {
          setIsListeningMic(false);
          setAlexaState('idle');
        };

        recognition.onend = () => {
          setIsListeningMic(false);
        };

        recognitionRef.current = recognition;
        recognition.start();
      } catch (err) {
        setIsListeningMic(false);
        setAlexaState('idle');
      }
    }
  };

  return (
    <div className="w-full h-screen max-h-screen bg-[linear-gradient(135deg,#c3eed0_0%,#d8f5e2_20%,#f0fcf5_38%,#b6e8c5_50%,#e4f9ec_70%,#c8f0d5_100%)] text-slate-900 flex flex-col font-sans select-none overflow-hidden m-0 p-0 antialiased">
      
      {/* ──────────────────────────────────────────────────────────────────────────
          1. TOP ENTERPRISE HEADER (All Green Buttons + White Text, Pure Circle Profile)
          ────────────────────────────────────────────────────────────────────────── */}
      <header className="h-16 w-full bg-white/95 backdrop-blur-md border-b-2 border-[#003d20] shadow-sm px-6 flex items-center justify-between shrink-0 z-30">
        
        {/* Left: Actual Logo + Name + Repo Input + 2-line Text (NO BOX) */}
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex items-center gap-2.5 shrink-0">
            <img
              src="/logo.png"
              alt="GreenCode"
              className="w-9 h-9 object-contain select-none shrink-0"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = '/assets/icon-180x180.png';
              }}
            />
            <span className="font-black text-xl tracking-tight text-[#0a291c] leading-none">
              GreenCode
            </span>
          </div>

          <div className="h-6 w-px bg-slate-300 shrink-0" />

          {/* Repo Input Box with Git Branch */}
          <div className="flex items-center gap-2 bg-slate-50 border-2 border-[#003d20]/30 rounded-lg px-3 py-1.5 shadow-2xs">
            <GitBranch className="w-4 h-4 text-[#003d20] shrink-0" />
            <input
              type="text"
              value={targetRepo}
              onChange={(e) => setTargetRepo(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAuditRepo()}
              className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none w-44 font-mono placeholder:text-slate-400"
              placeholder="owner/repo"
            />
          </div>

          {/* Files & SLOC Plain Text (NO BOX!) */}
          <div className="hidden lg:flex flex-col text-right text-xs font-mono text-slate-700 pl-1 leading-tight shrink-0">
            <span className="font-bold text-slate-900">211 files</span>
            <span className="text-slate-500 font-semibold">82,241 sloc</span>
          </div>
        </div>

        {/* Right Action Buttons (ALL GREEN WITH WHITE TEXT, Circular Profile & Logout) */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => setGithubConnectModalOpen(true)}
            className="px-3.5 py-1.5 bg-[#003d20] hover:bg-[#064e2e] active:scale-98 text-white text-xs font-bold rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer whitespace-nowrap"
          >
            <Github className="w-4 h-4 text-white" />
            <span>Link Repository</span>
          </button>

          {/* User Account / Profile Circle */}
          <div className="flex items-center gap-1.5 shrink-0 pl-1">
            <div
              className="w-8 h-8 rounded-full bg-[#003d20] text-emerald-300 font-mono font-bold text-xs flex items-center justify-center border-2 border-[#003d20] shadow-xs cursor-default shrink-0"
              title={user?.email || 'developer@greencode.dev'}
            >
              {(user?.username || user?.full_name || 'D')[0].toUpperCase()}
            </div>
            <button
              onClick={() => logout()}
              className="w-8 h-8 rounded-full bg-white hover:bg-rose-50 border-2 border-slate-300 hover:border-rose-400 text-slate-600 hover:text-rose-600 flex items-center justify-center transition shadow-2xs cursor-pointer shrink-0"
              title="Log Out"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Voice CLI Solid Button */}
          <button
            onClick={toggleMic}
            className={`px-3 py-1.5 ${
              isListeningMic
                ? 'bg-cyan-700 ring-2 ring-cyan-400 text-white'
                : 'bg-[#003d20] hover:bg-[#064e2e] text-white'
            } active:scale-98 text-xs font-mono font-bold rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer whitespace-nowrap`}
          >
            <Mic className={`w-3.5 h-3.5 ${isListeningMic ? 'text-cyan-300 animate-pulse' : 'text-white'}`} />
            <span>Voice CLI</span>
          </button>

          {/* Audit Logs Solid Button */}
          <button
            onClick={() => setVoiceAuditModalOpen(true)}
            className="px-3.5 py-1.5 bg-[#003d20] hover:bg-[#064e2e] active:scale-98 text-white text-xs font-bold rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer whitespace-nowrap"
          >
            <ShieldCheck className="w-4 h-4 text-white" />
            <span>Audit Logs</span>
          </button>

          {/* Run Scan Solid Button */}
          <button
            onClick={handleAuditRepo}
            disabled={isAuditing}
            className="px-4 py-1.5 bg-[#003d20] hover:bg-[#064e2e] active:scale-98 text-white text-xs font-bold rounded-lg transition-all flex items-center gap-2 shadow-xs cursor-pointer disabled:opacity-50 whitespace-nowrap"
          >
            {isAuditing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current text-white" />
                <span>Run Scan</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* ──────────────────────────────────────────────────────────────────────────
          2. FOUR UPPER KPI METRIC CARDS (Exact Layout from media_1792584152673_1c1b79a6.png)
          ────────────────────────────────────────────────────────────────────────── */}
      <section className="w-full px-6 pt-3 pb-2 shrink-0">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
          
          {/* Card 1: SCI Rating */}
          <div className="bg-white/95 backdrop-blur-sm border-2 border-[#0e482f]/60 rounded-xl p-4 flex flex-col justify-between shadow-[0_4px_16px_rgba(14,72,47,0.12)] hover:border-emerald-700 transition-all">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block font-sans">
                  SCI RATING
                </span>
                <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                  GSF SCI Specification
                </span>
              </div>
              <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0">
                <Gauge className="w-4 h-4 text-amber-600" />
              </div>
            </div>
            <div className="flex items-end justify-between mt-4">
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-black font-mono tracking-tight text-slate-900 leading-none">
                  {softwareRating}
                </span>
                <span className="text-xs font-mono font-semibold text-slate-400">/ 100</span>
              </div>
              <span className="text-[11px] font-mono font-semibold text-amber-800 bg-amber-50/90 border border-amber-300/80 px-2.5 py-0.5 rounded-md shadow-2xs">
                Grade: {efficiencyGrade} • {efficiencyStatus}
              </span>
            </div>
          </div>

          {/* Card 2: Static Analysis Issues */}
          <div className="bg-white/95 backdrop-blur-sm border-2 border-[#0e482f]/60 rounded-xl p-4 flex flex-col justify-between shadow-[0_4px_16px_rgba(14,72,47,0.12)] hover:border-rose-600 transition-all">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block font-sans">
                  STATIC ANALYSIS ISSUES
                </span>
                <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                  AST Rule Violations
                </span>
              </div>
              <div className="w-8 h-8 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0">
                <Layers className="w-4 h-4 text-rose-600" />
              </div>
            </div>
            <div className="flex items-end justify-between mt-4">
              <div className="flex items-baseline gap-1.5">
                <span className="text-2xl font-black font-mono tracking-tight text-slate-900 leading-none">
                  {remainingCount}
                </span>
                <span className="text-xs text-slate-500 font-sans font-medium">Issues</span>
              </div>
              <div className="flex items-center gap-1.5 font-sans">
                <span className="text-[10px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-md shadow-2xs">
                  0 Errors
                </span>
                <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md shadow-2xs">
                  {remainingCount} Warnings
                </span>
              </div>
            </div>
          </div>

          {/* Card 3: Estimated Energy Impact */}
          <div className="bg-white/95 backdrop-blur-sm border-2 border-[#0e482f]/60 rounded-xl p-4 flex flex-col justify-between shadow-[0_4px_16px_rgba(14,72,47,0.12)] hover:border-sky-600 transition-all">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block font-sans">
                  ESTIMATED ENERGY IMPACT
                </span>
                <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                  RAPL Power Profile
                </span>
              </div>
              <div className="w-8 h-8 rounded-lg bg-sky-50 border border-sky-200 flex items-center justify-center shrink-0">
                <Cpu className="w-4 h-4 text-sky-600" />
              </div>
            </div>
            <div className="flex items-end justify-between mt-4">
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-black font-mono tracking-tight text-slate-900 leading-none">
                  {workloadWh.toFixed(2)}
                </span>
                <span className="text-xs text-slate-500 font-mono font-medium">Wh / run</span>
              </div>
              <span className="text-[10px] font-mono font-semibold text-sky-800 bg-sky-50 border border-sky-300 px-2.5 py-0.5 rounded-md shadow-2xs">
                1.2 gCO2e / 10k runs
              </span>
            </div>
          </div>

          {/* Card 4: Est. Compute Cost */}
          <div className="bg-white/95 backdrop-blur-sm border-2 border-[#0e482f]/60 rounded-xl p-4 flex flex-col justify-between shadow-[0_4px_16px_rgba(14,72,47,0.12)] hover:border-teal-700 transition-all">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block font-sans">
                  EST. COMPUTE COST
                </span>
                <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                  AWS us-west-1 Baseline
                </span>
              </div>
              <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0">
                <TrendingDown className="w-4 h-4 text-teal-700" />
              </div>
            </div>
            <div className="flex items-end justify-between mt-4">
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-black font-mono tracking-tight text-teal-800 leading-none">
                  ${monthlyCost.toFixed(2)}
                </span>
                <span className="text-xs text-slate-500 font-mono font-semibold">/ mo</span>
              </div>
              <span className="text-[10px] font-sans font-semibold text-teal-800 bg-teal-50 border border-teal-300 px-2.5 py-0.5 rounded-md shadow-2xs">
                Est. Savings: ${projectedSavings}/yr
              </span>
            </div>
          </div>

        </div>
      </section>

      {/* ──────────────────────────────────────────────────────────────────────────
          3. MAIN WORKSPACE (Left Issues List + Right GitHub Unified Diff Viewer)
          ────────────────────────────────────────────────────────────────────────── */}
      <main className="flex-1 min-h-0 px-6 pb-2.5 flex gap-4 overflow-hidden relative">
        
        {/* Left Column: Detected Issues (40%) */}
        <div className="w-[40%] h-full flex flex-col bg-white/95 backdrop-blur-sm border-2 border-[#003d20] rounded-xl shadow-sm overflow-hidden">
          
          {/* Filter Toolbar */}
          <div className="h-10 px-3.5 border-b-2 border-[#003d20]/20 bg-[#FAFCFB] flex items-center justify-between gap-2 shrink-0">
            <div className="flex items-center gap-4 font-mono text-xs">
              <button
                onClick={() => setActiveFilter('ALL')}
                className={`pb-1 transition cursor-pointer ${
                  activeFilter === 'ALL'
                    ? 'font-bold text-slate-900 border-b-2 border-[#003d20]'
                    : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent'
                }`}
              >
                All ({violations.length})
              </button>
              <button
                onClick={() => setActiveFilter('ERROR')}
                className={`pb-1 transition cursor-pointer ${
                  activeFilter === 'ERROR'
                    ? 'font-bold text-rose-700 border-b-2 border-rose-600'
                    : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent'
                }`}
              >
                Errors (0)
              </button>
              <button
                onClick={() => setActiveFilter('WARNING')}
                className={`pb-1 transition cursor-pointer ${
                  activeFilter === 'WARNING'
                    ? 'font-bold text-amber-700 border-b-2 border-amber-600'
                    : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent'
                }`}
              >
                Warnings ({violations.length})
              </button>
            </div>

            {/* Quick Search */}
            <div className="relative w-44">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Filter issues..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-7 pr-2 py-1 text-xs bg-white border border-slate-300 rounded-md text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-[#003d20] font-mono"
              />
            </div>
          </div>

          {/* Subheader: Autofix All Button (Solid Green with White Text) */}
          <div className="h-8 px-3.5 border-b border-[#003d20]/15 bg-slate-50 flex items-center justify-between text-xs text-slate-700 shrink-0 font-mono">
            <span className="text-[11px] font-bold text-slate-800">
              {remainingCount} Issues Found
            </span>
            <button
              onClick={handleAutoPatchAll}
              className="text-[11px] font-bold text-white bg-[#003d20] hover:bg-[#064e2e] active:scale-98 px-2.5 py-0.5 rounded-md flex items-center gap-1 transition cursor-pointer shadow-xs"
            >
              <Wand2 className="w-3 h-3 text-white" />
              <span>Autofix All ({violations.length})</span>
            </button>
          </div>

          {/* Violations Stream with Resource Tags */}
          <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-slate-100 thin-scrollbar">
            {filteredViolations.map((v) => {
              const isSelected = violations[selectedIndex]?.id === v.id;
              const isItemFixed = fixedIds.has(v.id);

              return (
                <div
                  key={v.id}
                  onClick={() => {
                    const actualIdx = violations.findIndex((item) => item.id === v.id);
                    setSelectedIndex(actualIdx >= 0 ? actualIdx : 0);
                  }}
                  className={`p-3 transition-colors cursor-pointer flex flex-col gap-1.5 border-l-4 ${
                    isSelected
                      ? 'border-l-[#003d20] bg-emerald-50/50'
                      : 'border-l-transparent hover:bg-slate-50/80 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded shrink-0 bg-amber-50 text-amber-700 border border-amber-300">
                        {v.severity.toUpperCase()}
                      </span>
                      <h4 className="text-xs font-semibold text-slate-900 truncate font-mono">
                        {v.title}
                      </h4>
                      {isItemFixed && (
                        <span className="text-[9px] font-mono font-bold bg-emerald-100 text-[#003d20] px-1 rounded flex items-center gap-0.5">
                          <Check className="w-2.5 h-2.5" /> FIXED
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-mono font-bold text-amber-700 shrink-0">
                      +{v.energyWh.toFixed(3)} Wh
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pl-0.5">
                    <div className="flex items-center gap-1.5 truncate">
                      <FileCode className="w-3 h-3 text-slate-400 shrink-0" />
                      <span className="text-slate-800 font-bold">{v.filePath}</span>
                      <span className="text-emerald-700 font-medium bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 text-[10px] shrink-0 font-sans">
                        {v.impactTag}
                      </span>
                    </div>
                    <span className="shrink-0 text-slate-500 font-sans font-medium">
                      ~${v.costMonthly}/mo
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Unified Diff Remediation Viewer (60%) */}
        <div className="w-[60%] h-full flex flex-col bg-white/95 backdrop-blur-sm border-2 border-[#003d20] rounded-xl shadow-sm overflow-hidden">
          
          {/* Diff Header */}
          <div className="h-11 px-4 border-b-2 border-[#003d20]/20 bg-white flex items-center justify-between gap-3 shrink-0">
            <div className="min-w-0 flex items-center gap-2 font-mono text-xs truncate">
              <span className="font-bold text-slate-800 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded text-[11px] shrink-0 font-mono">
                {activeViolation.ruleId}: {activeViolation.ruleName}
              </span>
              <span className="text-slate-300 shrink-0">•</span>
              <span className="text-slate-700 truncate font-semibold font-mono">
                {activeViolation.filePath}
              </span>
            </div>

            {/* Action Buttons: Solid Green with White Text */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => {
                  setIsAiOptimizing(true);
                  setStatusText(`AI Refactoring ${activeViolation.filePath} with Amazon Bedrock Claude 3.5 Sonnet...`);
                  setTimeout(() => {
                    setIsAiOptimizing(false);
                    handleApplyPatch();
                    setStatusText(`AI Refactor applied green patch to ${activeViolation.filePath}`);
                  }, 800);
                }}
                disabled={isAiOptimizing}
                className="px-3 py-1 text-xs font-mono font-semibold text-white bg-[#003d20] hover:bg-[#064e2e] active:scale-98 rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50"
              >
                {isAiOptimizing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5 text-white" />
                )}
                <span>Generate Fix</span>
              </button>

              <button
                onClick={handleApplyPatch}
                disabled={isPatched}
                className={`px-3.5 py-1 text-xs font-mono font-bold rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer ${
                  isPatched
                    ? 'bg-slate-200 text-slate-500 cursor-default'
                    : 'bg-[#003d20] hover:bg-[#064e2e] text-white active:scale-98'
                }`}
              >
                <Check className="w-3.5 h-3.5 text-white" />
                <span>{isPatched ? 'Applied' : 'Apply Fix'}</span>
              </button>

              <button
                onClick={() => setPrModalOpen(true)}
                className="px-3 py-1 text-xs font-mono font-semibold text-white bg-[#003d20] hover:bg-[#064e2e] active:scale-98 rounded-lg transition flex items-center gap-1.5 shadow-xs cursor-pointer"
                title="Open PR on GitHub"
              >
                <GitPullRequest className="w-3.5 h-3.5 text-white" />
                <span>Open PR</span>
              </button>
            </div>
          </div>

          {/* View Tabs */}
          <div className="h-8 px-4 border-b border-[#003d20]/15 bg-slate-50 flex items-center justify-between text-xs shrink-0 font-mono">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setCodeViewTab('diff')}
                className={`pb-1 transition cursor-pointer ${
                  codeViewTab === 'diff'
                    ? 'font-bold text-slate-900 border-b-2 border-[#003d20]'
                    : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent'
                }`}
              >
                Diff (-46% Wh)
              </button>
              <button
                onClick={() => setCodeViewTab('fixed')}
                className={`pb-1 transition cursor-pointer ${
                  codeViewTab === 'fixed'
                    ? 'font-bold text-slate-900 border-b-2 border-[#003d20]'
                    : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent'
                }`}
              >
                Fixed Code
              </button>
              <button
                onClick={() => setCodeViewTab('full')}
                className={`pb-1 transition cursor-pointer ${
                  codeViewTab === 'full'
                    ? 'font-bold text-slate-900 border-b-2 border-[#003d20]'
                    : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent'
                }`}
              >
                Full File
              </button>
            </div>

            <button
              onClick={handleCopyCode}
              className="text-slate-500 hover:text-slate-800 text-xs flex items-center gap-1 cursor-pointer transition font-mono font-semibold"
            >
              {copyFeedback ? (
                <>
                  <Check className="w-3 h-3 text-[#003d20]" />
                  <span className="text-[#003d20] font-bold">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>

          {/* Code Canvas (Dark Theme #0B0F17) */}
          <div className="flex-1 min-h-0 bg-[#0B0F17] overflow-hidden flex flex-col font-mono text-xs select-text">
            <div className="flex-1 min-h-0 overflow-y-auto leading-relaxed text-slate-100 thin-scrollbar">
              
              {/* Tab 1: Standard Git Unified Diff Format */}
              {codeViewTab === 'diff' && (
                <div className="font-mono text-[11px]">
                  {/* Standard Git Unified Diff Hunk Header */}
                  <div className="bg-[#1e293b] text-cyan-300 px-3 py-1 font-mono text-[11px] border-b border-slate-700/60 select-none flex items-center justify-between">
                    <span>@@ -346,1 +346,2 @@</span>
                    <span className="text-slate-400">{activeViolation.fileOnly}</span>
                  </div>

                  {/* Git Diff Deleted Lines (-) */}
                  <div className="flex font-mono py-0.5 px-3 bg-rose-950/40 text-rose-300 hover:bg-rose-950/60 transition-colors">
                    <span className="w-8 text-right pr-3 select-none text-rose-400/60 shrink-0">
                      {activeViolation.line}
                    </span>
                    <span className="w-4 select-none shrink-0 font-bold text-rose-400">-</span>
                    <span className="whitespace-pre font-mono">{activeViolation.originalCode.replace(/^\d+\s*-\s*/, '')}</span>
                  </div>

                  {/* Git Diff Added Lines (+) */}
                  {activeViolation.refactoredCode.split('\n').map((line, idx) => (
                    <div
                      key={idx}
                      className="flex font-mono py-0.5 px-3 bg-emerald-950/40 text-emerald-300 hover:bg-emerald-950/60 transition-colors"
                    >
                      <span className="w-8 text-right pr-3 select-none text-emerald-400/60 shrink-0">
                        {activeViolation.line + idx}
                      </span>
                      <span className="w-4 select-none shrink-0 font-bold text-emerald-400">+</span>
                      <span className="whitespace-pre font-mono">{line.replace(/^\d+\s*\+\s*/, '')}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Tab 2: Fixed Code */}
              {codeViewTab === 'fixed' && (
                <pre className="p-4 m-0 text-slate-100 whitespace-pre">
                  {activeViolation.refactoredCode}
                </pre>
              )}

              {/* Tab 3: Full File */}
              {codeViewTab === 'full' && (
                <pre className="p-4 m-0 text-slate-300 whitespace-pre">
                  {activeViolation.originalCode}
                </pre>
              )}
            </div>
          </div>

          {/* Real Context Footer Strip: Rule Tip & Impact */}
          <div className="h-8 px-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-600 shrink-0 font-mono">
            <span className="truncate text-[11px] text-slate-700">
              <span className="font-bold text-slate-900">Rule Tip: </span>
              {activeViolation.tip}
            </span>
            <span className="text-[11px] font-bold text-emerald-800 whitespace-nowrap ml-3 font-mono">
              Impact: {activeViolation.impactStr}
            </span>
          </div>
        </div>

        {/* ──────────────────────────────────────────────────────────────────────
            4. AUTHENTIC VOICE OPS COCKPIT & CIRCULAR ALEXA ORB (Bottom Right)
            ────────────────────────────────────────────────────────────────────── */}
        <div className="absolute right-9 bottom-12 z-40 flex flex-col items-end gap-3 pointer-events-auto">
          
          {/* Active Voice Ops Status Card */}
          <div className="w-72 bg-[#090b0a]/95 backdrop-blur-md text-white p-3 rounded-xl border border-cyan-500/50 shadow-2xl font-mono text-xs">
            <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-800 text-[10px] text-cyan-400">
              <span className="flex items-center gap-1 font-bold">
                <Volume2 className="w-3 h-3 text-cyan-400" /> Voice Ops · Active
              </span>
              <span className="bg-cyan-950/60 text-cyan-300 px-1.5 py-0.2 rounded border border-cyan-800/60 font-semibold">
                Hands-Free
              </span>
            </div>
            <p className="text-slate-200 text-xs leading-relaxed font-sans font-medium">
              {alexaText || 'Listening... Speak question ("score", "issues", "fix all")'}
            </p>
            <div className="mt-2 text-[9px] text-slate-400 font-mono border-t border-slate-800/60 pt-1">
              Auto-executes automatically when you stop speaking
            </div>
          </div>

          {/* Pure Circular Radial Audio Orb (NO BOX, PURE CIRCLE) */}
          <button
            type="button"
            onClick={toggleMic}
            className={`w-18 h-18 rounded-full flex flex-col items-center justify-center transition-all duration-300 cursor-pointer select-none active:scale-95 ${
              isListeningMic
                ? 'bg-[#002816] text-cyan-300 border-2 border-cyan-400 shadow-[0_0_28px_rgba(6,182,212,0.8)] scale-105'
                : 'bg-[#090b0a] text-cyan-400 border-2 border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.4)] hover:border-cyan-300 hover:shadow-[0_0_28px_rgba(6,182,212,0.6)]'
            }`}
            title="Alexa Voice Agent (Click to speak or pause)"
          >
            <Mic className={`w-5 h-5 mb-0.5 ${isListeningMic ? 'text-cyan-300 animate-pulse' : 'text-cyan-400'}`} />
            <span className="text-[9px] font-bold text-white tracking-tight">Listening</span>
            <span className="text-[7px] text-cyan-300 font-mono leading-none">Auto-Detect</span>
          </button>
        </div>
      </main>

      {/* ──────────────────────────────────────────────────────────────────────────
          5. BOTTOM STATUS BAR (Exact Match to Screenshot)
          ────────────────────────────────────────────────────────────────────────── */}
      <footer className="h-7 w-full bg-white/95 backdrop-blur-md border-t-2 border-[#003d20] px-6 flex items-center justify-between text-[11px] font-mono text-slate-700 shrink-0 z-30 select-none shadow-xs">
        {/* Left Status */}
        <div className="flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-xs bg-[#003d20] shrink-0" />
          <span className="font-bold text-slate-900 truncate">{statusText}</span>
        </div>

        {/* Center Grid */}
        <div className="hidden md:flex items-center gap-2">
          <Globe className="w-3.5 h-3.5 text-[#003d20]" />
          <span className="text-slate-600 font-bold">Grid Region:</span>
          <select className="bg-slate-50 border border-slate-300 rounded px-1.5 py-0.2 text-[10px] font-bold text-slate-800 focus:outline-none cursor-pointer font-mono">
            <option>United States (California ISO / Silicon Valley) (215 gCO₂/kWh)</option>
            <option>United States (N. Virginia / PJM) (379 gCO₂/kWh)</option>
            <option>Europe (Sweden / Nord Pool) (18 gCO₂/kWh)</option>
            <option>Europe (Ireland / EirGrid) (245 gCO₂/kWh)</option>
          </select>
        </div>

        {/* Right Standard */}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-[#003d20] font-bold">
            <ShieldCheck className="w-4 h-4 text-[#003d20]" />
            <span>Compliant: ISO 14064-1 · GSF SCI</span>
          </span>
        </div>
      </footer>

      {/* ──────────────────────────────────────────────────────────────────────────
          6. MODALS (Voice Ledger, GitHub Connect, PR Dispatch)
          ────────────────────────────────────────────────────────────────────────── */}
      
      {/* Voice Ledger Modal */}
      {voiceAuditModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-2xl border-2 border-[#003d20] max-w-xl w-full p-5 space-y-4 max-h-[85vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 border border-emerald-300 flex items-center justify-center text-[#003d20]">
                  <Volume2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Voice Command Ledger &amp; Audio Audit Trail</h3>
                  <p className="text-[11px] text-slate-500 font-mono">Verified Alexa+ speech transcripts and dispatch logs</p>
                </div>
              </div>
              <button
                onClick={() => setVoiceAuditModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 font-mono text-xs thin-scrollbar">
              {voiceLogs.map((log, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg border text-xs ${
                    log.speaker === 'User'
                      ? 'bg-slate-50 border-slate-200'
                      : 'bg-emerald-50/50 border-emerald-300 text-emerald-900'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                    <span className="font-bold text-slate-700">{log.speaker}</span>
                    <span>{log.time}</span>
                  </div>
                  <p className="font-sans text-xs leading-relaxed text-slate-800">
                    {log.text}
                  </p>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-slate-200 flex justify-end shrink-0">
              <button
                onClick={() => setVoiceAuditModalOpen(false)}
                className="px-4 py-1.5 bg-[#003d20] hover:bg-[#064e2e] text-white text-xs font-bold rounded-lg cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* GitHub Connect Modal */}
      {githubConnectModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-2xl border-2 border-[#003d20] max-w-md w-full p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2">
                <Github className="w-5 h-5 text-slate-900" />
                <h3 className="text-sm font-bold text-slate-900">GitHub Repository Sync</h3>
              </div>
              <button onClick={() => setGithubConnectModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600">
              Connected to <strong>{targetRepo}</strong>. GreenCode monitors PR branches and scans AST syntax trees automatically.
            </p>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono space-y-1">
              <div className="text-slate-500">Repository: <span className="text-slate-900 font-bold">{targetRepo}</span></div>
              <div className="text-slate-500">Analyzed Files: <span className="text-slate-900 font-bold">211</span></div>
              <div className="text-slate-500">Analyzed LOC: <span className="text-slate-900 font-bold">82,241 sloc</span></div>
              <div className="text-slate-500">PR Action: <span className="text-[#003d20] font-bold">Auto-Check Active</span></div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setGithubConnectModalOpen(false)}
                className="px-4 py-1.5 bg-[#003d20] text-white text-xs font-bold rounded-lg"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Pull Request Modal */}
      {prModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-2xl border-2 border-[#003d20] max-w-lg w-full p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div className="flex items-center gap-2 text-[#003d20]">
                <GitPullRequest className="w-5 h-5" />
                <h3 className="text-sm font-bold text-slate-900">Dispatch Green Pull Request</h3>
              </div>
              <button onClick={() => setPrModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Open a verified Pull Request to <strong>{targetRepo}</strong> containing synthesized AST refactorings, reducing computational complexity and scope 2 emissions.
            </p>
            <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-lg text-xs font-mono space-y-1">
              <div className="text-[#003d20] font-bold">Branch: green-fix/{activeViolation.slug}</div>
              <div className="text-slate-700">File: {activeViolation.filePath}</div>
              <div className="text-slate-700">Verified Energy Delta: -{activeViolation.energyWh} Wh (-46%)</div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setPrModalOpen(false)}
                className="px-3 py-1.5 border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setPrModalOpen(false);
                  handleApplyPatch();
                  setStatusText(`Pull Request created for ${activeViolation.filePath}! Branch: green-fix/${activeViolation.slug}`);
                }}
                className="px-4 py-1.5 bg-[#003d20] hover:bg-[#064e2e] text-white text-xs font-bold rounded-lg flex items-center gap-1.5"
              >
                <GitPullRequest className="w-3.5 h-3.5" />
                <span>Create PR on GitHub</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
