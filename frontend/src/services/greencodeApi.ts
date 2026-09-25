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

export default {
  authService,
  scanService,
  githubService,
  gridService,
  profilerService,
  refactorService,
  dynamicService,
  auditService,
};

