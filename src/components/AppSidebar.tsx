import {
  LayoutDashboard,
  Users,
  Settings,
  ChevronDown,
  Building2,
  Truck,
  HardDrive,
  Wallet,
  ArrowDownToLine,
  ArrowUpFromLine,
  ArrowLeftRight,
  UserCheck,
  FileText,
  Package,
  BookOpen,
  Banknote,
  Receipt,
  PenLine,
  BarChart3,
  Landmark,
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

const defineItems = [
  { title: "MS Parties", url: "/define/ms-parties", icon: Building2 },
  { title: "From Parties", url: "/define/from-parties", icon: Building2 },
  { title: "Vendors", url: "/define/vendors", icon: Truck },
  { title: "Items", url: "/define/items", icon: Package },
  { title: "Assets", url: "/define/assets", icon: HardDrive },
  { title: "Expenses", url: "/define/expenses", icon: Wallet },
  { title: "Accounts", url: "/define/accounts", icon: Landmark },
  { title: "Outward Parties", url: "/define/outward-parties", icon: Truck },
];

const dataEntryItems = [
  { title: "Inward", url: "/data-entry/inward", icon: ArrowDownToLine },
  { title: "Outward", url: "/data-entry/outward", icon: ArrowUpFromLine },
  { title: "Transfer", url: "/data-entry/transfer", icon: ArrowLeftRight },
  { title: "Transfer By Name", url: "/data-entry/transfer-by-name", icon: UserCheck },
  { title: "Invoice", url: "/data-entry/invoice", icon: FileText },
  { title: "Vouchers", url: "/data-entry/vouchers", icon: Receipt },
];

const reportItems = [
  { title: "Stocks", url: "/reports/stocks", icon: Package },
  { title: "Stock Ledger", url: "/reports/stock-ledger", icon: BookOpen },
  { title: "Cash Ledger", url: "/reports/cash-ledger", icon: Banknote },
];

interface NavGroupProps {
  label: string;
  icon: React.ElementType;
  items: { title: string; url: string; icon: React.ElementType }[];
  collapsed: boolean;
}

function NavGroup({ label, icon: GroupIcon, items, collapsed }: NavGroupProps) {
  const location = useLocation();
  const isActive = items.some((i) => location.pathname.startsWith(i.url));

  return (
    <Collapsible defaultOpen={isActive}>
      <SidebarGroup>
        <CollapsibleTrigger className="w-full">
          <SidebarGroupLabel className="flex items-center justify-between text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors cursor-pointer uppercase text-[11px] font-semibold tracking-wider px-3 py-2">
            <span className="flex items-center gap-2">
              <GroupIcon className="h-4 w-4" />
              {!collapsed && label}
            </span>
            {!collapsed && (
              <ChevronDown className="h-3.5 w-3.5 transition-transform duration-200 group-data-[state=open]:rotate-180" />
            )}
          </SidebarGroupLabel>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-accent-foreground hover:bg-sidebar-accent transition-all duration-150"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      {!collapsed && <span className="text-sm">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </CollapsibleContent>
      </SidebarGroup>
    </Collapsible>
  );
}

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();

  // Get user from localStorage
  const userStr = localStorage.getItem("user");
  const user = userStr ? JSON.parse(userStr) : null;
  const access = user?.module_access || "";
  const isAdmin = user?.role === "admin" || access === "all";

  const hasAccess = (moduleId: string) => {
    if (isAdmin) return true;
    if (moduleId === "dashboard") return true; // Dashboard always visible
    return access.split(",").includes(moduleId);
  };

  // Filter items
  const filteredDefine = defineItems.filter((item) => {
      const map: Record<string, string> = {
          "/define/ms-parties": "define_ms_parties",
          "/define/from-parties": "define_from_parties",
          "/define/vendors": "define_vendors",
          "/define/items": "define_items",
          "/define/assets": "define_assets",
          "/define/expenses": "define_expenses",
          "/define/accounts": "define_accounts",
          "/define/outward-parties": "define_outward_parties",
      };
      return hasAccess(map[item.url]);
  });
  
  const filteredDataEntry = dataEntryItems.filter((item) => {
    const map: Record<string, string> = {
      "/data-entry/inward": "inward",
      "/data-entry/outward": "outward",
      "/data-entry/transfer": "transfer",
      "/data-entry/transfer-by-name": "transfer_by_name",
      "/data-entry/invoice": "invoice",
      "/data-entry/vouchers": "vouchers",
    };
    return hasAccess(map[item.url]);
  });

  const filteredReports = reportItems.filter((item) => {
    if (item.url === "/reports/stocks") return hasAccess("reports_stocks");
    return hasAccess("reports_ledger"); // Both ledgers under reports_ledger
  });

  const handleLogout = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  return (
    <Sidebar collapsible="icon" className="border-r-0">
      <SidebarHeader className="px-4 py-5 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg page-header-gradient flex items-center justify-center shrink-0">
            <LayoutDashboard className="h-5 w-5 text-primary-foreground" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="text-base font-bold text-sidebar-accent-foreground tracking-tight">
                Universal Dyeing
              </h1>
              <p className="text-[11px] text-sidebar-foreground/50 font-medium">
                Dyeing Management Suite
              </p>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 py-3 space-y-1">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {hasAccess("dashboard") && (
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to="/"
                      end
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-accent-foreground hover:bg-sidebar-accent transition-all duration-150"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <LayoutDashboard className="h-4 w-4 shrink-0" />
                      {!collapsed && <span className="text-sm">Dashboard</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
              
              {isAdmin && (
                <>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to="/user-management"
                      end
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-accent-foreground hover:bg-sidebar-accent transition-all duration-150"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <Users className="h-4 w-4 shrink-0" />
                      {!collapsed && <span className="text-sm">User Management</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                    <SidebarMenuButton asChild>
                      <NavLink
                        to="/settings"
                        end
                        className="flex items-center gap-3 px-3 py-2 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-accent-foreground hover:bg-sidebar-accent transition-all duration-150"
                        activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                      >
                        <Settings className="h-4 w-4 shrink-0" />
                        {!collapsed && <span className="text-sm">App Settings</span>}
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <div className="px-3 py-1">
          <div className="h-px bg-sidebar-border" />
        </div>

        {filteredDefine.length > 0 && <NavGroup label="Define" icon={Settings} items={filteredDefine} collapsed={collapsed} />}
        {filteredDataEntry.length > 0 && <NavGroup label="Data Entry" icon={PenLine} items={filteredDataEntry} collapsed={collapsed} />}
        {filteredReports.length > 0 && <NavGroup label="Reports" icon={BarChart3} items={filteredReports} collapsed={collapsed} />}
      </SidebarContent>

      <SidebarFooter className="px-4 py-3 border-t border-sidebar-border">
        {!collapsed && (
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center border border-sidebar-border">
                <span className="text-xs font-semibold text-sidebar-primary uppercase">
                  {user?.username?.[0] || 'U'}
                </span>
              </div>
              <div className="min-w-0">
                <p className="text-sm font-bold text-sidebar-accent-foreground truncate uppercase">{user?.username || 'User'}</p>
                <p className="text-[10px] text-sidebar-foreground/50 truncate font-medium uppercase">{user?.role || 'Guest'}</p>
              </div>
            </div>
            <button 
              onClick={handleLogout}
              className="p-1.5 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors text-sidebar-foreground/40"
              title="Logout"
            >
              <ArrowUpFromLine className="h-4 w-4 rotate-90" />
            </button>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
