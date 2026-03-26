import { Navigate, useLocation } from "react-router-dom";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("auth_token");
  const expiry = localStorage.getItem("auth_expiry");
  const location = useLocation();

  const isExpired = expiry && new Date().getTime() > parseInt(expiry);

  if (!token || isExpired) {
    // If expired, clear the stale data
    if (isExpired) {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_expiry");
        localStorage.removeItem("user");
    }

    // Redirect them to the /login page
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
