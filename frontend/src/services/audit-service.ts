import { mockDelay } from "./api-client";
import type { AuditEvent } from "@/types/domain";

export const AUDIT_EVENTS: AuditEvent[] = [
  { id: "e1", timestamp: new Date(Date.now() - 2 * 3_600_000).toISOString(), action: "worm-upload --dry-run", actor: "GitHub Actions (mlops-pipeline.yml)", sha256: "3f7a1c...9b02e4", immutable: false },
  { id: "e2", timestamp: new Date(Date.now() - 26 * 3_600_000).toISOString(), action: "drift-monitor run", actor: "GitHub Actions (mlops-pipeline.yml)", sha256: "8d21e0...c4a17f", immutable: false },
  { id: "e3", timestamp: new Date(Date.now() - 50 * 3_600_000).toISOString(), action: "worm-upload --dry-run", actor: "GitHub Actions (mlops-pipeline.yml)", sha256: "1b9f66...7e03aa", immutable: false },
  { id: "e4", timestamp: new Date(Date.now() - 74 * 3_600_000).toISOString(), action: "fairness audit re-run", actor: "scripts/run_module5.py", sha256: "e5c802...2d19b6", immutable: false },
];

export const CANDIDATE_AUDIT_FILES = [
  { path: "reports_m5/fairness_summary.json", category: "Fairness" },
  { path: "reports_m5/drift_status.json", category: "Drift" },
  { path: "reports_m4/dp_report.md", category: "Differential Privacy" },
  { path: "reports/classification_report.json", category: "Data Security" },
];

export interface WormStatus {
  mode: "dry_run" | "live";
  filesListed: number;
  secretsConfigured: number;
  secretsRequired: number;
}

const WORM_STATUS: WormStatus = {
  mode: "dry_run",
  filesListed: CANDIDATE_AUDIT_FILES.length,
  secretsConfigured: 0,
  secretsRequired: 6,
};

export async function getAuditEvents(): Promise<AuditEvent[]> {
  return mockDelay(AUDIT_EVENTS, 300);
}

export async function getWormStatus(): Promise<WormStatus> {
  return mockDelay(WORM_STATUS, 300);
}
