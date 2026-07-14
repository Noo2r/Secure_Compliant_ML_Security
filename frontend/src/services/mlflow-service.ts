import { mockDelay } from "./api-client";
import { MODEL_LEADERBOARD, DATASET } from "@/data/real-facts";
import type { MlflowRun } from "@/types/domain";

const RUNS: MlflowRun[] = MODEL_LEADERBOARD.map((m, i) => ({
  id: `run-${(i + 1).toString().padStart(3, "0")}`,
  runName: `module3_${m.id}_tuning`,
  model: m.name,
  status: "FINISHED",
  prAuc: m.holdoutPrAuc,
  rocAuc: m.holdoutRocAuc,
  startedAt: new Date(Date.now() - (i + 1) * 6 * 3_600_000).toISOString(),
  durationSec: 180 + i * 47,
}));

export interface RegistryEntry {
  name: string;
  version: number;
  stage: "None" | "Staging" | "Production";
  artifactPath: string;
}

const REGISTRY: RegistryEntry[] = [
  { name: "fraud-lightgbm", version: 3, stage: "None", artifactPath: `artifacts_m3/lightgbm_inference_bundle.joblib` },
  { name: "fraud-xgboost", version: 2, stage: "None", artifactPath: "artifacts_m3/xgboost_inference_bundle.joblib" },
  { name: "fraud-random-forest", version: 1, stage: "None", artifactPath: "artifacts_m3/random_forest_inference_bundle.joblib" },
  { name: "fraud-nn-dp", version: 1, stage: "None", artifactPath: "artifacts_m4/dp_model.joblib" },
];

export async function getMlflowRuns(): Promise<MlflowRun[]> {
  return mockDelay(RUNS, 300);
}

export async function getRegistry(): Promise<RegistryEntry[]> {
  return mockDelay(REGISTRY, 300);
}

export const MLFLOW_NOTE = `Local MLflow tracking store (mlruns/, gitignored, machine-local) — dataset version ${DATASET.datasetVersion}. No stage transitions to "Production" have been made; this reflects local experiment tracking, not a deployed model registry.`;
