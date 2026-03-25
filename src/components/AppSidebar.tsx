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
];

const dataEntryItems = [
  { title: "Inward", url: "/data-entry/inward", icon: ArrowDownToLine },
  { title: "Outward", url: "/data-entry/outward", icon: ArrowUpFromLine },
  { title: "Transfer", url: "/data-entry/transfer", icon: ArrowLeftRight },
  { title: "Transfer By Name", url: "/data-entry/transfer-by-name", icon: UserCheck },
  { title: "Invoice", url: "/data-entry/invoice", icon: FileText },
];

const reportItems = [
  { title: "Stocks", url: "/reports/stocks", icon: Package },
  { title: "Stock Ledger", url: "/reports/stock-ledger", icon: BookOpen },
  { title: "Cash Ledger", url: "/reports/cash-ledger", icon: Banknote },
  { title: "Vouchers", url: "/reports/vouchers", icon: Receipt },
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
                AdminPro
              </h1>
              <p className="text-[11px] text-sidebar-foreground/50 font-medium">
                Management Suite
              </p>
            </div>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 py-3 space-y-1">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
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
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <div className="px-3 py-1">
          <div className="h-px bg-sidebar-border" />
        </div>

        <NavGroup label="Define" icon={Settings} items={defineItems} collapsed={collapsed} />
        <NavGroup label="Data Entry" icon={PenLine} items={dataEntryItems} collapsed={collapsed} />
        <NavGroup label="Reports" icon={BarChart3} items={reportItems} collapsed={collapsed} />
      </SidebarContent>

      <SidebarFooter className="px-4 py-3 border-t border-sidebar-border">
        {!collapsed && (
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center">
              <span className="text-xs font-semibold text-sidebar-primary">A</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-sidebar-accent-foreground truncate">Admin</p>
              <p className="text-[11px] text-sidebar-foreground/50 truncate">admin@company.com</p>
            </div>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
