import { AppSidebar } from "@/components/app-shell/AppSidebar";
import { AppTopbar } from "@/components/app-shell/AppTopbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-1">
      <AppSidebar />
      <div className="flex flex-1 flex-col">
        <AppTopbar />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
