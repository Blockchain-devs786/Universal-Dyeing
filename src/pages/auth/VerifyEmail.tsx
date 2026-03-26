import { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { 
  ShieldCheck, 
  ShieldAlert, 
  RefreshCw, 
  CheckCircle2, 
  ArrowRight,
  Mail,
  Home
} from "lucide-react";
import { authApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const verifyMutation = useMutation({
    mutationFn: (token: string) => authApi.verifyEmail(token),
    onSuccess: () => {
      setStatus("success");
      // Auto redirect after 5 seconds?
      setTimeout(() => navigate("/login"), 5000);
    },
    onError: (error: any) => {
      setStatus("error");
      setErrorMsg(error.message || "Email verification failed.");
    }
  });

  useEffect(() => {
    if (token) {
      verifyMutation.mutate(token);
    } else {
      setStatus("error");
      setErrorMsg("Missing verification token.");
    }
  }, [token]);

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-slate-950/20">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.1),transparent_50%)] pointer-events-none" />
      
      <Card className="w-full max-w-md shadow-2xl border-none overflow-hidden animate-in zoom-in-95 duration-500">
        <CardHeader className="bg-slate-900 text-white text-center py-10">
          <div className="mx-auto p-4 bg-blue-600/20 rounded-2xl w-fit mb-4">
            {status === "loading" && <RefreshCw className="h-10 w-10 text-blue-400 animate-spin" />}
            {status === "success" && <CheckCircle2 className="h-10 w-10 text-emerald-400" />}
            {status === "error" && <ShieldAlert className="h-10 w-10 text-red-400" />}
          </div>
          <CardTitle className="text-2xl font-black">
            {status === "loading" ? "Verifying Email..." : 
             status === "success" ? "Email Verified" : "Verification Failed"}
          </CardTitle>
          <CardDescription className="text-slate-400 mt-1">
            {status === "loading" ? "Please wait while we secure your account." : 
             status === "success" ? "Your account is now active and ready." : "Something went wrong during activation."}
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-8 min-h-[200px] flex flex-col justify-center text-center">
            {status === "loading" && (
                <p className="text-slate-500 text-sm font-medium animate-pulse">
                    Initializing secure connection to Neon Auth...
                </p>
            )}
            
            {status === "success" && (
                <div className="space-y-6">
                    <p className="text-slate-600 text-sm">
                        Thank you for verifying your email. You can now login to access the management portal.
                    </p>
                    <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 flex items-center gap-3 text-emerald-800 text-xs font-bold shadow-sm">
                        <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
                        Redirecting to login page in 5 seconds...
                    </div>
                </div>
            )}

            {status === "error" && (
                <div className="space-y-6">
                    <div className="p-4 bg-red-50 rounded-xl border border-red-100 text-red-800 text-sm font-medium shadow-sm">
                        {errorMsg}
                    </div>
                    <p className="text-slate-500 text-xs px-4">
                        This link may have expired or was already used. Try logging in again to receive a fresh verification link.
                    </p>
                </div>
            )}
        </CardContent>

        <CardFooter className="bg-slate-50 border-t p-6 flex flex-col gap-3">
          <Button asChild className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg transition-all active:scale-95">
            <Link to="/login">
                Go to Login <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" className="w-full h-10 text-slate-500 border-none shadow-none hover:bg-slate-200/50">
            <Link to="/">
                <Home className="mr-2 h-4 w-4" /> Home Page
            </Link>
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
