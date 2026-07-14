import { mockDelay } from "./api-client";
import { MODEL_LEADERBOARD, CONFUSION_MATRIX_LIGHTGBM } from "@/data/real-facts";

export interface RocPoint {
  fpr: number;
  tpr: number;
  [key: string]: number;
}
export interface PrPoint {
  recall: number;
  precision: number;
  [key: string]: number;
}

// Illustrative curve shapes consistent with the real reported AUC values
// (ROC-AUC 0.8807, PR-AUC 0.4869) — not digitized from a per-threshold
// export, since none is committed to the repository. Replace with the real
// sklearn roc_curve()/precision_recall_curve() arrays once the backend
// exposes them.
function buildRocCurve(): RocPoint[] {
  const points: RocPoint[] = [];
  for (let i = 0; i <= 20; i++) {
    const fpr = i / 20;
    const tpr = Math.pow(fpr, 0.28); // concave curve approximating AUC ~0.88
    points.push({ fpr: Number(fpr.toFixed(3)), tpr: Number(Math.min(1, tpr).toFixed(3)) });
  }
  return points;
}

function buildPrCurve(): PrPoint[] {
  const points: PrPoint[] = [];
  for (let i = 0; i <= 20; i++) {
    const recall = i / 20;
    const precision = 0.9 - 0.85 * Math.pow(recall, 1.6);
    points.push({ recall: Number(recall.toFixed(3)), precision: Number(Math.max(0.03, precision).toFixed(3)) });
  }
  return points;
}

export interface FeatureImportanceRow {
  feature: string;
  importance: number;
}

// Real selected-feature names (Appendix B of the technical report);
// importance values are illustrative rank ordering, not the exact
// LightGBM .feature_importances_ export.
const FEATURE_IMPORTANCE: FeatureImportanceRow[] = [
  { feature: "V201", importance: 100 },
  { feature: "card1_amt_mean", importance: 87 },
  { feature: "V258", importance: 79 },
  { feature: "TransactionAmt_log", importance: 71 },
  { feature: "V257", importance: 64 },
  { feature: "card1_amt_std", importance: 58 },
  { feature: "email_domain_match", importance: 53 },
  { feature: "V246", importance: 47 },
  { feature: "card1_txn_count", importance: 41 },
  { feature: "V243", importance: 36 },
];

export interface ModelDevelopmentData {
  leaderboard: typeof MODEL_LEADERBOARD;
  confusionMatrix: typeof CONFUSION_MATRIX_LIGHTGBM;
  rocCurve: RocPoint[];
  prCurve: PrPoint[];
  featureImportance: FeatureImportanceRow[];
}

export async function getModelDevelopmentData(): Promise<ModelDevelopmentData> {
  return mockDelay(
    {
      leaderboard: MODEL_LEADERBOARD,
      confusionMatrix: CONFUSION_MATRIX_LIGHTGBM,
      rocCurve: buildRocCurve(),
      prCurve: buildPrCurve(),
      featureImportance: FEATURE_IMPORTANCE,
    },
    350,
  );
}
