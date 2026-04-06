import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import DashboardLayout from "@/components/DashboardLayout";
import Dashboard from "@/pages/Dashboard";
import UserManagement from "@/pages/UserManagement";
import MsParties from "@/pages/define/MsParties";
import FromParties from "@/pages/define/FromParties";
import Vendors from "@/pages/define/Vendors";
import Items from "@/pages/define/Items";
import Assets from "@/pages/define/Assets";
import Expenses from "@/pages/define/Expenses";
import Accounts from "@/pages/define/Accounts";
import OutwardParties from "@/pages/define/OutwardParties";
import Inward from "@/pages/data-entry/Inward";
import Outward from "@/pages/data-entry/Outward";
import Transfer from "@/pages/data-entry/Transfer";
import TransferByName from "@/pages/data-entry/TransferByName";
import Invoice from "@/pages/data-entry/Invoice";
import Stocks from "@/pages/reports/Stocks";
import StockLedger from "@/pages/reports/StockLedger";
import CashLedger from "@/pages/reports/CashLedger";
import Vouchers from "@/pages/data-entry/Vouchers";
import Settings from "@/pages/Settings";
import NotFound from "@/pages/NotFound";
import Login from "@/pages/auth/Login";
import VerifyEmail from "@/pages/auth/VerifyEmail";
import AuthGuard from "@/components/AuthGuard";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

function LayoutWrapper({ children }: { children: React.ReactNode }) {
  return <DashboardLayout>{children}</DashboardLayout>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          
          {/* Protected Management Routes */}
          <Route path="/" element={<AuthGuard><LayoutWrapper><Dashboard /></LayoutWrapper></AuthGuard>} />
          
          {/* User Management (Protected) */}
          <Route path="/user-management" element={<AuthGuard><LayoutWrapper><UserManagement /></LayoutWrapper></AuthGuard>} />
          
          <Route path="/define/ms-parties" element={<AuthGuard><LayoutWrapper><MsParties /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/from-parties" element={<AuthGuard><LayoutWrapper><FromParties /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/vendors" element={<AuthGuard><LayoutWrapper><Vendors /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/items" element={<AuthGuard><LayoutWrapper><Items /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/assets" element={<AuthGuard><LayoutWrapper><Assets /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/expenses" element={<AuthGuard><LayoutWrapper><Expenses /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/accounts" element={<AuthGuard><LayoutWrapper><Accounts /></LayoutWrapper></AuthGuard>} />
          <Route path="/define/outward-parties" element={<AuthGuard><LayoutWrapper><OutwardParties /></LayoutWrapper></AuthGuard>} />
          <Route path="/data-entry/inward" element={<AuthGuard><LayoutWrapper><Inward /></LayoutWrapper></AuthGuard>} />
          <Route path="/data-entry/outward" element={<AuthGuard><LayoutWrapper><Outward /></LayoutWrapper></AuthGuard>} />
          <Route path="/data-entry/transfer" element={<AuthGuard><LayoutWrapper><Transfer /></LayoutWrapper></AuthGuard>} />
          <Route path="/data-entry/transfer-by-name" element={<AuthGuard><LayoutWrapper><TransferByName /></LayoutWrapper></AuthGuard>} />
          <Route path="/data-entry/invoice" element={<AuthGuard><LayoutWrapper><Invoice /></LayoutWrapper></AuthGuard>} />
          <Route path="/data-entry/vouchers" element={<AuthGuard><LayoutWrapper><Vouchers /></LayoutWrapper></AuthGuard>} />
          <Route path="/reports/stocks" element={<AuthGuard><LayoutWrapper><Stocks /></LayoutWrapper></AuthGuard>} />
          <Route path="/reports/stock-ledger" element={<AuthGuard><LayoutWrapper><StockLedger /></LayoutWrapper></AuthGuard>} />
          <Route path="/reports/cash-ledger" element={<AuthGuard><LayoutWrapper><CashLedger /></LayoutWrapper></AuthGuard>} />
          <Route path="/settings" element={<AuthGuard><LayoutWrapper><Settings /></LayoutWrapper></AuthGuard>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
      <Sonner position="top-center" richColors />
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
