"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/shared/PasswordInput";
import { useLoginMutation } from "@/hooks/use-login";
import { isApiError } from "@/lib/auth";
import type { Role } from "@/types/auth";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
  rememberMe: z.boolean(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const ROLE_HOME: Record<Role, string> = {
  USER: "/portal",
  ADMIN: "/admin",
};

export function AuthForm(props: { forgotPasswordHref: string }) {
  return (
    <Suspense>
      <AuthFormInner {...props} />
    </Suspense>
  );
}

function AuthFormInner({ forgotPasswordHref }: { forgotPasswordHref: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const loginMutation = useLoginMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: true },
  });

  const onSubmit = (values: LoginFormValues) => {
    loginMutation.mutate(
      { email: values.email, password: values.password, remember_me: values.rememberMe },
      {
        onSuccess: (user) => {
          const next = searchParams.get("next");
          router.push(next ?? ROLE_HOME[user.role]);
        },
        onError: (error) => {
          toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again.");
        },
      }
    );
  };

  return (
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

      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Password</Label>
          <Link href={forgotPasswordHref} className="text-sm text-primary hover:underline">
            Forgot password?
          </Link>
        </div>
        <PasswordInput id="password" autoComplete="current-password" {...register("password")} />
        {errors.password && (
          <p className="text-sm text-destructive" role="alert">
            {errors.password.message}
          </p>
        )}
      </div>

      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <input type="checkbox" className="size-4 rounded border-border" {...register("rememberMe")} />
        Remember me
      </label>

      <Button type="submit" className="w-full" isLoading={loginMutation.isPending}>
        Log in
      </Button>
    </form>
  );
}
