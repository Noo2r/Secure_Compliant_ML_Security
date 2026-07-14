import { mockDelay } from "./api-client";
import type { DriftFeatureRow, HealthState } from "@/types/domain";

export interface DriftReport {
  overallStatus: HealthState;
  datasetDriftDetected: boolean;
  driftedFeatureCount: number;
  totalFeaturesChecked: number;
  usedSyntheticFallback: boolean;
  features: DriftFeatureRow[];
  trend: { run: string; driftedCount: number }[];
}

const FEATURES: DriftFeatureRow[] = [
  { feature: "TransactionAmt_log", psi: 0.04, status: "healthy", driftScore: 0.04 },
  { feature: "card1_amt_mean", psi: 0.06, status: "healthy", driftScore: 0.06 },
  { feature: "email_domain_match", psi: 0.02, status: "healthy", driftScore: 0.02 },
  { feature: "transaction_hour", psi: 0.11, status: "warning", driftScore: 0.11 },
  { feature: "card1_txn_count", psi: 0.03, status: "healthy", driftScore: 0.03 },
  { feature: "V201", psi: 0.05, status: "healthy", driftScore: 0.05 },
  { feature: "DeviceType", psi: 0.08, status: "healthy", driftScore: 0.08 },
  { feature: "card6", psi: 0.02, status: "healthy", driftScore: 0.02 },
];

const REPORT: DriftReport = {
  overallStatus: "healthy",
  datasetDriftDetected: false,
  driftedFeatureCount: FEATURES.filter((f) => f.status !== "healthy").length,
  totalFeaturesChecked: FEATURES.length,
  usedSyntheticFallback: true,
  features: FEATURES,
  trend: [
    { run: "Run -6", driftedCount: 0 },
    { run: "Run -5", driftedCount: 1 },
    { run: "Run -4", driftedCount: 0 },
    { run: "Run -3", driftedCount: 0 },
    { run: "Run -2", driftedCount: 2 },
    { run: "Run -1", driftedCount: 1 },
    { run: "Latest", driftedCount: 1 },
  ],
};

export async function getDriftReport(): Promise<DriftReport> {
  return mockDelay(REPORT, 300);
}
