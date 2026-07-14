import { mockDelay } from "./api-client";
import { FAIRNESS_METRICS } from "@/data/real-facts";

export async function getFairnessMetrics() {
  return mockDelay(FAIRNESS_METRICS, 300);
}

export const BIAS_FINDINGS = [
  {
    id: "f1",
    title: "card6 (debit vs. credit) shows the strongest disparity",
    detail:
      "Credit-card transactions are flagged as fraud roughly 4x more often than debit (DIR=3.996), and the model catches real fraud among credit transactions about 19 percentage points more often (EOD=0.189). Both are statistically significant.",
    severity: "high" as const,
  },
  {
    id: "f2",
    title: "card4 = discover shows a significant selection-rate disparity",
    detail: "DIR=3.14 relative to visa, statistically significant, though the equal-opportunity gap (EOD) is not significant for this group.",
    severity: "medium" as const,
  },
  {
    id: "f3",
    title: "card4 = mastercard shows a significant opportunity gap without a selection-rate gap",
    detail: "DIR is not significant, but EOD (0.050) and AOD (0.026) are — the model's true-positive rate differs even though overall selection rates are similar.",
    severity: "medium" as const,
  },
  {
    id: "f4",
    title: "DeviceType (mobile vs. desktop) shows a consistent, significant disparity across all four metrics",
    detail: "Mobile transactions are flagged more often (DIR=1.254) but the model is less accurate at catching real fraud on mobile (EOD=-0.112).",
    severity: "medium" as const,
  },
  {
    id: "f5",
    title: "card4 = american express shows no statistically significant disparity",
    detail: "All four metrics' confidence intervals include the no-disparity value — the smallest group (n=1,126), so this may also reflect limited statistical power.",
    severity: "low" as const,
  },
];
