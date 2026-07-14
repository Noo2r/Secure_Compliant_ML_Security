import { useQuery } from "@tanstack/react-query";
import { getDashboardSnapshot } from "@/services/dashboard-service";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard-snapshot"],
    queryFn: getDashboardSnapshot,
  });
}
