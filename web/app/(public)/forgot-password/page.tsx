"use client";

import Link from "next/link";
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { AuthCard } from "@/components/shared/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useForgotPasswordMutation } from "@/hooks/use-forgot-password";
import { isApiError } from "@/lib/auth";

const forgotPasswordSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address."),
});

type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const forgotPasswordMutation = useForgotPasswordMutation();
  const [devResetLink, setDevResetLink] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = (values: ForgotPasswordValues) => {
    forgotPasswordMutation.mutate(values.email, {
      onSuccess: (data) => {
        toast.success(data.detail);
        // Only ever populated when the backend is running in debug mode
        // (no real email delivery exists yet) - surfaces the reset link
        // directly instead of silently doing nothing in dev.
        if (data.reset_token) {
          setDevResetLink(`/reset-password?token=${encodeURIComponent(data.reset_token)}`);
        }
      },
      onError: (error) => {
        toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again.");
      },
    });
  };

  return (
    <div className="flex w-full flex-col items-center gap-6">
      <AuthCard
        title="Reset your password"
        subtitle="Enter your email and we'll help you get back into your account."
        footer={
          <p className="text-center text-sm text-muted-foreground">
            <Link href="/login" className="text-primary hover:underline">
              Back to login
            </Link>
          </p>
        }
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" placeholder="you@example.com" {...register("email")} />
            {errors.email && (
              <p className="text-sm text-destructive" role="alert">
                {errors.email.message}
              </p>
            )}
          </div>
          <Button type="submit" className="w-full" isLoading={forgotPasswordMutation.isPending}>
            Send reset link
          </Button>
        </form>
        {devResetLink && (
          <div className="rounded-md border border-border bg-muted p-3 text-sm">
            <p className="font-medium">Dev mode - no email was sent.</p>
            <Link href={devResetLink} className="text-primary hover:underline">
              Click here to reset your password
            </Link>
          </div>
        )}
      </AuthCard>
    </div>
  );
}
