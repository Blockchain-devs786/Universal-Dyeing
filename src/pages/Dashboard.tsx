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
  
  // Get user from localStorage
  const userStr = localStorage.getItem("user");
  const user = userStr ? JSON.parse(userStr) : null;
  const isAdmin = user?.role === "admin";

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Welcome */}
      <div className="page-header-gradient rounded-2xl p-10 text-primary-foreground shadow-premium border-none relative overflow-hidden">
        {/* Subtle decorative background element */}
        <div className="absolute top-0 right-0 -m-8 h-64 w-64 rounded-full bg-white/10 blur-3xl" />
        
        <div className="relative z-10 flex flex-col gap-2">
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight mb-2 uppercase flex items-center gap-3">
                <LayoutDashboard className="h-8 w-8 sm:h-10 sm:w-10 opacity-50" />
                Welcome Back, <span className="text-white underline decoration-white/20 underline-offset-8 decoration-4">{user?.username || 'User'}</span>
            </h1>
            <p className="text-primary-foreground/80 text-lg font-medium opacity-90 max-w-2xl leading-relaxed">
              {isAdmin 
                ? "Your management command center is ready. You have complete oversight of all organizational modules and reports."
                : "Your personal workspace is active. Use the side menu to begin your daily tasks and movements."}
            </p>
        </div>
      </div>

      {isAdmin && (
        <>
            {/* Stats - Only for Admin */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {stats.map((stat) => (
                <div key={stat.label} className="bg-card rounded-xl p-6 shadow-card border border-border/60 hover:border-primary/30 transition-colors duration-300 group">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-2.5 rounded-lg bg-slate-100/50 group-hover:bg-primary/5 transition-colors">
                            <stat.icon className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                        </div>
                    </div>
                    <p className="text-3xl font-black text-foreground tracking-tight">{stat.value}</p>
                    <p className="text-xs font-black uppercase tracking-wider text-muted-foreground/60 mt-1">{stat.label}</p>
                </div>
                ))}
            </div>

            {/* Sections - Only for Admin */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
                {sections.map((section) => (
                <div
                    key={section.title}
                    className="bg-card rounded-2xl shadow-card border border-border/40 overflow-hidden hover:shadow-elevated hover:border-primary/20 transition-all duration-300 cursor-pointer group flex flex-col h-full"
                    onClick={() => navigate(section.link)}
                >
                    <div className={`h-1.5 bg-gradient-to-r ${section.color}`} />
                    <div className="p-7 flex flex-col flex-1">
                    <div className="flex items-center justify-between mb-5">
                        <div className="h-12 w-12 rounded-xl bg-slate-100 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <section.icon className="h-6 w-6 text-slate-700 group-hover:text-primary transition-colors" />
                        </div>
                        <div className="h-8 w-8 rounded-full flex items-center justify-center bg-slate-50 group-hover:bg-primary/10 transition-colors">
                            <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-all" />
                        </div>
                    </div>
                    <h3 className="text-xl font-black text-foreground mb-2 uppercase tracking-tight">{section.title}</h3>
                    <p className="text-sm text-muted-foreground/80 mb-6 font-medium leading-relaxed">{section.description}</p>
                    <div className="mt-auto flex flex-wrap gap-2">
                        {section.items.map((item) => (
                        <span key={item} className="text-[10px] sm:text-[11px] font-black uppercase tracking-wide bg-slate-100 text-slate-500 rounded-md px-2.5 py-1 group-hover:bg-white group-hover:shadow-sm transition-all border border-transparent group-hover:border-slate-100">
                            {item}
                        </span>
                        ))}
                    </div>
                    </div>
                </div>
                ))}
            </div>
        </>
      )}

      {!isAdmin && (
          <div className="flex flex-col items-center justify-center py-20 px-4 text-center animate-in fade-in duration-1000">
              <div className="h-24 w-24 rounded-full bg-slate-50 flex items-center justify-center mb-6">
                  <LayoutDashboard className="h-10 w-10 text-slate-300" />
              </div>
              <h2 className="text-xl font-bold text-slate-400 uppercase tracking-widest mb-4">Workspace Selection Pending</h2>
              <p className="text-slate-500 max-w-sm font-medium leading-relaxed">
                  Please use the left-hand navigation menu to access your assigned modules and begin your professional session.
              </p>
          </div>
      )}
    </div>
  );
}
