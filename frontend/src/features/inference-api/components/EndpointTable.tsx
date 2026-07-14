import { Lock, Unlock } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import type { ApiEndpointRow } from "@/services/inference-service";

export function EndpointTable({ endpoints }: { endpoints: ApiEndpointRow[] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Endpoint</TableHead>
            <TableHead>Auth</TableHead>
            <TableHead>Input</TableHead>
            <TableHead>Output</TableHead>
            <TableHead>Security controls</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {endpoints.map((e) => (
            <TableRow key={e.route}>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {e.method}
                  </Badge>
                  <span className="font-mono text-xs">{e.route}</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{e.purpose}</p>
              </TableCell>
              <TableCell>
                {e.auth ? (
                  <Lock className="size-3.5 text-warning" />
                ) : (
                  <Unlock className="size-3.5 text-muted-foreground" />
                )}
              </TableCell>
              <TableCell className="max-w-52 font-mono text-xs text-muted-foreground">{e.input}</TableCell>
              <TableCell className="max-w-52 font-mono text-xs text-muted-foreground">{e.output}</TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {e.security.map((s) => (
                    <Badge key={s} variant="secondary" className="text-[10px]">
                      {s}
                    </Badge>
                  ))}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
