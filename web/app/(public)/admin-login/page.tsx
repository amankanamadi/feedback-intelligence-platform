import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { AuthCard } from "@/components/shared/AuthCard";
import { AuthForm } from "@/components/shared/AuthForm";

export default function AdminLoginPage() {
  return (
    <div className="flex w-full flex-col items-center gap-6">
      <div className="flex items-center gap-2 text-primary">
        <ShieldCheck className="size-8" aria-hidden="true" />
        <span className="text-lg font-semibold text-foreground">Feedback Intelligence Admin</span>
      </div>
      <AuthCard title="Admin Login" subtitle="Authorized personnel only.">
        <AuthForm forgotPasswordHref="/forgot-password" />
      </AuthCard>
      <Link href="/login" className="text-sm text-muted-foreground hover:underline">
        Looking to submit feedback instead?
      </Link>
    </div>
  );
}
