import { AdminSidebar } from "@/components/admin-portal/AdminSidebar";
import { AdminTopbar } from "@/components/admin-portal/AdminTopbar";

export default function AdminPortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div data-portal="admin" className="flex min-h-screen flex-1">
      <AdminSidebar />
      <div className="flex flex-1 flex-col">
        <AdminTopbar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
