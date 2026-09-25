export type ViolationType =
  | 'NESTED_LOOPS_DEPTH_3+'
  | 'RAW_DB_CURSOR_NO_CONTEXT'
  | 'UNCACHED_NETWORK_IN_LOOP'
  | 'QUADRATIC_STRING_CONCAT_IN_LOOP'
  | 'HIDDEN_ITERATIVE_COMPUTATION';

export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Violation {
  id?: number;
  file_path: string;
  relative_path?: string;
  language: string;
  line_number: number;
  end_line_number?: number;
  violation_type: ViolationType;
  title: string;
  severity: Severity;
  deduction: number;
  gsf_pattern: string;
  description: string;
  suggested_fix: string;
  snippet: string;
  context_code: string;
  rule_code?: string;
}

export interface FileResult {
  file_path: string;
  relative_path?: string;
  language: string;
  lines_count: number;
  green_score: number;
  violations: Violation[];
  total_deductions: number;
}

export interface ScanResult {
  repo_path: string;
  repo_id?: number;
  total_files: number;
  total_lines: number;
  green_score: number;
  total_violations: number;
  violation_breakdown: Record<string, number>;
  languages_breakdown: Record<string, number>;
  violations: Violation[];
  file_results: FileResult[];
  energy_wh?: number;
  carbon_g?: number;
  is_github?: boolean;
}

export interface SarifReport {
  $schema: string;
  version: string;
  runs: Array<{
    tool: { driver: { name: string; version: string; rules: any[] } };
    results: any[];
  }>;
}

export interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  language?: string;
  description?: string;
  stargazers_count: number;
  updated_at: string;
}

export interface GitHubUser {
  login: string;
  id: number;
  avatar_url: string;
  html_url: string;
  name?: string;
  email?: string;
  bio?: string;
  public_repos: number;
  followers: number;
  following: number;
}

export interface ZoneData {
  zone: string;
  name: string;
  region: string;
  carbon_intensity: number;
  marginal_carbon_intensity: number;
  clean_energy_percentage: number;
  fossil_fuel_percentage: number;
  datacenter_hubs: string[];
  source: string;
  updated_at: string;
  is_live: boolean;
  time_of_day_info?: {
    local_hour: number;
    period: string;
    multiplier: number;
    recommendation: string;
  };
}

export interface GridZone {
  zone: string;
  name: string;
  region: string;
  carbon_intensity: number;
  clean_energy_percentage: number;
  fossil_fuel_percentage: number;
  datacenter_hubs: string[];
  source: string;
  utc_offset_hours: number;
  solar_peak_window: [number, number];
  solar_efficiency_factor: number;
  fossil_peak_window: [number, number];
  fossil_overhead_factor: number;
  baseline_factor: number;
  marginal_carbon_intensity: number;
  time_of_day_info: {
    local_hour: number;
    period: string;
    multiplier: number;
    solar_peak_window: number[];
    solar_efficiency_factor: number;
    fossil_peak_window: number[];
    fossil_overhead_factor: number;
    recommendation: string;
  };
}

export interface ProfilingResult {
  file_path: string;
  profiling_mode: string;
  duration_sec: number;
  avg_cpu_percent: number;
  peak_memory_mb: number;
  total_power_watts: number;
  energy_joules: number;
  energy_wh: number;
  energy_kwh: number;
  operational_carbon_gco2: number;
  embodied_carbon_gco2: number;
  sci_score_gco2: number;
  grid_intensity_gco2_per_kwh: number;
  exit_code: number;
  stdout_preview: string;
  stderr_preview: string;
}

export interface RefactorResult {
  original_code: string;
  refactored_code: string;
  violation_type: string;
  language?: string;
  energy_reduction_pct: number;
  carbon_saved_gco2_10k_runs: number;
  explanation: string;
  model_used: string;
}

export interface CIGateResult {
  passed: boolean;
  green_score: number;
  threshold: number;
  total_files: number;
  total_lines: number;
  total_violations: number;
  violation_breakdown: Record<string, number>;
  exit_code: number;
  message: string;
}

export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  avatar_url?: string;
  github_username?: string;
  role: string;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  access_token: string;
  token_type: string;
  user: User;
  email_dispatch?: { queued: boolean; mode: string };
}

export interface RepositoryRecord {
  id: number;
  name: string;
  path_or_url: string;
  total_files: number;
  total_lines: number;
  green_score: number;
  violations_data: Violation[];
  summary_json: string;
  created_at: string;
  user_id?: number;
}

export interface CumulativeSavings {
  total_carbon_saved_gco2_10k_runs: number;
  average_energy_reduction_pct: number;
  total_refactoring_operations: number;
}

export interface TaskStatus {
  status: string;
  result?: any;
  error?: string;
}

export const VIOLATION_RULE_MAP: Record<string, string> = {
  'NESTED_LOOPS_DEPTH_3+': 'GSF-E101',
  RAW_DB_CURSOR_NO_CONTEXT: 'GSF-R202',
  UNCACHED_NETWORK_IN_LOOP: 'GSF-N303',
  QUADRATIC_STRING_CONCAT_IN_LOOP: 'GSF-M404',
  HIDDEN_ITERATIVE_COMPUTATION: 'GSF-V505',
};

export const VIOLATION_LABEL_MAP: Record<ViolationType, string> = {
  'NESTED_LOOPS_DEPTH_3+': 'Deep Nested Iteration',
  'RAW_DB_CURSOR_NO_CONTEXT': 'Unmanaged Database Cursor',
  'UNCACHED_NETWORK_IN_LOOP': 'Un-cached Network Call In Loop',
  'QUADRATIC_STRING_CONCAT_IN_LOOP': 'Quadratic String Concatenation',
  'HIDDEN_ITERATIVE_COMPUTATION': 'Hidden Iterative Computation',
};

export const VIOLATION_SEVERITY_COLOR: Record<Severity, string> = {
  CRITICAL: '#dc2626',
  HIGH: '#d97706',
  MEDIUM: '#ca8a04',
  LOW: '#6b7280',
};
