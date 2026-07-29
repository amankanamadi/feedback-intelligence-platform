import Link from "next/link";
import { MessageSquareHeart } from "lucide-react";
import { AuthCard } from "@/components/shared/AuthCard";
import { AuthForm } from "@/components/shared/AuthForm";

export default function LoginPage() {
  return (
    <div data-portal="user" className="flex w-full flex-col items-center gap-6">
      <div className="flex items-center gap-2 text-primary">
        <MessageSquareHeart className="size-8" aria-hidden="true" />
        <span className="text-lg font-semibold text-foreground">Feedback Intelligence</span>
      </div>
      <AuthCard
        title="Login to Give Feedback"
        subtitle="Share your ideas, report issues, and help us improve our products."
        footer={
          <p className="text-center text-sm text-muted-foreground">
            New here?{" "}
            <Link href="/signup" className="text-primary hover:underline">
              Create an account
            </Link>
          </p>
        }
      >
        <AuthForm forgotPasswordHref="/forgot-password" />
      </AuthCard>
      <Link href="/admin-login" className="text-sm text-muted-foreground hover:underline">
        Administrator? Sign in here
      </Link>
    </div>
  );
}
