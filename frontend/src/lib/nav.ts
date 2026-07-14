import {
  LayoutDashboard,
  ShieldCheck,
  Wand2,
  Boxes,
  Lock,
  Scale,
  Webhook,
  Swords,
  FileCheck2,
  Activity,
  Archive,
  FlaskConical,
  Server,
  GitBranch,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  group: string;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard, group: "Overview", description: "System-wide health and metrics" },
  { label: "Data Validation", path: "/data-validation", icon: ShieldCheck, group: "ML Pipeline", description: "Module 1 — data contract checks" },
  { label: "Feature Engineering", path: "/feature-engineering", icon: Wand2, group: "ML Pipeline", description: "Module 2 — engineering & selection" },
  { label: "Model Development", path: "/model-development", icon: Boxes, group: "ML Pipeline", description: "Module 3 — training & leaderboard" },
  { label: "Differential Privacy", path: "/differential-privacy", icon: Lock, group: "ML Pipeline", description: "Module 4 — DP-SGD privacy budget" },
  { label: "Fairness Analysis", path: "/fairness", icon: Scale, group: "ML Pipeline", description: "Module 5 — bias & fairness metrics" },
  { label: "Inference API", path: "/inference-api", icon: Webhook, group: "Deployment", description: "Secure FastAPI prediction service" },
  { label: "Threat Model", path: "/threat-model", icon: Swords, group: "Deployment", description: "STRIDE analysis & trust boundaries" },
  { label: "Compliance", path: "/compliance", icon: FileCheck2, group: "Governance", description: "GDPR / HIPAA / ISO 27001 mapping" },
  { label: "Drift Monitoring", path: "/drift-monitoring", icon: Activity, group: "MLOps", description: "Evidently-based data drift" },
  { label: "Audit Storage", path: "/audit-storage", icon: Archive, group: "Governance", description: "WORM immutable audit trail" },
  { label: "MLflow", path: "/mlflow", icon: FlaskConical, group: "MLOps", description: "Experiment tracking & registry" },
  { label: "Deployment", path: "/deployment", icon: Server, group: "Deployment", description: "Azure IaC target architecture" },
  { label: "CI/CD", path: "/cicd", icon: GitBranch, group: "MLOps", description: "GitHub Actions pipeline" },
  { label: "Settings", path: "/settings", icon: Settings, group: "System", description: "Preferences & configuration" },
];

export const NAV_GROUPS = ["Overview", "ML Pipeline", "Deployment", "Governance", "MLOps", "System"] as const;
