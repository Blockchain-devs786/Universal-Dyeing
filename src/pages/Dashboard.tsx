import { LayoutDashboard, Users, Settings, PenLine, BarChart3, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

const sections = [
  {
    title: "Define",
    description: "Set up master data for your organization",
    icon: Settings,
    color: "from-primary to-primary/80",
    items: ["MS Parties", "Vendors", "Assets", "Expenses"],
    link: "/define/ms-parties",
  },
  {
    title: "Data Entry",
    description: "Record daily transactions and movements",
    icon: PenLine,
    color: "from-success to-success/80",
    items: ["Inward", "Outward", "Transfer", "Transfer By Name", "Invoice"],
    link: "/data-entry/inward",
  },
  {
    title: "Reports",
    description: "View analytics and generate reports",
    icon: BarChart3,
    color: "from-info to-info/80",
    items: ["Stocks", "Stock Ledger", "Cash Ledger", "Vouchers"],
    link: "/reports/stocks",
  },
];

const stats = [
  { label: "Total Users", value: "—", icon: Users },
  { label: "Define Items", value: "4", icon: Settings },
  { label: "Data Entry Types", value: "5", icon: PenLine },
  { label: "Report Types", value: "4", icon: BarChart3 },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const userStr = localStorage.getItem("user");
  const user = userStr ? JSON.parse(userStr) : null;
  const displayName = user?.username || "User";

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Welcome */}
      <div className="page-header-gradient rounded-2xl p-8 text-primary-foreground shadow-premium border-none relative overflow-hidden">
        <div className="relative z-10">
            <h1 className="text-3xl font-black mb-2 uppercase tracking-tight">Welcome back, {displayName}</h1>
            <p className="text-primary-foreground/80 text-lg font-medium opacity-90">
            Your management dashboard is ready. All modules are correctly initialized.
            </p>
        </div>
        <div className="absolute top-0 right-0 p-8 h-full flex items-center opacity-10">
            <LayoutDashboard size={120} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="bg-card rounded-xl p-5 shadow-card border border-border">
            <div className="flex items-center justify-between mb-3">
              <stat.icon className="h-5 w-5 text-muted-foreground" />
            </div>
            <p className="text-2xl font-bold text-foreground">{stat.value}</p>
            <p className="text-sm text-muted-foreground">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {sections.map((section) => (
          <div
            key={section.title}
            className="bg-card rounded-xl shadow-card border border-border overflow-hidden hover:shadow-elevated transition-shadow duration-300 cursor-pointer group"
            onClick={() => navigate(section.link)}
          >
            <div className={`h-2 bg-gradient-to-r ${section.color}`} />
            <div className="p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="h-10 w-10 rounded-lg bg-accent flex items-center justify-center">
                  <section.icon className="h-5 w-5 text-accent-foreground" />
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground group-hover:translate-x-1 transition-all" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-1">{section.title}</h3>
              <p className="text-sm text-muted-foreground mb-4">{section.description}</p>
              <div className="flex flex-wrap gap-2">
                {section.items.map((item) => (
                  <span key={item} className="text-xs bg-muted text-muted-foreground rounded-md px-2.5 py-1">
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
