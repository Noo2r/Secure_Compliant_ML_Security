import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { useNavigate, useLocation } from "react-router-dom";
import { ShieldCheck, Loader2, Eye, EyeOff, Lock, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useAuth } from "@/hooks/use-auth";

const loginSchema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { signIn, isLoading, error } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  });

  const fillDemo = () => {
    setValue("username", "svc-ml-engineer");
    setValue("password", "CHANGE_ME_IN_PRODUCTION");
  };

  const from = (location.state as { from?: Location })?.from?.pathname ?? "/";

  const onSuccessRedirect = handleSubmit(async (values) => {
    await signIn(values)
      .then(() => navigate(from, { replace: true }))
      .catch(() => undefined);
  });

  return (
    <div className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background px-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, color-mix(in srgb, var(--primary) 18%, transparent), transparent 45%), radial-gradient(circle at 80% 70%, color-mix(in srgb, var(--success) 12%, transparent), transparent 45%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative z-10 w-full max-w-sm"
      >
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-primary/15 ring-1 ring-primary/30">
            <ShieldCheck className="size-6 text-primary" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Secure ML Security Platform</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign in to the fraud detection control plane</p>
        </div>

        <form onSubmit={onSuccessRedirect} className="space-y-4 rounded-xl border border-border bg-card p-6 shadow-lg shadow-black/20">
          {error && (
            <Alert variant="destructive">
              <Lock className="size-4" />
              <AlertTitle>Authentication failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="username">Username</Label>
            <Input id="username" placeholder="svc-ml-engineer" autoComplete="username" {...register("username")} />
            {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                autoComplete="current-password"
                className="pr-9"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 flex w-9 items-center justify-center text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}
            Sign in
          </Button>

          <button
            type="button"
            onClick={fillDemo}
            className="w-full text-center text-xs text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
          >
            Use demo credentials (svc-ml-engineer)
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          OAuth2 password flow against <code className="rounded bg-muted px-1 py-0.5 font-mono">/api/v1/auth/token</code> — JWT
          bearer tokens, 15-minute expiry, rate-limited.
        </p>
      </motion.div>
    </div>
  );
}
