import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { MetricRow, MetricGrid } from "@/components/shared/MetricRow";
import { VerificationBadge } from "@/components/shared/StatusBadge";
import { API_ENDPOINTS } from "@/services/inference-service";
import { EndpointTable } from "./components/EndpointTable";
import { LiveDemoPanel } from "./components/LiveDemoPanel";

export default function InferenceApiPage() {
  return (
    <div>
      <PageHeader
        title="Inference API"
        description="Secure FastAPI service (Milestone 3) — JWT-authenticated, rate-limited fraud-risk scoring"
        badge={<VerificationBadge status="locally_tested" />}
      />

      <div className="space-y-6">
        <Section title="Endpoints" noPadding>
          <EndpointTable endpoints={API_ENDPOINTS} />
        </Section>

        <LiveDemoPanel />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Section title="Security Headers" description="Applied to every response by security_headers_middleware">
            <MetricRow label="Strict-Transport-Security" value="max-age=63072000" />
            <MetricRow label="X-Content-Type-Options" value="nosniff" />
            <MetricRow label="X-Frame-Options" value="DENY" />
            <MetricRow label="Content-Security-Policy" value="default-src 'none'" hint="relaxed only for /docs, /redoc, /static" />
            <MetricRow label="Referrer-Policy" value="no-referrer" />
          </Section>

          <Section title="Rate Limiting & Auth" description="SlowAPI global limiter + OAuth2 password flow">
            <MetricGrid cols={2}>
              <MetricRow label="Default rate limit" value="30/minute" />
              <MetricRow label="Auth endpoint" value="stricter limit" />
              <MetricRow label="Token lifetime" value="15 minutes" />
              <MetricRow label="Algorithm" value="HS256" />
            </MetricGrid>
            <p className="mt-3 text-xs text-muted-foreground">
              Locally tested end-to-end with the real trained LightGBM bundle — never deployed to a live, externally-reachable
              server.
            </p>
          </Section>
        </div>
      </div>
    </div>
  );
}
