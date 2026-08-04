import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { AuthCard } from "@/components/shared/AuthCard";
import { AuthForm } from "@/components/shared/AuthForm";

export default function AdminLoginPage() {
  return (
    <div className="flex w-full flex-col items-center gap-6">
      <div className="flex items-center gap-2 text-primary">
        <ShieldCheck className="size-8" aria-hidden="true" />
        <span className="text-lg font-semibold text-foreground">Airbnb Operations</span>
      </div>
      <AuthCard title="Operations Sign In" subtitle="For Customer Support, Operations, Product, Trust & Safety, and Executive Leadership teams only.">
        <AuthForm forgotPasswordHref="/forgot-password" />
      </AuthCard>
      <div className="flex flex-col items-center gap-1">
        <Link href="/login" className="text-sm text-muted-foreground hover:underline">
          Guest? Sign in here
        </Link>
        <Link href="/host-login" className="text-sm text-muted-foreground hover:underline">
          Host? Sign in here
        </Link>
      </div>
    </div>
  );
}
