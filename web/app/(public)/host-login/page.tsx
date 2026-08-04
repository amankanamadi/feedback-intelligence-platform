import Link from "next/link";
import { Home } from "lucide-react";
import { AuthCard } from "@/components/shared/AuthCard";
import { AuthForm } from "@/components/shared/AuthForm";

export default function HostLoginPage() {
  return (
    <div className="flex w-full flex-col items-center gap-6">
      <div className="flex items-center gap-2 text-primary">
        <Home className="size-8" aria-hidden="true" />
        <span className="text-lg font-semibold text-foreground">Airbnb Guest Experience Intelligence</span>
      </div>
      <AuthCard
        title="Host Sign In"
        subtitle="Manage your properties, respond to guest complaints, and track your performance."
        footer={
          <p className="text-center text-sm text-muted-foreground">
            New host?{" "}
            <Link href="/signup" className="text-primary hover:underline">
              Create an account
            </Link>
          </p>
        }
      >
        <AuthForm forgotPasswordHref="/forgot-password" />
      </AuthCard>
      <div className="flex flex-col items-center gap-1">
        <Link href="/login" className="text-sm text-muted-foreground hover:underline">
          Guest? Sign in here
        </Link>
        <Link href="/admin-login" className="text-sm text-muted-foreground hover:underline">
          Airbnb operations staff? Sign in here
        </Link>
      </div>
    </div>
  );
}
