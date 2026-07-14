import { cn } from "@/lib/utils";
import { formatNumber } from "@/lib/format";
import type { CONFUSION_MATRIX_LIGHTGBM } from "@/data/real-facts";

export function ConfusionMatrixGrid({ matrix }: { matrix: typeof CONFUSION_MATRIX_LIGHTGBM }) {
  const cells = [
    { label: "True Negative", value: matrix.trueNegative, tone: "success" },
    { label: "False Positive", value: matrix.falsePositive, tone: "warning" },
    { label: "False Negative", value: matrix.falseNegative, tone: "warning" },
    { label: "True Positive", value: matrix.truePositive, tone: "success" },
  ] as const;

  return (
    <div>
      <div className="grid grid-cols-[auto_1fr_1fr] gap-1 text-center text-xs text-muted-foreground">
        <div />
        <div className="pb-1">Predicted: Not Fraud</div>
        <div className="pb-1">Predicted: Fraud</div>

        <div className="flex items-center justify-center pr-1 text-xs text-muted-foreground">True: Not Fraud</div>
        {cells.slice(0, 2).map((c) => (
          <MatrixCell key={c.label} {...c} />
        ))}

        <div className="flex items-center justify-center pr-1 text-xs text-muted-foreground">True: Fraud</div>
        {cells.slice(2, 4).map((c) => (
          <MatrixCell key={c.label} {...c} />
        ))}
      </div>
    </div>
  );
}

function MatrixCell({ label, value, tone }: { label: string; value: number; tone: "success" | "warning" }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-0.5 rounded-lg border p-4",
        tone === "success" ? "border-success/30 bg-success/10" : "border-warning/30 bg-warning/10",
      )}
    >
      <span className={cn("text-lg font-semibold", tone === "success" ? "text-success" : "text-warning")}>{formatNumber(value)}</span>
      <span className="text-[11px] text-muted-foreground">{label}</span>
    </div>
  );
}
