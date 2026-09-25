import api from './api';
import { AuthResponse, ScanResult, ProfilingResult, RefactorResult, CIGateResult, ZoneData, GitHubRepo, GitHubUser, RepositoryRecord, User, TaskStatus } from '../types';

export const authService = {
  signup: (email: string, username: string, password: string, fullName?: string, githubToken?: string) =>
    api.post<AuthResponse>('/api/auth/signup', { email, username, password, full_name: fullName, github_token: githubToken }),

  signin: (login: string, password: string) =>
    api.post<AuthResponse>('/api/auth/signin', { login, password }),

  githubSignIn: (githubToken: string) =>
    api.post<AuthResponse>('/api/auth/github', { github_token: githubToken }),

  getUser: (userId: number) =>
    api.get<User>(`/api/auth/user/${userId}`),

  updateUser: (userId: number, data: { github_token?: string; github_username?: string; avatar_url?: string; full_name?: string }) =>
    api.put<User>(`/api/auth/user/${userId}`, data),

  forgotPassword: (email: string) =>
    api.post('/api/auth/forgot-password', { email }),

  resetPassword: (token: string, newPassword: string) =>
    api.post('/api/auth/reset-password', { token, new_password: newPassword }),

  verifyEmail: (token: string) =>
    api.get(`/api/auth/verify-email?token=${token}`),
};

export const scanService = {
  scanRepository: (repoPath: string, name?: string) =>
    api.post<ScanResult>('/api/scan', { repo_path: repoPath, name }),

  scanRepositoryAsync: (repoPath: string, name?: string) =>
    api.post<{ task_id: string }>('/api/scan/async', { repo_path: repoPath, name }),

  getTaskStatus: (taskId: string) =>
    api.get<TaskStatus>(`/api/task/${taskId}`),

  uploadZip: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post<ScanResult>('/api/scan/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getRepositoryDetails: (repoId: number) =>
    api.get<RepositoryRecord>(`/api/repository/${repoId}`),

  getRepositorySarif: (repoId: number) =>
    api.get(`/api/repository/${repoId}/sarif`),

  scanSarif: (repoPath: string) =>
    api.post('/api/scan/sarif', { repo_path: repoPath }),

  getHistory: () =>
    api.get<{ repositories: RepositoryRecord[]; cumulative_savings: any }>('/api/history'),

  ciEvaluate: (repoPath: string, threshold: number, zone: string) =>
    api.post<CIGateResult>('/api/ci/evaluate', { repo_path: repoPath, threshold, zone }),
};

export const gridService = {
  getZones: () =>
    api.get<any[]>('/api/grid/zones'),

  getZoneIntensity: (zone: string, apiKey?: string) =>
    api.get<ZoneData>(`/api/grid/zone/${zone}`, { params: apiKey ? { api_key: apiKey } : undefined }),
};

export const profilerService = {
  profile: (filePath: string, timeoutSec: number, zone: string, repoId?: number) =>
    api.post<ProfilingResult>('/api/profile', { file_path: filePath, timeout_sec: timeoutSec, zone, repo_id: repoId }),
};

export const refactorService = {
  refactor: (snippet: string, violationType: string, language: string, fileContext?: string, apiKey?: string) =>
    api.post<RefactorResult>('/api/refactor', { snippet, violation_type: violationType, language, file_context: fileContext, api_key: apiKey }),

  applyFixInPlace: (filePath: string, originalSnippet: string, refactoredCode: string, backupDir?: string) =>
    api.post('/api/refactor/apply', { file_path: filePath, original_snippet: originalSnippet, refactored_code: refactoredCode, backup_dir: backupDir }),
};

export const githubService = {
  getAuthenticatedUser: (token?: string) =>
    api.get<{ authenticated: boolean; user?: GitHubUser }>('/github/user', { params: token ? { token } : undefined }),

  listRepositories: (token?: string, limit: number = 30) =>
    api.get<{ count: number; repositories: GitHubRepo[] }>('/github/repos', { params: { token, limit } }),

  createPullRequest: (repoFullName: string, filePath: string, refactoredCode: string, violationTitle: string, energyReductionPct: number, carbonSaved10k: number, token?: string, originalSnippet?: string) =>
    api.post('/github/pull-request', {
      repo_full_name: repoFullName,
      file_path: filePath,
      refactored_code: refactoredCode,
      violation_title: violationTitle,
      energy_reduction_pct: energyReductionPct,
      carbon_saved_10k: carbonSaved10k,
      token,
      original_snippet: originalSnippet,
    }),
};

export default { authService, scanService, gridService, profilerService, refactorService, githubService };
