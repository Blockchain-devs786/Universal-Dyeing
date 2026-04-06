import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { useLocation } from "react-router-dom";

const routeTitles: Record<string, string> = {
  "/": "Dashboard",
  "/user-management": "User Management",
  "/define/ms-parties": "MS Parties",
  "/define/vendors": "Vendors",
  "/define/assets": "Assets",
  "/define/expenses": "Expenses",
  "/data-entry/inward": "Inward",
  "/data-entry/outward": "Outward",
  "/data-entry/transfer": "Transfer",
  "/data-entry/transfer-by-name": "Transfer By Name",
  "/data-entry/invoice": "Invoice",
  "/reports/stocks": "Stocks",
  "/reports/stock-ledger": "Stock Ledger",
  "/reports/cash-ledger": "Cash Ledger",
  "/reports/vouchers": "Vouchers",
  "/define/outward-parties": "Outward Parties",
  "/settings": "Settings",
};

const routeBreadcrumbs: Record<string, string[]> = {
  "/": ["Dashboard"],
  "/user-management": ["User Management"],
  "/define/ms-parties": ["Define", "MS Parties"],
  "/define/vendors": ["Define", "Vendors"],
  "/define/assets": ["Define", "Assets"],
  "/define/expenses": ["Define", "Expenses"],
  "/data-entry/inward": ["Data Entry", "Inward"],
  "/data-entry/outward": ["Data Entry", "Outward"],
  "/data-entry/transfer": ["Data Entry", "Transfer"],
  "/data-entry/transfer-by-name": ["Data Entry", "Transfer By Name"],
  "/data-entry/invoice": ["Data Entry", "Invoice"],
  "/reports/stocks": ["Reports", "Stocks"],
  "/reports/stock-ledger": ["Reports", "Stock Ledger"],
  "/reports/cash-ledger": ["Reports", "Cash Ledger"],
  "/reports/vouchers": ["Reports", "Vouchers"],
  "/define/outward-parties": ["Define", "Outward Parties"],
  "/settings": ["Settings"],
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const title = routeTitles[location.pathname] || "Page";
  const breadcrumbs = routeBreadcrumbs[location.pathname] || [title];

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full print:block">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-14 flex items-center gap-4 border-b border-border bg-card px-4 sticky top-0 z-10 print:hidden">
            <SidebarTrigger className="text-muted-foreground hover:text-foreground" />
            <div className="flex items-center gap-2 text-sm">
              {breadcrumbs.map((crumb, i) => (
                <span key={i} className="flex items-center gap-2">
                  {i > 0 && <span className="text-muted-foreground/40">/</span>}
                  <span className={i === breadcrumbs.length - 1 ? "font-medium text-foreground" : "text-muted-foreground"}>
                    {crumb}
                  </span>
                </span>
              ))}
            </div>
          </header>
          <main className="flex-1 p-4 sm:p-6 print:p-0">
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
