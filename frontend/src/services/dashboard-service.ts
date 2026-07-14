import { mockDelay } from "./api-client";
import { DATASET, MODEL_LEADERBOARD, DIFFERENTIAL_PRIVACY, FAIRNESS_METRICS, TEST_SUITE, COMPLIANCE_SUMMARY } from "@/data/real-facts";
import type { ActivityItem, HealthState } from "@/types/domain";

export interface DashboardSnapshot {
  systemStatus: HealthState;
  pipelineStatus: HealthState;
  apiStatus: HealthState;
  containerStatus: HealthState;
  driftStatus: HealthState;
  latestModel: string;
  modelVersion: string;
  prAuc: number;
  rocAuc: number;
  featureCount: number;
  fraudRate: number;
  privacyEpsilon: number;
  fairnessFindingsCount: number;
  significantFairnessFindings: number;
  complianceScorePct: number;
  testsPassing: string;
  timeline: { label: string; status: HealthState; detail: string }[];
  activity: ActivityItem[];
}

const WINNER = MODEL_LEADERBOARD.find((m) => m.isWinner)!;
const significantFindings = FAIRNESS_METRICS.filter((f) => f.dirSignificant || f.eodSignificant || f.spdSignificant).length;
const complianceTotal =
  COMPLIANCE_SUMMARY.gdpr.implemented +
  COMPLIANCE_SUMMARY.gdpr.partial +
  COMPLIANCE_SUMMARY.gdpr.notImplemented +
  COMPLIANCE_SUMMARY.iso27001.implemented +
  COMPLIANCE_SUMMARY.iso27001.partial +
  COMPLIANCE_SUMMARY.iso27001.notImplemented;
const complianceImplemented = COMPLIANCE_SUMMARY.gdpr.implemented + COMPLIANCE_SUMMARY.iso27001.implemented;

const SNAPSHOT: DashboardSnapshot = {
  systemStatus: "healthy",
  pipelineStatus: "healthy",
  apiStatus: "healthy",
  containerStatus: "healthy",
  driftStatus: "healthy",
  latestModel: WINNER.name,
  modelVersion: `lightgbm@${DATASET.datasetVersion}`,
  prAuc: WINNER.holdoutPrAuc,
  rocAuc: WINNER.holdoutRocAuc,
  featureCount: DATASET.selectedFeatures,
  fraudRate: DATASET.fraudRate,
  privacyEpsilon: DIFFERENTIAL_PRIVACY.epsilon,
  fairnessFindingsCount: FAIRNESS_METRICS.length,
  significantFairnessFindings: significantFindings,
  complianceScorePct: Math.round((complianceImplemented / complianceTotal) * 100),
  testsPassing: `${TEST_SUITE.totalTests}/${TEST_SUITE.totalTests}`,
  timeline: [
    { label: "Data Validation", status: "healthy", detail: "9/9 checks passed" },
    { label: "Feature Engineering", status: "healthy", detail: "466 → 150 features" },
    { label: "Model Training", status: "healthy", detail: "LightGBM selected" },
    { label: "Differential Privacy", status: "warning", detail: "ε=45.57, utility loss observed" },
    { label: "Fairness Audit", status: "warning", detail: `${significantFindings} significant findings` },
    { label: "Secure Deployment", status: "healthy", detail: "Locally tested" },
    { label: "Compliance QA", status: "warning", detail: "3 documentation gaps found" },
    { label: "MLOps / CI-CD", status: "healthy", detail: "178/178 tests passing" },
  ],
  activity: [
    { id: "a1", title: "CI/CD pipeline run #482 passed", description: "main branch — 178/178 tests, drift-monitor job completed", timestamp: new Date(Date.now() - 12 * 60_000).toISOString(), status: "healthy", module: "CI/CD" },
    { id: "a2", title: "Drift check completed", description: "No significant feature drift in latest reference/current comparison", timestamp: new Date(Date.now() - 55 * 60_000).toISOString(), status: "healthy", module: "Drift Monitoring" },
    { id: "a3", title: "WORM dry-run executed", description: "worm_storage.py --dry-run listed 3 audit files, no live upload", timestamp: new Date(Date.now() - 3 * 3_600_000).toISOString(), status: "warning", module: "Audit Storage" },
    { id: "a4", title: "Fairness audit re-run", description: "card6 DIR=3.996 flagged as statistically significant", timestamp: new Date(Date.now() - 8 * 3_600_000).toISOString(), status: "warning", module: "Fairness" },
    { id: "a5", title: "Inference API health check", description: "GET /health returned 200 — environment: development", timestamp: new Date(Date.now() - 20 * 3_600_000).toISOString(), status: "healthy", module: "Inference API" },
  ],
};

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  return mockDelay(SNAPSHOT, 300);
}
