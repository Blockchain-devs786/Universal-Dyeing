import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import DashboardLayout from "@/components/DashboardLayout";
import Dashboard from "@/pages/Dashboard";
import UserManagement from "@/pages/UserManagement";
import MsParties from "@/pages/define/MsParties";
import Vendors from "@/pages/define/Vendors";
import Assets from "@/pages/define/Assets";
import Expenses from "@/pages/define/Expenses";
import Inward from "@/pages/data-entry/Inward";
import Outward from "@/pages/data-entry/Outward";
import Transfer from "@/pages/data-entry/Transfer";
import TransferByName from "@/pages/data-entry/TransferByName";
import Invoice from "@/pages/data-entry/Invoice";
import Stocks from "@/pages/reports/Stocks";
import StockLedger from "@/pages/reports/StockLedger";
import CashLedger from "@/pages/reports/CashLedger";
import Vouchers from "@/pages/reports/Vouchers";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route element={<DashboardLayout><Routes><Route path="/" element={<Dashboard />} /></Routes></DashboardLayout>} path="/" />
          <Route path="/*" element={
            <DashboardLayout>
              <Routes>
                <Route path="/user-management" element={<UserManagement />} />
                <Route path="/define/ms-parties" element={<MsParties />} />
                <Route path="/define/vendors" element={<Vendors />} />
                <Route path="/define/assets" element={<Assets />} />
                <Route path="/define/expenses" element={<Expenses />} />
                <Route path="/data-entry/inward" element={<Inward />} />
                <Route path="/data-entry/outward" element={<Outward />} />
                <Route path="/data-entry/transfer" element={<Transfer />} />
                <Route path="/data-entry/transfer-by-name" element={<TransferByName />} />
                <Route path="/data-entry/invoice" element={<Invoice />} />
                <Route path="/reports/stocks" element={<Stocks />} />
                <Route path="/reports/stock-ledger" element={<StockLedger />} />
                <Route path="/reports/cash-ledger" element={<CashLedger />} />
                <Route path="/reports/vouchers" element={<Vouchers />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </DashboardLayout>
          } />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
