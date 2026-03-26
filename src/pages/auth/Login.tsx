import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { 
  Mail, 
  Lock, 
  ShieldCheck, 
  RefreshCw, 
  ArrowRight,
  User,
  AlertCircle,
  FileKey
} from "lucide-react";
import { authApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

export default function Login() {
  const [step, setStep] = useState(1); // 1: Email, 2: Login
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const navigate = useNavigate();

  // Mutation to check email status
  const checkMutation = useMutation({
    mutationFn: (email: string) => authApi.checkEmail(email),
    onSuccess: (data: any) => {
      if (data.verified) {
        setStep(2);
      } else {
        toast.success("Verification email sent! Please check your inbox.");
      }
    },
    onError: (error: any) => {
      toast.error(error.message || "Email lookup failed.");
    }
  });

  // Mutation to login
  const loginMutation = useMutation({
    mutationFn: (data: any) => authApi.login(data),
    onSuccess: (data: any) => {
      toast.success("Login successful!");
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("user", JSON.stringify(data.user));
      navigate("/");
      window.location.reload(); // Quick refresh for context
    },
    onError: (error: any) => {
      toast.error(error.message || "Invalid credentials.");
    }
  });

  const handleNext = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      toast.error("Please enter your email.");
      return;
    }
    checkMutation.mutate(email);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) {
      toast.error("Please enter your password.");
      return;
    }
    loginMutation.mutate({ email, password });
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-slate-950/20">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.1),transparent_50%)] pointer-events-none" />
      
      <Card className="w-full max-w-md shadow-2xl border-none overflow-hidden animate-in zoom-in-95 duration-500">
        <CardHeader className="bg-slate-900 text-white text-center py-10">
          <div className="mx-auto p-4 bg-blue-600/20 rounded-2xl w-fit mb-4">
            <ShieldCheck className="h-10 w-10 text-blue-400" />
          </div>
          <CardTitle className="text-2xl font-black">Universal Dyeing</CardTitle>
          <CardDescription className="text-slate-400 mt-1">Management Portal v2.0</CardDescription>
        </CardHeader>

        <CardContent className="pt-8 min-h-[300px] flex flex-col justify-center">
          {step === 1 ? (
            <form onSubmit={handleNext} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="email" className="text-xs font-black uppercase text-slate-500 flex items-center gap-2">
                  <Mail className="h-3 w-3" /> Professional Email
                </Label>
                <div className="relative group">
                  <Input 
                    id="email" 
                    type="email" 
                    placeholder="name@organization.com" 
                    value={email} 
                    onChange={e => setEmail(e.target.value)}
                    className="h-12 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/50 pl-10"
                    required
                  />
                  <Mail className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>
                <p className="text-[10px] text-slate-400 italic">We use this to verify your corporate identity.</p>
              </div>

              <Button 
                type="submit" 
                className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg transition-all active:scale-95 group"
                disabled={checkMutation.isPending}
              >
                {checkMutation.isPending ? <RefreshCw className="mr-2 h-5 w-5 animate-spin" /> : <>Continue to Login <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" /></>}
              </Button>
            </form>
          ) : (
            <form onSubmit={handleLogin} className="space-y-6 animate-in slide-in-from-right-4 duration-300">
              <div className="space-y-2 mb-6">
                <div className="flex items-center gap-2 text-sm text-emerald-600 font-bold bg-emerald-50 p-2 rounded-lg border border-emerald-100">
                    <ShieldCheck className="h-4 w-4" /> Account Verified: {email}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="password" className="text-xs font-black uppercase text-slate-500 flex items-center gap-2">
                  <Lock className="h-3 w-3" /> Security Password
                </Label>
                <div className="relative group">
                  <Input 
                    id="password" 
                    type="password" 
                    placeholder="••••••••" 
                    value={password} 
                    onChange={e => setPassword(e.target.value)}
                    className="h-12 border-slate-200 focus-visible:ring-blue-500 bg-slate-50/50 pl-10"
                    required
                  />
                  <Lock className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full h-12 bg-slate-900 border border-slate-800 hover:bg-slate-950 text-white font-bold shadow-xl transition-all active:scale-95"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? <RefreshCw className="mr-2 h-5 w-5 animate-spin" /> : <>Access System <FileKey className="ml-2 h-4 w-4" /></>}
              </Button>
              
              <button 
                type="button" 
                onClick={() => setStep(1)} 
                className="text-xs text-slate-400 hover:text-blue-500 block w-full text-center transition-colors font-medium underline underline-offset-4"
              >
                Switch account
              </button>
            </form>
          )}
        </CardContent>

        <CardFooter className="bg-slate-50 border-t p-6">
          <div className="flex items-start gap-3 w-full">
            <AlertCircle className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
            <p className="text-[10px] text-slate-500 leading-normal">
                This is a restricted administrative system. Unauthorized access attempts are monitored and logged. If you've lost access, contact your IT administrator.
            </p>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
