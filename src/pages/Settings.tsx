import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Settings as SettingsIcon, Save, RefreshCw, Mail, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { settingsApi } from "@/lib/api-client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardContent, CardDescription, CardFooter } from "@/components/ui/card";

export default function Settings() {
  const queryClient = useQueryClient();
  const [whatsappNo, setWhatsappNo] = useState("");
  const [email, setEmail] = useState("");

  const { data: settings = [], isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => settingsApi.list(),
  });

  useEffect(() => {
    if (settings.length > 0) {
      const w = settings.find((s: any) => s.key === "whatsapp_no");
      const e = settings.find((s: any) => s.key === "email");
      if (w) setWhatsappNo(w.value);
      if (e) setEmail(e.value);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, string>) => settingsApi.updateMultiple(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Settings updated successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      whatsapp_no: whatsappNo,
      email: email,
    });
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <SettingsIcon className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Application Settings</h1>
            <p className="text-white/80 mt-1">Configure global application variables and contact info.</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6">
        <Card className="shadow-card border-none bg-white/50 backdrop-blur-sm">
          <form onSubmit={handleSubmit}>
            <CardHeader>
              <CardTitle className="text-xl font-bold flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-blue-600" />
                Communication Channels
              </CardTitle>
              <CardDescription>
                These details will be used for sharing ledgers and reports via WhatsApp and Email.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="whatsapp" className="text-sm font-bold text-slate-700">WhatsApp Number</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold">+</span>
                  <Input 
                    id="whatsapp" 
                    value={whatsappNo} 
                    onChange={e => setWhatsappNo(e.target.value)} 
                    placeholder="923001234567" 
                    className="pl-7 h-12 text-lg font-medium shadow-inner border-slate-200"
                  />
                </div>
                <p className="text-[10px] text-slate-400 italic px-1">Include country code without + or spaces.</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-bold text-slate-700 font-sans">Default Admin Email</Label>
                <div className="relative">
                   <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                   <Input 
                    id="email" 
                    type="email"
                    value={email} 
                    onChange={e => setEmail(e.target.value)} 
                    placeholder="admin@example.com" 
                    className="pl-11 h-12 text-lg font-medium shadow-inner border-slate-200"
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter className="bg-slate-50/50 border-t p-6 flex justify-end">
              <Button 
                type="submit" 
                disabled={updateMutation.isPending || isLoading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-8 h-12 font-bold shadow-lg transition-all active:scale-95"
              >
                {updateMutation.isPending ? (
                  <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
                ) : (
                  <Save className="mr-2 h-5 w-5" />
                )}
                Save Configuration
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
