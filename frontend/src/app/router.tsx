import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { PageLoader } from "@/components/shared/PageLoader";
import { RouteErrorBoundary } from "@/components/layout/RouteErrorBoundary";
import LoginPage from "@/features/auth/LoginPage";
import DashboardPage from "@/features/dashboard/DashboardPage";

const DataValidationPage = lazy(() => import("@/features/data-validation/DataValidationPage"));
const FeatureEngineeringPage = lazy(() => import("@/features/feature-engineering/FeatureEngineeringPage"));
const ModelDevelopmentPage = lazy(() => import("@/features/model-development/ModelDevelopmentPage"));
const DifferentialPrivacyPage = lazy(() => import("@/features/differential-privacy/DifferentialPrivacyPage"));
const FairnessPage = lazy(() => import("@/features/fairness/FairnessPage"));
const InferenceApiPage = lazy(() => import("@/features/inference-api/InferenceApiPage"));
const ThreatModelPage = lazy(() => import("@/features/threat-model/ThreatModelPage"));
const CompliancePage = lazy(() => import("@/features/compliance/CompliancePage"));
const DriftMonitoringPage = lazy(() => import("@/features/drift-monitoring/DriftMonitoringPage"));
const AuditStoragePage = lazy(() => import("@/features/audit-storage/AuditStoragePage"));
const MlflowPage = lazy(() => import("@/features/mlflow/MlflowPage"));
const DeploymentPage = lazy(() => import("@/features/deployment/DeploymentPage"));
const CicdPage = lazy(() => import("@/features/cicd/CicdPage"));
const SettingsPage = lazy(() => import("@/features/settings/SettingsPage"));
const NotFoundPage = lazy(() => import("@/features/shared/NotFoundPage"));

function withSuspense(node: React.ReactNode) {
  return <Suspense fallback={<PageLoader />}>{node}</Suspense>;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage />, errorElement: <RouteErrorBoundary /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorBoundary />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "data-validation", element: withSuspense(<DataValidationPage />) },
      { path: "feature-engineering", element: withSuspense(<FeatureEngineeringPage />) },
      { path: "model-development", element: withSuspense(<ModelDevelopmentPage />) },
      { path: "differential-privacy", element: withSuspense(<DifferentialPrivacyPage />) },
      { path: "fairness", element: withSuspense(<FairnessPage />) },
      { path: "inference-api", element: withSuspense(<InferenceApiPage />) },
      { path: "threat-model", element: withSuspense(<ThreatModelPage />) },
      { path: "compliance", element: withSuspense(<CompliancePage />) },
      { path: "drift-monitoring", element: withSuspense(<DriftMonitoringPage />) },
      { path: "audit-storage", element: withSuspense(<AuditStoragePage />) },
      { path: "mlflow", element: withSuspense(<MlflowPage />) },
      { path: "deployment", element: withSuspense(<DeploymentPage />) },
      { path: "cicd", element: withSuspense(<CicdPage />) },
      { path: "settings", element: withSuspense(<SettingsPage />) },
      { path: "*", element: withSuspense(<NotFoundPage />) },
    ],
  },
]);
