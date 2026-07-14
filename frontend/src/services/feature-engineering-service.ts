import { mockDelay } from "./api-client";
import { DATASET } from "@/data/real-facts";

export interface FeatureStage {
  stage: string;
  count: number;
  description: string;
}

export interface EngineeringTransformer {
  name: string;
  outputExample: string;
  description: string;
}

export interface FeatureEngineeringSummary {
  funnel: FeatureStage[];
  transformers: EngineeringTransformer[];
  categoryBreakdown: { name: string; value: number }[];
  pipelineSteps: string[];
}

const SUMMARY: FeatureEngineeringSummary = {
  funnel: [
    { stage: "Raw columns", count: DATASET.rawColumnCount, description: "Transaction + identity tables joined on TransactionID" },
    { stage: "Candidate features", count: DATASET.candidateFeatures, description: "After 6 engineering transformers applied" },
    { stage: "− Near-zero variance", count: DATASET.candidateFeatures - DATASET.droppedNearZeroVariance, description: `${DATASET.droppedNearZeroVariance} columns dropped (single value > 99.9% of rows)` },
    { stage: "− Correlation redundancy", count: DATASET.candidateFeatures - DATASET.droppedNearZeroVariance - DATASET.droppedCorrelationRedundancy, description: `${DATASET.droppedCorrelationRedundancy} columns dropped (|correlation| > 0.95)` },
    { stage: "Selected (final)", count: DATASET.selectedFeatures, description: `${DATASET.selectedNumeric} numeric + ${DATASET.selectedCategorical} categorical` },
  ],
  transformers: [
    { name: "TimeFeatureEngineer", outputExample: "transaction_hour, transaction_day_of_week", description: "Derives calendar features from the raw TransactionDT counter" },
    { name: "TransactionAmountFeatureEngineer", outputExample: "TransactionAmt_log, TransactionAmt_decimal", description: "Log-scale and decimal-part transforms of the transaction amount" },
    { name: "EmailDomainGrouper", outputExample: "email_domain_match", description: "Groups high-cardinality email domains; strongest single engineered signal in EDA (9.65% vs 2.21% fraud rate)" },
    { name: "CardVelocityFeatureEngineer", outputExample: "card1_txn_count, card1_amt_zscore", description: "Per-card transaction-count and amount statistics" },
    { name: "FrequencyEncoder", outputExample: "id_30, id_31, id_33, DeviceInfo", description: "Training-fold frequency encoding; unseen values encoded as 0 to avoid leakage" },
    { name: "MissingIndicatorEngineer", outputExample: "V-block missingness pattern flags", description: "Hashes each column's null-mask, grouping identical patterns into one indicator" },
  ],
  categoryBreakdown: [
    { name: "Numeric", value: DATASET.selectedNumeric },
    { name: "Categorical", value: DATASET.selectedCategorical },
  ],
  pipelineSteps: ["Raw Data", "Cleaning", "Encoding", "Engineering", "Selection", "Final Dataset"],
};

export async function getFeatureEngineeringSummary(): Promise<FeatureEngineeringSummary> {
  return mockDelay(SUMMARY, 300);
}
