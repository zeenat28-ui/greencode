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
  /** Repository slug as `owner/repo` in GitHub-only mode. */
  repo_path: string;
  repo_id?: number;
  full_name?: string;
  ref?: string;
  default_branch?: string;
  html_url?: string;
  language?: string;
  source?: 'github';
  is_github?: boolean;
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
}

export interface GitHubRepo {
  full_name: string;
  name: string;
  owner: string;
  default_branch: string;
  language: string;
  description: string;
  size_kb: number;
  private: boolean;
  fork: boolean;
  archived: boolean;
  stars: number;
  forks: number;
  open_issues: number;
  updated_at: string;
  url: string;
}

export interface GitHubBranch {
  name: string;
  sha: string;
}

export interface RepoPreflight {
  can_audit: boolean;
  message: string;
  language: string;
  size_kb: number;
  default_branch: string;
  archived: boolean;
  full_name: string;
  html_url: string;
}

export interface BenchmarkScript {
  id: string;
  label: string;
  description: string;
}

/** OASIS SARIF v2.1.0 - results live under `runs[0]`, per the spec. */
export interface SarifReport {
  $schema: string;
  version: string;
  runs: Array<{
    tool: { driver: { name: string; version: string; rules: any[] } };
    results: any[];
    properties?: {
      green_score?: number;
      total_files?: number;
      total_violations?: number;
    };
  }>;
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
  /** Always null in API responses - the raw PAT is never sent to the client. */
  github_token?: string | null;
  has_github_token?: boolean;
  github_token_masked?: string | null;
  role: string;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
  user: User;
  github_login?: string;
}

export interface RepositoryRecord {
  id: number;
  name: string;
  /** `owner/repo` for GitHub audits. */
  path_or_url: string;
  full_name: string | null;
  default_branch: string | null;
  html_url: string | null;
  source: string;
  total_files: number;
  total_lines: number;
  green_score: number;
  created_at: string | null;
  user_id?: number | null;
}

export interface CumulativeSavings {
  total_carbon_saved_gco2_10k_runs: number;
  average_energy_reduction_pct: number;
  total_refactoring_operations: number;
}

export interface RepositoryPage {
  repositories: RepositoryRecord[];
  cumulative_savings: CumulativeSavings;
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface TaskStatus {
  task_id: string;
  status: 'Processing' | 'Completed' | 'Failed' | 'NotFound' | string;
  is_done?: boolean;
  queue_backend?: string;
  result?: ScanResult | null;
  error?: string | null;
  progress_message?: string | null;
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

// ---------------------------------------------------------------------------
// Dynamic analysis
// ---------------------------------------------------------------------------

/**
 * How the energy figure was obtained.
 *
 * `rapl` / `perf` / `battery` are real hardware measurements. `model` is a
 * calibrated TDP estimate, which is meaningfully less trustworthy and must never
 * be presented as if it were measured.
 */
export type MeasurementMethod = 'rapl' | 'perf' | 'battery' | 'model';

export interface EnergyMeasurementCapabilities {
  /** Which backends this host can actually reach right now. */
  best_available: MeasurementMethod;
  rapl: { supported: boolean; domains: Array<{ name: string; kind: string; max_range_uj: number }> };
  perf: { supported: boolean };
  battery: { supported: boolean; watts: number | null };
  /** Always true: a TDP model is always available as a last resort. */
  modelled_fallback: boolean;
}

export interface DynamicAnalysisStatus {
  dynamic_analysis_available: boolean;
  /** Human-readable reasons the feature is off, e.g. Docker missing. */
  blockers: string[];
  docker: { sdk_installed: boolean; reachable: boolean; error: string | null };
  energy_measurement: EnergyMeasurementCapabilities;
  hardware_measurement_available: boolean;
}

export interface SCIResult {
  energy_kwh: number;
  carbon_intensity_gco2_per_kwh: number;
  /** R in the SCI formula. 1 means this is a total, not an intensity. */
  functional_unit: number;
  operational_gco2: number;
  embodied_gco2: number;
  sci_gco2_per_functional_unit: number;
  pue: number;
  measurement_method: MeasurementMethod;
  /** False for modelled figures - the UI must label these distinctly. */
  measurement_is_hardware: boolean;
  it_energy_joules: number;
  cpu_joules: number;
  memory_joules: number;
  energy_joules: number;
  duration_seconds: number;
  /** Caveats a reader must see next to the numbers. */
  warnings: string[];
}

export interface CarbonEquivalents {
  smartphone_charges: number;
  km_driven_petrol_car: number;
  hours_watching_1080p_video: number;
  tree_years_absorbed: number;
  meals_vegetarian: number;
}

export interface DynamicAnalysisResult {
  ok: boolean;
  /** 'ok' | 'sandbox_unavailable' | 'no_entry_point' | 'timeout' | 'nonzero_exit' | ... */
  reason: string;
  repo_slug: string;
  ref: string;
  entry_point: string;
  language: string;
  /** e.g. 'docker-isolated' or 'none'. */
  sandbox: string;
  measurement_method: MeasurementMethod;
  measurement_is_hardware: boolean;
  exit_code: number;
  duration_seconds: number;
  peak_memory_mb: number;
  it_energy_joules: number;
  cpu_joules: number;
  memory_joules: number;
  sci: SCIResult;
  grade: { grade: string; label: string; equivalent: string };
  equivalents: CarbonEquivalents;
  stdout_tail: string;
  stderr_tail: string;
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Audit intelligence
// ---------------------------------------------------------------------------

export interface ViolationTheme {
  theme: string;
  count: number;
  rules: string[];
  weighted_impact: number;
}

export interface RemediationStep {
  violation_type: string;
  theme: string;
  occurrences: number;
  file_count: number;
  files: string[];
  action: string;
  effort: 'low' | 'medium' | 'high';
  /** How likely the change is to alter behaviour. */
  risk: 'low' | 'medium' | 'high';
  priority_score: number;
  sample_lines: Array<{ file: string; line: number | null; snippet: string }>;
}

export interface AuditContext {
  context: {
    repository: string;
    total_files: number;
    total_lines: number;
    green_score: number;
    total_violations: number;
    files_with_violations: number;
    violation_themes: ViolationTheme[];
    concentration: { pct_files_affected: number; pct_lines_affected: number };
  };
  plan: {
    steps: RemediationStep[];
    step_count: number;
    total_occurrences: number;
    quick_wins: number;
    quick_win_occurrences: number;
    estimated_effort: { engineer_days: number; band: string };
  };
  breakdown: Record<string, number>;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  timestamp: string;
  service: string;
  version: string;
  deps: Record<string, string>;
  capabilities: {
    dynamic_analysis: boolean;
    dynamic_analysis_blockers: string[];
    hardware_energy_measurement: boolean;
    llm_refactoring: boolean;
  };
}
