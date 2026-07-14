import { mockDelay } from "./api-client";
import { TEST_SUITE } from "@/data/real-facts";
import type { CiRun } from "@/types/domain";

const RUNS: CiRun[] = [
  {
    id: "482",
    branch: "main",
    commitSha: "a1f9c3d",
    commitMessage: "Fix WORM upload path resolution for CI checkout",
    triggeredBy: "push",
    status: "success",
    startedAt: new Date(Date.now() - 13 * 60_000).toISOString(),
    stages: [
      { id: "s1", name: "Install dependencies", status: "success", durationSec: 42, detail: "requirements-milestone2/3/5.txt" },
      { id: "s2", name: "Run test suite", status: "success", durationSec: 118, detail: `${TEST_SUITE.totalTests}/${TEST_SUITE.totalTests} tests passed` },
      { id: "s3", name: "drift-monitor job", status: "success", durationSec: 34, detail: "Synthetic-data fallback (data/ gitignored)" },
      { id: "s4", name: "alert-on-drift job", status: "skipped", durationSec: 0, detail: "No drift detected — job skipped" },
      { id: "s5", name: "worm-upload job", status: "success", durationSec: 8, detail: "--dry-run fallback (no Azure secrets configured)" },
    ],
  },
  {
    id: "481",
    branch: "main",
    commitSha: "7e2b810",
    commitMessage: "Add tests for drift_monitor + worm_storage pure functions",
    triggeredBy: "push",
    status: "success",
    startedAt: new Date(Date.now() - 26 * 3_600_000).toISOString(),
    stages: [
      { id: "s1", name: "Install dependencies", status: "success", durationSec: 45, detail: "requirements-milestone2/3/5.txt" },
      { id: "s2", name: "Run test suite", status: "success", durationSec: 121, detail: `${TEST_SUITE.totalTests}/${TEST_SUITE.totalTests} tests passed` },
      { id: "s3", name: "drift-monitor job", status: "success", durationSec: 31, detail: "Synthetic-data fallback" },
      { id: "s4", name: "alert-on-drift job", status: "skipped", durationSec: 0, detail: "No drift detected" },
      { id: "s5", name: "worm-upload job", status: "success", durationSec: 9, detail: "--dry-run fallback" },
    ],
  },
  {
    id: "480",
    branch: "feature/milestone5-mlops",
    commitSha: "c48af02",
    commitMessage: "Copy drift_monitor.py + worm_storage.py with path fixes",
    triggeredBy: "pull_request",
    status: "failed",
    startedAt: new Date(Date.now() - 50 * 3_600_000).toISOString(),
    stages: [
      { id: "s1", name: "Install dependencies", status: "success", durationSec: 44, detail: "requirements-milestone2/3/5.txt" },
      { id: "s2", name: "Run test suite", status: "success", durationSec: 119, detail: `${TEST_SUITE.totalTests}/${TEST_SUITE.totalTests} tests passed` },
      { id: "s3", name: "drift-monitor job", status: "failed", durationSec: 6, detail: "unrecognized arguments: --features (fixed in #482)" },
      { id: "s4", name: "alert-on-drift job", status: "skipped", durationSec: 0, detail: "Upstream job failed" },
      { id: "s5", name: "worm-upload job", status: "skipped", durationSec: 0, detail: "Upstream job failed" },
    ],
  },
];

export async function getCiRuns(): Promise<CiRun[]> {
  return mockDelay(RUNS, 300);
}
