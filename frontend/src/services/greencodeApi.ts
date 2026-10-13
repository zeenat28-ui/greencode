import api from './api';
import {
  AuthResponse,
  ScanResult,
  ProfilingResult,
  RefactorResult,
  ZoneData,
  GitHubRepo,
  GitHubUser,
  GitHubBranch,
  RepositoryRecord,
  RepositoryPage,
  User,
  TaskStatus,
  BenchmarkScript,
  RepoPreflight,
  DynamicAnalysisStatus,
  DynamicAnalysisResult,
  AuditContext,
  HealthStatus,
} from '../types';

// ---------------------------------------------------------------------------
// Authentication - GitHub Personal Access Token is the only supported method.
// ---------------------------------------------------------------------------
export const authService = {
  signInWithGitHub: (githubToken: string) =>
    api.post<AuthResponse>('/api/auth/github', { github_token: githubToken }),

  refresh: (refreshToken: string) =>
    api.post<AuthResponse>('/api/auth/refresh', { refresh_token: refreshToken }),

  logout: () => api.post<{ success: boolean }>('/api/auth/logout'),

  me: () => api.get<{ authenticated: boolean; user: User }>('/api/auth/me'),

  getUser: (userId: number) => api.get<User>(`/api/auth/user/${userId}`),

  updateProfile: (userId: number, data: { github_token?: string; github_username?: string; full_name?: string }) =>
    api.put<{ success: boolean; message: string; user: User }>(`/api/auth/user/${userId}`, data),
};

// ---------------------------------------------------------------------------
// GitHub repository auditing
// ---------------------------------------------------------------------------
export const githubService = {
  getAuthenticatedUser: () => api.get<{ authenticated: boolean; user: GitHubUser }>('/github/user'),

  listRepositories: (limit: number = 50) =>
    api.get<{ count: number; repositories: GitHubRepo[]; message?: string }>('/github/repos', {
      params: { limit },
    }),

  listBranches: (owner: string, name: string) =>
    api.get<{ count: number; branches: GitHubBranch[] }>(
      `/github/repos/${owner}/${name}/branches`
    ),

  inspect: (owner: string, name: string) =>
    api.get<RepoPreflight>(`/github/repos/${owner}/${name}/inspect`),

  createPullRequest: (
    repoFullName: string,
    filePath: string,
    refactoredCode: string,
    violationTitle: string,
    energyReductionPct: number,
    carbonSaved10k: number,
    originalSnippet?: string
  ) =>
    api.post<{ success: boolean; pr_url: string; pr_number: number; branch: string }>(
      '/github/pull-request',
      {
        repo_full_name: repoFullName,
        file_path: filePath,
        refactored_code: refactoredCode,
        violation_title: violationTitle,
        energy_reduction_pct: energyReductionPct,
        carbon_saved_10k: carbonSaved10k,
        original_snippet: originalSnippet,
      }
    ),
};

export const scanService = {
  /** Synchronous audit. The backend rejects repos over its sync size ceiling. */
  scanGitHub: (repo: string, ref?: string) =>
    api.post<ScanResult>('/api/scan/github', { repo, ref }),

  /** Background audit - returns a task id to poll via `getTaskStatus`. */
  scanGitHubAsync: (repo: string, ref?: string) =>
    api.post<{ task_id: string; status: string; queue_backend: string; message: string }>(
      '/api/scan/github/async',
      { repo, ref }
    ),

  getTaskStatus: (taskId: string) => api.get<TaskStatus>(`/api/task/${taskId}`),

  getRepositoryDetails: (repoId: number) => api.get<RepositoryRecord>(`/api/repository/${repoId}`),

  getRepositorySarif: (repoId: number) => api.get(`/api/repository/${repoId}/sarif`),

  getHistory: (limit: number = 20, offset: number = 0) =>
    api.get<RepositoryPage>('/api/history', { params: { limit, offset } }),
};

// ---------------------------------------------------------------------------
// Grid telemetry, profiler & refactoring
// ---------------------------------------------------------------------------
export const gridService = {
  getZones: () => api.get<ZoneData[]>('/api/grid/zones'),

  getZoneIntensity: (zone: string) => api.get<ZoneData>(`/api/grid/zone/${zone}`),
};

export const profilerService = {
  listBenchmarks: () => api.get<{ benchmarks: BenchmarkScript[] }>('/api/profile/benchmarks'),

  /**
   * Run a bundled benchmark. `benchmark` is a whitelisted id (e.g. 'heavy_pipeline')
   * - the API rejects anything else, so the profiler can never execute an
   * arbitrary server-side path.
   */
  profile: (benchmark: string, timeoutSec: number, zone: string, repoId?: number) =>
    api.post<ProfilingResult>('/api/profile', {
      benchmark,
      timeout_sec: timeoutSec,
      zone,
      repo_id: repoId,
    }),
};

export const refactorService = {
  refactor: (snippet: string, violationType: string, language: string, fileContext?: string) =>
    api.post<RefactorResult>('/api/refactor', {
      snippet,
      violation_type: violationType,
      language,
      file_context: fileContext,
    }),
};

// ---------------------------------------------------------------------------
// Dynamic analysis
//
// Runs a repository's test/benchmark suite inside a Docker sandbox and reports
// what it actually cost. Unlike the static scan, every figure here is observed
// from execution - though whether it came from a hardware counter or a model is
// reported explicitly, because those are not equally trustworthy.
// ---------------------------------------------------------------------------
export const dynamicService = {
  /**
   * Whether dynamic analysis can run on this deployment, and how energy will be
   * measured. Safe to call unauthenticated - it exposes no repository data.
   */
  getStatus: () => api.get<DynamicAnalysisStatus>('/api/dynamic/status'),

  /**
   * Execute a repository and measure it.
   *
   * @param functionalUnit R in the SCI formula. The number of times the code's
   *   functionality was delivered during the run (e.g. test cases executed).
   *   Leaving this at 1 reports a total, not an intensity, and the API says so.
   */
  analyze: (repoFullName: string, options?: {
    ref?: string;
    gridIntensity?: number;
    functionalUnit?: number;
    timeoutSec?: number;
  }) =>
    api.post<DynamicAnalysisResult>('/api/dynamic/analyze', {
      repo_full_name: repoFullName,
      ref: options?.ref,
      grid_intensity: options?.gridIntensity ?? 380.0,
      functional_unit: options?.functionalUnit ?? 1.0,
      timeout_sec: options?.timeoutSec ?? 60.0,
    }),
};

// ---------------------------------------------------------------------------
// Audit intelligence
// ---------------------------------------------------------------------------
export const auditService = {
  /** Deterministic, prioritised remediation plan for a stored audit. */
  getContext: (repoId: number) => api.get<AuditContext>('/api/audit/context', {
    params: { repo_id: repoId },
  }),

  /** Operational health, including measurement and AI capabilities. */
  getHealth: () => api.get<HealthStatus>('/api/health'),
};

// ---------------------------------------------------------------------------
// Enterprise Scope 1-3 GHG Accounting (CSRD ESRS-E1 & SBTi ICT)
// ---------------------------------------------------------------------------
export const scopeService = {
  calculateInventory: (params: {
    energy_joules: number;
    duration_seconds?: number;
    grid_intensity_gco2_per_kwh?: number;
    runs_per_year?: number;
    team_size?: number;
    dev_hours?: number;
    cloud_provider?: string;
    vcpu_count?: number;
    memory_gb?: number;
    data_transfer_gb?: number;
    grid_zone?: string;
    renewable_rec_pct?: number;
  }) => api.post('/api/scope/inventory', params),
};

// ---------------------------------------------------------------------------
// Machine Learning & Cloud Carbon Telemetry (PyTorch, H100/A100)
// ---------------------------------------------------------------------------
export const mlService = {
  auditCode: (sourceCode: string, filePath?: string) =>
    api.post('/api/ml/audit', { source_code: sourceCode, file_path: filePath }),

  calculateTokens: (params: {
    parameter_count_b: number;
    token_count: number;
    hardware: string;
    grid_intensity_gco2_per_kwh: number;
    runs_per_year: number;
  }) => api.post('/api/ml/tokens', params),
};

// ---------------------------------------------------------------------------
// Energy SLA & Budget Policy Engine
// ---------------------------------------------------------------------------
export const slaService = {
  evaluate: (params: {
    total_joules: number;
    green_score: number;
    sci_gco2e?: number;
    config_path?: string;
  }) => api.post('/api/sla/evaluate', params),
};

// ---------------------------------------------------------------------------
// Commercial Licensing & Quotas
// ---------------------------------------------------------------------------
export const pricingService = {
  getTiers: () => api.get('/api/pricing/tiers'),
};

// ---------------------------------------------------------------------------
// Amazon Web Services (AWS) FinOps & Carbon
//
// Every call here hits a real FastAPI endpoint under /api/aws/*, which in turn
// calls the live AWS SDK (STS AssumeRole, Budgets) and Electricity Maps. There
// is no client-side fabrication: an unlinked account or a missing credential
// surfaces as the backend's own fail-closed response, never a made-up number.
// ---------------------------------------------------------------------------
export const awsService = {
  /** Backend health + count of linked AWS accounts for the org. */
  getHealth: (orgId: number = 1) => api.get('/api/aws/health', { params: { org_id: orgId } }),

  /** Supported AWS regions and their AWS-region -> grid-zone mapping. */
  getRegions: () => api.get('/api/aws/regions'),

  /** Live (or Ember-2024 referenced) marginal carbon intensity for one region. */
  getRegionCarbon: (region: string) =>
    api.get(`/api/aws/regions/${encodeURIComponent(region)}/carbon-intensity`),

  /** Ranked carbon-optimal AWS target regions, honouring data residency. */
  recommendMigration: (params: {
    current_region: string;
    monthly_kwh?: number;
    data_residency?: string;
    max_candidates?: number;
  }) =>
    api.get('/api/aws/regions/recommend-migration', {
      params: {
        current_region: params.current_region,
        monthly_kwh: params.monthly_kwh ?? 1000.0,
        data_residency: params.data_residency ?? 'GLOBAL',
        max_candidates: params.max_candidates ?? 5,
      },
    }),

  /** AWS accounts already linked to the organization. */
  listAccounts: (orgId: number = 1) => api.get('/api/aws/accounts', { params: { org_id: orgId } }),

  /** Link an AWS account via STS AssumeRole (never returns raw credentials). */
  linkAccount: (payload: {
    account_id: string;
    role_arn: string;
    region?: string;
    account_name?: string;
    external_id?: string;
    org_id?: number;
  }) => api.post('/api/aws/accounts/link', { org_id: 1, region: 'us-east-1', ...payload }),

  /** Unlink an AWS account. */
  unlinkAccount: (accountId: string, orgId: number = 1) =>
    api.delete(`/api/aws/accounts/${encodeURIComponent(accountId)}`, { params: { org_id: orgId } }),

  /** Month-to-date AWS Budgets spend + physics-calibrated carbon for a linked account. */
  getCostCarbon: (accountId: string, params?: { region?: string; instance_type?: string; org_id?: number }) =>
    api.get(`/api/aws/accounts/${encodeURIComponent(accountId)}/cost-carbon`, {
      params: {
        region: params?.region ?? 'us-east-1',
        instance_type: params?.instance_type ?? 'c6g.xlarge',
        org_id: params?.org_id ?? 1,
      },
    }),
};

export default {
  authService,
  scanService,
  githubService,
  gridService,
  profilerService,
  refactorService,
  dynamicService,
  auditService,
  scopeService,
  mlService,
  slaService,
  pricingService,
  awsService,
};


