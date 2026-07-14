import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { formatDecimal, formatNumber } from "@/lib/format";
import type { FAIRNESS_METRICS } from "@/data/real-facts";

function ciCell(value: number, ci: [number, number], significant: boolean) {
  return (
    <div className="flex flex-col items-end">
      <span className={significant ? "font-medium text-warning" : "text-foreground"}>{formatDecimal(value, 4)}</span>
      <span className="text-[10px] text-muted-foreground">
        [{formatDecimal(ci[0], 3)}, {formatDecimal(ci[1], 3)}]
      </span>
    </div>
  );
}

export function FairnessTable({ metrics }: { metrics: typeof FAIRNESS_METRICS }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Attribute</TableHead>
            <TableHead>Group vs. reference</TableHead>
            <TableHead className="text-right">n (group / ref)</TableHead>
            <TableHead className="text-right">SPD</TableHead>
            <TableHead className="text-right">DIR</TableHead>
            <TableHead className="text-right">EOD</TableHead>
            <TableHead className="text-right">AOD</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metrics.map((m) => (
            <TableRow key={`${m.attribute}-${m.group}`}>
              <TableCell className="font-mono text-xs">{m.attribute}</TableCell>
              <TableCell>
                <span className="font-medium">{m.group}</span>
                <span className="text-muted-foreground"> vs {m.referenceGroup}</span>
                {(m.dirSignificant || m.eodSignificant || m.spdSignificant) && (
                  <Badge variant="outline" className="ml-2 border-warning/30 bg-warning/10 text-[10px] text-warning">
                    significant
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right font-mono text-xs text-muted-foreground">
                {formatNumber(m.nGroup)} / {formatNumber(m.nReference)}
              </TableCell>
              <TableCell className="text-right font-mono text-xs">{ciCell(m.spd, m.spdCi, m.spdSignificant)}</TableCell>
              <TableCell className="text-right font-mono text-xs">{ciCell(m.dir, m.dirCi, m.dirSignificant)}</TableCell>
              <TableCell className="text-right font-mono text-xs">{ciCell(m.eod, m.eodCi, m.eodSignificant)}</TableCell>
              <TableCell className="text-right font-mono text-xs">{ciCell(m.aod, m.aodCi, m.aodSignificant)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
