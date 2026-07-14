import { useState } from "react";
import { KeyRound, Send, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { JsonBlock } from "@/components/shared/JsonBlock";
import { Section } from "@/components/shared/Section";
import { requestToken, requestPrediction, SAMPLE_REQUEST } from "@/services/inference-service";
import type { PredictionResponsePreview } from "@/types/domain";

export function LiveDemoPanel() {
  const [token, setToken] = useState<string | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);

  const [response, setResponse] = useState<PredictionResponsePreview | null>(null);
  const [predictLoading, setPredictLoading] = useState(false);
  const [predictError, setPredictError] = useState<string | null>(null);

  const handleGetToken = async () => {
    setTokenLoading(true);
    setTokenError(null);
    try {
      const t = await requestToken("svc-ml-engineer", "CHANGE_ME_IN_PRODUCTION");
      setToken(t);
    } catch (err) {
      setTokenError(err instanceof Error ? err.message : "Failed to get token");
    } finally {
      setTokenLoading(false);
    }
  };

  const handlePredict = async () => {
    setPredictLoading(true);
    setPredictError(null);
    setResponse(null);
    try {
      const res = await requestPrediction(token ?? "", SAMPLE_REQUEST);
      setResponse(res);
    } catch (err) {
      setPredictError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setPredictLoading(false);
    }
  };

  return (
    <Section title="Live Demo" description="Exercises the real OAuth2 password flow, then a real prediction request">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">1. Generate JWT</p>
            <Button size="sm" onClick={handleGetToken} disabled={tokenLoading}>
              {tokenLoading ? <Loader2 className="size-3.5 animate-spin" /> : <KeyRound className="size-3.5" />}
              POST /api/v1/auth/token
            </Button>
          </div>
          {token && (
            <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-xs text-success">
              <CheckCircle2 className="size-3.5 shrink-0" />
              <span className="truncate font-mono">{token}</span>
            </div>
          )}
          {tokenError && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <XCircle className="size-3.5 shrink-0" />
              {tokenError}
            </div>
          )}

          <p className="pt-2 text-sm font-medium text-foreground">2. Request body</p>
          <JsonBlock data={SAMPLE_REQUEST} />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">3. Run prediction</p>
            <Button size="sm" onClick={handlePredict} disabled={predictLoading} variant="secondary">
              {predictLoading ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
              POST /api/v1/inference/predict
            </Button>
          </div>

          {response && (
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Badge variant="outline" className={response.is_fraud ? "border-destructive/30 bg-destructive/10 text-destructive" : "border-success/30 bg-success/10 text-success"}>
                  {response.is_fraud ? "FRAUD" : "NOT FRAUD"}
                </Badge>
                <span className="text-xs text-muted-foreground">probability {response.fraud_probability}</span>
              </div>
              <JsonBlock data={response} />
            </div>
          )}
          {predictError && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
              <XCircle className="size-3.5 shrink-0" />
              {predictError}
            </div>
          )}
          {!response && !predictError && (
            <p className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-xs text-muted-foreground">
              Generate a token first, then run a prediction to see the real response shape.
            </p>
          )}
        </div>
      </div>
    </Section>
  );
}
