"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { MessageSquareHeart } from "lucide-react";
import { AuthCard } from "@/components/shared/AuthCard";
import { PasswordInput } from "@/components/shared/PasswordInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRegisterMutation } from "@/hooks/use-register";
import { isApiError } from "@/lib/auth";

const signupSchema = z
  .object({
    fullName: z.string().max(200).optional(),
    email: z.string().min(1, "Email is required").email("Enter a valid email address."),
    password: z.string().min(8, "Password must be at least 8 characters."),
    confirmPassword: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match.",
    path: ["confirmPassword"],
  });

type SignupFormValues = z.infer<typeof signupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const registerMutation = useRegisterMutation();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: "", email: "", password: "", confirmPassword: "" },
  });

  const onSubmit = (values: SignupFormValues) => {
    registerMutation.mutate(
      { email: values.email, password: values.password, full_name: values.fullName || undefined },
      {
        onSuccess: () => {
          toast.success("Account created!");
          router.push("/app");
        },
        onError: (error) => {
          toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again.");
        },
      }
    );
  };

  return (
    <div className="flex w-full flex-col items-center gap-6">
      <div className="flex items-center gap-2 text-primary">
        <MessageSquareHeart className="size-8" aria-hidden="true" />
        <span className="text-lg font-semibold text-foreground">Feedback Intelligence</span>
      </div>
      <AuthCard
        title="Create your account"
        subtitle="Sign up to share feedback and track its progress."
        footer={
          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline">
              Log in
            </Link>
          </p>
        }
      >
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="fullName">Full name</Label>
            <Input id="fullName" autoComplete="name" placeholder="Jordan Lee" {...register("fullName")} />
          </div>

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
            <Label htmlFor="password">Password</Label>
            <PasswordInput id="password" autoComplete="new-password" {...register("password")} />
            {errors.password && (
              <p className="text-sm text-destructive" role="alert">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="confirmPassword">Confirm password</Label>
            <PasswordInput id="confirmPassword" autoComplete="new-password" {...register("confirmPassword")} />
            {errors.confirmPassword && (
              <p className="text-sm text-destructive" role="alert">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>

          <Button type="submit" className="w-full" isLoading={registerMutation.isPending}>
            Create account
          </Button>
        </form>
      </AuthCard>
    </div>
  );
}
