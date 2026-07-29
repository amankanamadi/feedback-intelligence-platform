import { UserTopbar } from "@/components/user-portal/UserTopbar";

export default function UserPortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-portal="user" className="flex min-h-screen flex-1 flex-col">
      <UserTopbar />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col p-6">{children}</main>
    </div>
  );
}
