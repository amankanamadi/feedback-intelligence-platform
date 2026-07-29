"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/shared/PasswordInput";
import { useChangePasswordMutation } from "@/hooks/use-change-password";
import { useUpdateProfileMutation } from "@/hooks/use-update-profile";
import { useAuth, isApiError } from "@/lib/auth";
import { formatDate } from "@/lib/format";

const profileSchema = z.object({
  fullName: z.string().max(200).optional(),
});
type ProfileFormValues = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, "Current password is required."),
    newPassword: z.string().min(8, "Password must be at least 8 characters."),
    confirmPassword: z.string().min(1, "Please confirm your new password."),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords do not match.",
    path: ["confirmPassword"],
  });
type PasswordFormValues = z.infer<typeof passwordSchema>;

function ProfileForm() {
  const { user } = useAuth();
  const updateProfileMutation = useUpdateProfileMutation();

  const { register, handleSubmit } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { fullName: user?.full_name ?? "" },
  });

  const onSubmit = (values: ProfileFormValues) => {
    updateProfileMutation.mutate(values.fullName ?? "", {
      onSuccess: () => toast.success("Profile updated."),
      onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
    });
  };

  if (!user) return null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" value={user.email} disabled />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="fullName">Full name</Label>
        <Input id="fullName" {...register("fullName")} placeholder="Your name" />
      </div>
      <dl className="text-xs text-muted-foreground">
        <dt className="inline">Member since </dt>
        <dd className="inline text-foreground">{formatDate(user.created_at)}</dd>
      </dl>
      <Button type="submit" className="w-fit" isLoading={updateProfileMutation.isPending}>
        Save profile
      </Button>
    </form>
  );
}

function ChangePasswordForm() {
  const changePasswordMutation = useChangePasswordMutation();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
  });

  const onSubmit = (values: PasswordFormValues) => {
    changePasswordMutation.mutate(
      { current_password: values.currentPassword, new_password: values.newPassword },
      {
        onSuccess: () => {
          toast.success("Password changed.");
          reset();
        },
        onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
      }
    );
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="currentPassword">Current password</Label>
        <PasswordInput id="currentPassword" autoComplete="current-password" {...register("currentPassword")} />
        {errors.currentPassword && (
          <p className="text-sm text-destructive" role="alert">
            {errors.currentPassword.message}
          </p>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="newPassword">New password</Label>
        <PasswordInput id="newPassword" autoComplete="new-password" {...register("newPassword")} />
        {errors.newPassword && (
          <p className="text-sm text-destructive" role="alert">
            {errors.newPassword.message}
          </p>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="confirmPassword">Confirm new password</Label>
        <PasswordInput id="confirmPassword" autoComplete="new-password" {...register("confirmPassword")} />
        {errors.confirmPassword && (
          <p className="text-sm text-destructive" role="alert">
            {errors.confirmPassword.message}
          </p>
        )}
      </div>
      <Button type="submit" className="w-fit" isLoading={changePasswordMutation.isPending}>
        Change password
      </Button>
    </form>
  );
}

export default function ProfilePage() {
  return (
    <div className="flex max-w-xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Profile</h1>
        <p className="text-muted-foreground">Update your details and manage your password.</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile details</CardTitle>
        </CardHeader>
        <CardContent>
          <ProfileForm />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change password</CardTitle>
          <CardDescription>Choose a new password for your account.</CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordForm />
        </CardContent>
      </Card>
    </div>
  );
}
