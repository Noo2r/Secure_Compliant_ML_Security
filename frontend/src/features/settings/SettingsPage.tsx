import { useState } from "react";
import { Moon, Sun, Save, User, Server, ShieldCheck } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Section } from "@/components/shared/Section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { MetricRow } from "@/components/shared/MetricRow";
import { useAuth } from "@/hooks/use-auth";
import { useTheme } from "@/hooks/use-theme";

const API_URL_KEY = "secureml-api-url";

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem(API_URL_KEY) ?? import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000");
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem(API_URL_KEY, apiUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 1800);
  };

  return (
    <div>
      <PageHeader title="Settings" description="Preferences, profile, and API configuration" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section title="Profile" description="Current session">
          <div className="flex items-center gap-3">
            <div className="flex size-11 items-center justify-center rounded-full bg-primary/15 text-sm font-medium text-primary">
              {user?.username?.slice(0, 2).toUpperCase() ?? "ML"}
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{user?.username ?? "svc-ml-engineer"}</p>
              <p className="text-xs text-muted-foreground">Role: {user?.role ?? "ml_engineer"}</p>
            </div>
          </div>
          <div className="mt-4 space-y-1">
            <MetricRow label="Auth flow" value="OAuth2 password" />
            <MetricRow label="Token lifetime" value="15 minutes" />
          </div>
        </Section>

        <Section title="Appearance">
          <div className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
            <div className="flex items-center gap-3">
              {theme === "dark" ? <Moon className="size-4 text-primary" /> : <Sun className="size-4 text-warning" />}
              <div>
                <p className="text-sm font-medium text-foreground">Dark mode</p>
                <p className="text-xs text-muted-foreground">This platform is designed dark-first</p>
              </div>
            </div>
            <Switch checked={theme === "dark"} onCheckedChange={toggleTheme} />
          </div>
        </Section>

        <Section title="API Configuration" description="Base URL for the FastAPI backend">
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="api-url">Backend API URL</Label>
              <Input id="api-url" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} placeholder="http://127.0.0.1:8000" />
            </div>
            <Button size="sm" onClick={handleSave}>
              <Save className="size-3.5" />
              {saved ? "Saved" : "Save"}
            </Button>
            <p className="text-xs text-muted-foreground">
              Mock data is used by default (VITE_USE_MOCKS). Set it to false and restart the dev server to talk to a real
              locally-running backend.
            </p>
          </div>
        </Section>

        <Section title="Security Settings" description="Read-only — controlled server-side by app/main.py & app/core/*">
          <MetricRow label="Rate limit (default)" value="30/minute" />
          <MetricRow label="JWT algorithm" value="HS256" />
          <MetricRow label="CORS allow-list" value="explicit origins only" />
          <MetricRow label="CSP (API routes)" value="default-src 'none'" />
        </Section>
      </div>

      <div className="mt-6 flex gap-3 text-xs text-muted-foreground">
        <User className="size-3.5" />
        <span>Profile settings are local to this browser session.</span>
        <Server className="size-3.5" />
        <span>API URL changes require a page reload.</span>
        <ShieldCheck className="size-3.5" />
        <span>Security settings are enforced server-side.</span>
      </div>
    </div>
  );
}
