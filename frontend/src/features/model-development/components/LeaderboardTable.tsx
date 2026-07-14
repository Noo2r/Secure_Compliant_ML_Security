import { Trophy } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { formatDecimal } from "@/lib/format";
import type { MODEL_LEADERBOARD } from "@/data/real-facts";

export function LeaderboardTable({ models }: { models: typeof MODEL_LEADERBOARD }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Model</TableHead>
            <TableHead className="text-right">PR-AUC</TableHead>
            <TableHead className="text-right">ROC-AUC</TableHead>
            <TableHead className="text-right">Precision</TableHead>
            <TableHead className="text-right">Recall</TableHead>
            <TableHead className="text-right">F1</TableHead>
            <TableHead className="text-right">Accuracy</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {models
            .slice()
            .sort((a, b) => b.holdoutPrAuc - a.holdoutPrAuc)
            .map((m) => (
              <TableRow key={m.id} className={cn(m.isWinner && "bg-primary/5")}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    {m.isWinner && <Trophy className="size-3.5 text-warning" />}
                    {m.name}
                    {m.isWinner && (
                      <Badge className="bg-primary/15 text-primary hover:bg-primary/15" variant="secondary">
                        Selected
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono">{formatDecimal(m.holdoutPrAuc, 4)}</TableCell>
                <TableCell className="text-right font-mono">{formatDecimal(m.holdoutRocAuc, 4)}</TableCell>
                <TableCell className="text-right font-mono">{formatDecimal(m.holdoutPrecision, 4)}</TableCell>
                <TableCell className="text-right font-mono">{formatDecimal(m.holdoutRecall, 4)}</TableCell>
                <TableCell className="text-right font-mono">{formatDecimal(m.holdoutF1, 4)}</TableCell>
                <TableCell className="text-right font-mono">{formatDecimal(m.holdoutAccuracy, 4)}</TableCell>
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </div>
  );
}
