export interface Case {
  id: number;
  label: string;
  metadata_json: string;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRun {
  id: number;
  case_id: number;
  status: string;
  config_snapshot: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface StepRun {
  id: number;
  run_id: number;
  module: string;
  step_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Artifact {
  id: number;
  step_run_id: number;
  artifact_type: string;
  format: string;
  path: string;
  checksum: string | null;
  size_bytes: number | null;
  status: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  environment: string;
}

export interface ModuleStatus {
  name: string;
  enabled: boolean;
}
