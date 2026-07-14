import { mockDelay } from "./api-client";
import { DATASET, VALIDATION_CHECKS } from "@/data/real-facts";
import type { ValidationCheck } from "@/types/domain";

export interface ValidationReport {
  datasetVersion: string;
  rowCount: number;
  rawColumnCount: number;
  checks: ValidationCheck[];
  criticalPassed: number;
  criticalTotal: number;
  warningPassed: number;
  warningTotal: number;
}

const checks: ValidationCheck[] = VALIDATION_CHECKS.map((c) => ({
  ...c,
  status: "pass",
}));

const REPORT: ValidationReport = {
  datasetVersion: DATASET.datasetVersion,
  rowCount: DATASET.rowCount,
  rawColumnCount: DATASET.rawColumnCount,
  checks,
  criticalPassed: checks.filter((c) => c.severity === "critical" && c.status === "pass").length,
  criticalTotal: checks.filter((c) => c.severity === "critical").length,
  warningPassed: checks.filter((c) => c.severity === "warning" && c.status === "pass").length,
  warningTotal: checks.filter((c) => c.severity === "warning").length,
};

export async function getValidationReport(): Promise<ValidationReport> {
  return mockDelay(REPORT, 300);
}
