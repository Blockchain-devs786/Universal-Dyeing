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

function LayoutWrapper({ children }: { children: React.ReactNode }) {
  return <DashboardLayout>{children}</DashboardLayout>;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LayoutWrapper><Dashboard /></LayoutWrapper>} />
          <Route path="/user-management" element={<LayoutWrapper><UserManagement /></LayoutWrapper>} />
          <Route path="/define/ms-parties" element={<LayoutWrapper><MsParties /></LayoutWrapper>} />
          <Route path="/define/vendors" element={<LayoutWrapper><Vendors /></LayoutWrapper>} />
          <Route path="/define/assets" element={<LayoutWrapper><Assets /></LayoutWrapper>} />
          <Route path="/define/expenses" element={<LayoutWrapper><Expenses /></LayoutWrapper>} />
          <Route path="/data-entry/inward" element={<LayoutWrapper><Inward /></LayoutWrapper>} />
          <Route path="/data-entry/outward" element={<LayoutWrapper><Outward /></LayoutWrapper>} />
          <Route path="/data-entry/transfer" element={<LayoutWrapper><Transfer /></LayoutWrapper>} />
          <Route path="/data-entry/transfer-by-name" element={<LayoutWrapper><TransferByName /></LayoutWrapper>} />
          <Route path="/data-entry/invoice" element={<LayoutWrapper><Invoice /></LayoutWrapper>} />
          <Route path="/reports/stocks" element={<LayoutWrapper><Stocks /></LayoutWrapper>} />
          <Route path="/reports/stock-ledger" element={<LayoutWrapper><StockLedger /></LayoutWrapper>} />
          <Route path="/reports/cash-ledger" element={<LayoutWrapper><CashLedger /></LayoutWrapper>} />
          <Route path="/reports/vouchers" element={<LayoutWrapper><Vouchers /></LayoutWrapper>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
