import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  Users, 
  UserPlus, 
  Mail, 
  User as UserIcon, 
  Lock, 
  ShieldCheck, 
  RefreshCw,
  AlertCircle
} from "lucide-react";
import { authApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

export default function UserManagement() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: any) => authApi.createUser(data),
    onSuccess: () => {
      toast.success("User created successfully!");
      // Reset form
      setEmail("");
      setUsername("");
      setPassword("");
      setRole("user");
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to create user.");
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !username || !password) {
      toast.error("Please fill all required fields.");
      return;
    }
    createMutation.mutate({ email, username, password, role });
  };

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center gap-4">
        <div className="p-3 bg-blue-600/10 rounded-xl">
          <Users className="h-8 w-8 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System User Management</h1>
          <p className="text-slate-500 text-sm mt-1">Create and manage administrative and staff accounts.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 space-y-4">
            <Card className="border-blue-100 bg-blue-50/30">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-bold flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4 text-blue-600" /> Administrative Notice
                    </CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-slate-600 leading-relaxed">
                    User creation triggers a verification workflow. New users will receive an automated email from Resend to activate their accounts before they can login. 
                </CardContent>
            </Card>
            
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex gap-3">
                <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <p className="text-[11px] text-amber-900 leading-normal">
                    <strong>Security Policy:</strong> Ensure passwords are at least 8 characters long and unique for each user.
                </p>
            </div>
        </div>

        <Card className="md:col-span-2 shadow-elevated border-none overflow-hidden">
          <CardHeader className="bg-slate-900 text-white pb-6">
            <CardTitle className="text-xl flex items-center gap-2">
                <UserPlus className="h-5 w-5" /> Account Information
            </CardTitle>
            <CardDescription className="text-slate-400">Fill in the details to register a new system user.</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="pt-8 space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-xs font-black uppercase text-slate-500 flex items-center gap-2">
                    <UserIcon className="h-3 w-3" /> Username
                  </Label>
                  <Input 
                    id="username" 
                    placeholder="e.g., admin_main" 
                    value={username} 
                    onChange={e => setUsername(e.target.value)}
                    className="h-11 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/50"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-xs font-black uppercase text-slate-500 flex items-center gap-2">
                    <Mail className="h-3 w-3" /> Email Address
                  </Label>
                  <Input 
                    id="email" 
                    type="email" 
                    placeholder="user@example.com" 
                    value={email} 
                    onChange={e => setEmail(e.target.value)}
                    className="h-11 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="role" className="text-xs font-black uppercase text-slate-500 flex items-center gap-2">
                    <ShieldCheck className="h-3 w-3" /> Account Role
                  </Label>
                  <Select value={role} onValueChange={setRole}>
                    <SelectTrigger className="h-11 border-slate-200 focus:ring-blue-500 bg-slate-50/50">
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">Standard User</SelectItem>
                      <SelectItem value="manager">Manager</SelectItem>
                      <SelectItem value="admin">Administrator</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-xs font-black uppercase text-slate-500 flex items-center gap-2">
                    <Lock className="h-3 w-3" /> Initial Password
                  </Label>
                  <Input 
                    id="password" 
                    type="password" 
                    placeholder="••••••••" 
                    value={password} 
                    onChange={e => setPassword(e.target.value)}
                    className="h-11 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/50"
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter className="bg-slate-50 border-t p-6">
              <Button 
                type="submit" 
                className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg shadow-lg active:scale-95 transition-all disabled:opacity-50"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? <RefreshCw className="mr-2 h-5 w-5 animate-spin" /> : <UserPlus className="mr-2 h-5 w-5" />}
                Authorize & Create New User
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
