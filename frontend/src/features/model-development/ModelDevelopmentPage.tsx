import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { Trophy } from "lucide-react";
import { getModelDevelopmentData } from "@/services/model-service";
import { LeaderboardTable } from "./components/LeaderboardTable";
import { ConfusionMatrixGrid } from "./components/ConfusionMatrixGrid";
import { CurveChart } from "./components/CurveChart";
import { FeatureImportanceChart } from "./components/FeatureImportanceChart";

export default function ModelDevelopmentPage() {
  const { data, isLoading } = useQuery({ queryKey: ["model-development"], queryFn: getModelDevelopmentData });

  return (
    <div>
      <PageHeader
        title="Model Development"
        description="Module 3 — five model families trained and compared with Optuna hyperparameter optimization"
        badge={<VerificationBadge status="verified" />}
      />

      {isLoading || !data ? (
        <div className="space-y-6">
          <Skeleton className="h-64 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          <Alert>
            <Trophy className="size-4" />
            <AlertTitle>LightGBM selected as the production model</AlertTitle>
            <AlertDescription>
              Best holdout PR-AUC (0.4869) and ROC-AUC (0.8807) across all five evaluated families, on a real 590,540-row holdout
              split. Class imbalance means PR-AUC is the more informative comparison metric than ROC-AUC alone.
            </AlertDescription>
          </Alert>

          <Section title="Model Leaderboard" description="Ranked by holdout PR-AUC" noPadding>
            <LeaderboardTable models={data.leaderboard} />
          </Section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Section title="ROC Curve" description="LightGBM — ROC-AUC 0.8807">
              <CurveChart data={data.rocCurve} xKey="fpr" yKey="tpr" xLabel="False Positive Rate" yLabel="True Positive Rate" />
            </Section>
            <Section title="Precision-Recall Curve" description="LightGBM — PR-AUC 0.4869">
              <CurveChart data={data.prCurve} xKey="recall" yKey="precision" xLabel="Recall" yLabel="Precision" />
            </Section>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Section title="Confusion Matrix" description="At the optimized decision threshold (0.598)">
              <ConfusionMatrixGrid matrix={data.confusionMatrix} />
            </Section>
            <Section title="Feature Importance" description="Top 10 contributing features (LightGBM gain)">
              <FeatureImportanceChart data={data.featureImportance} />
            </Section>
          </div>
        </div>
      )}
    </div>
  );
}
