import { useEffect, useState } from "react";
import { useRouteError, isRouteErrorResponse } from "react-router-dom";
import { AlertOctagon, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

// Vite dev-server restarts and production re-deploys both invalidate
// previously-fetched chunk URLs. A route lazily imported before that happens
// throws "Failed to fetch dynamically imported module" the next time the
// user navigates to it — this is a stale-cache problem, not a real crash, so
// the correct fix is a single automatic reload rather than showing an error.
// Guarded by sessionStorage so a *genuinely* broken chunk doesn't reload
// forever.
const RELOAD_GUARD_KEY = "secureml-chunk-reload-attempted";

function isChunkLoadError(error: unknown): boolean {
  const message = error instanceof Error ? error.message : String(error);
  return /failed to fetch dynamically imported module|error loading dynamically imported module|importing a module script failed/i.test(
    message,
  );
}

export function RouteErrorBoundary() {
  const error = useRouteError();
  const [autoReloading, setAutoReloading] = useState(false);

  const chunkError = isChunkLoadError(error);

  useEffect(() => {
    if (!chunkError) return;
    const alreadyTried = sessionStorage.getItem(RELOAD_GUARD_KEY);
    if (alreadyTried) return;
    sessionStorage.setItem(RELOAD_GUARD_KEY, "1");
    setAutoReloading(true);
    window.location.reload();
  }, [chunkError]);

  // Once a route successfully renders again after a reload, clear the guard
  // so a future genuine restart can still trigger one auto-reload.
  useEffect(() => {
    return () => sessionStorage.removeItem(RELOAD_GUARD_KEY);
  }, []);

  const title = chunkError ? "Reloading — the app was updated" : "Something went wrong";
  const description = chunkError
    ? "The dev server (or a new deploy) restarted while this page was open, so the previously loaded module is stale. Reloading automatically..."
    : isRouteErrorResponse(error)
      ? `${error.status} ${error.statusText}`
      : error instanceof Error
        ? error.message
        : "An unexpected error occurred while loading this page.";

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-destructive/15">
        {autoReloading ? (
          <RefreshCw className="size-7 animate-spin text-destructive" />
        ) : (
          <AlertOctagon className="size-7 text-destructive" />
        )}
      </div>
      <div>
        <h1 className="text-lg font-semibold text-foreground">{title}</h1>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
      {!autoReloading && (
        <Button onClick={() => window.location.reload()}>
          <RefreshCw className="size-4" />
          Reload the page
        </Button>
      )}
    </div>
  );
}
