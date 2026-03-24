import { LucideIcon } from "lucide-react";
import { Construction } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

export default function PlaceholderPage({ title, description, icon: Icon }: PlaceholderPageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="h-20 w-20 rounded-2xl bg-accent flex items-center justify-center mb-6">
        <Icon className="h-10 w-10 text-accent-foreground" />
      </div>
      <h1 className="text-2xl font-bold text-foreground mb-2">{title}</h1>
      <p className="text-muted-foreground max-w-md mb-8">{description}</p>
      <div className="flex items-center gap-2 text-sm text-muted-foreground/60 bg-muted rounded-full px-4 py-2">
        <Construction className="h-4 w-4" />
        <span>Coming soon in Phase 2</span>
      </div>
    </div>
  );
}
