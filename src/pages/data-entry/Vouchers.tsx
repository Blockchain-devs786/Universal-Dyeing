import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  Receipt, Plus, Search, Trash2, Printer, 
  ArrowDownCircle, ArrowUpCircle, Scale,
  Building2, Truck, Wallet, HardDrive, Landmark, PlusCircle, X
} from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { 
  vouchersApi, msPartiesApi, vendorsApi, 
  expensesApi, accountsApi, assetsApi,
  type Voucher, type VoucherEntry 
} from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

type AccountType = 'MS Party' | 'Vendor' | 'Expense' | 'Account' | 'Asset';

interface FormEntry {
  account_type: AccountType;
  account_id: number;
  debit: number;
  credit: number;
  description: string;
}

export default function Vouchers() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedPrintId, setSelectedPrintId] = useState<number | null>(null);

  // Form State
  const [voucherType, setVoucherType] = useState<'CRV' | 'CPV' | 'JV'>('CRV');
  const [voucherDate, setVoucherDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [voucherRef, setVoucherRef] = useState("");
  const [voucherDesc, setVoucherDesc] = useState("");
  const [entries, setEntries] = useState<FormEntry[]>([
    { account_type: 'Account', account_id: 0, debit: 0, credit: 0, description: "" },
    { account_type: 'MS Party', account_id: 0, debit: 0, credit: 0, description: "" },
  ]);

  // Fetching Account Data for Dropdowns
  const { data: msParties = [] } = useQuery({ queryKey: ["ms_parties"], queryFn: () => msPartiesApi.list() });
  const { data: vendors = [] } = useQuery({ queryKey: ["vendors"], queryFn: () => vendorsApi.list() });
  const { data: expenses = [] } = useQuery({ queryKey: ["expenses"], queryFn: () => expensesApi.list() });
  const { data: bankAccounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: () => accountsApi.list() });
  const { data: assets = [] } = useQuery({ queryKey: ["assets"], queryFn: () => assetsApi.list() });

  const accountOptions = useMemo(() => ({
    'MS Party': msParties,
    'Vendor': vendors,
    'Expense': expenses,
    'Account': bankAccounts,
    'Asset': assets,
  }), [msParties, vendors, expenses, bankAccounts, assets]);

  // Fetch Vouchers
  const { data: vouchers = [], isLoading } = useQuery({
    queryKey: ["vouchers", search, typeFilter],
    queryFn: () => vouchersApi.list({ 
      search, 
      type: typeFilter !== "all" ? typeFilter : undefined 
    }),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => vouchersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vouchers"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["ms_parties"] });
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      toast.success("Voucher posted successfully");
      setIsDialogOpen(false);
      resetForm();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => vouchersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vouchers"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["ms_parties"] });
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      toast.success("Voucher deleted and balances reversed");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Totals
  const totalDebit = entries.reduce((sum, e) => sum + (Number(e.debit) || 0), 0);
  const totalCredit = entries.reduce((sum, e) => sum + (Number(e.credit) || 0), 0);
  const isBalanced = Math.abs(totalDebit - totalCredit) < 0.01 && totalDebit > 0;

  const resetForm = () => {
    setVoucherType('CRV');
    setVoucherDate(format(new Date(), 'yyyy-MM-dd'));
    setVoucherRef("");
    setVoucherDesc("");
    setEntries([
        { account_type: 'Account', account_id: 0, debit: 0, credit: 0, description: "" },
        { account_type: 'MS Party', account_id: 0, debit: 0, credit: 0, description: "" },
    ]);
  };

  const addEntry = () => {
    setEntries([...entries, { account_type: 'Expense', account_id: 0, debit: 0, credit: 0, description: "" }]);
  };

  const handlePrint = (id: number) => {
    setSelectedPrintId(id);
    setTimeout(() => {
      window.print();
      setSelectedPrintId(null);
    }, 100);
  };

  const removeEntry = (index: number) => {
    if (entries.length <= 2) return toast.error("Voucher must have at least 2 entries");
    setEntries(entries.filter((_, i) => i !== index));
  };

  const updateEntry = (index: number, field: keyof FormEntry, value: any) => {
    const newEntries = [...entries];
    newEntries[index] = { ...newEntries[index], [field]: value };
    
    // For simple CRV/CPV logic: 
    // If it's a 2-line voucher and user updates first line's amount, sync second line.
    if (voucherType !== 'JV' && entries.length === 2 && (field === 'debit' || field === 'credit')) {
       const otherIndex = index === 0 ? 1 : 0;
       const amt = parseFloat(value) || 0;
       if (field === 'debit') newEntries[otherIndex].credit = amt;
       if (field === 'credit') newEntries[otherIndex].debit = amt;
    }

    setEntries(newEntries);
  };

  const handleVoucherTypeChange = (type: 'CRV' | 'CPV' | 'JV') => {
    setVoucherType(type);
    if (type === 'CRV') {
        setEntries([
            { account_type: 'Account', account_id: 0, debit: 0, credit: 0, description: "Cash Received" },
            { account_type: 'MS Party', account_id: 0, debit: 0, credit: 0, description: "Party Payment" },
        ]);
    } else if (type === 'CPV') {
        setEntries([
            { account_type: 'Expense', account_id: 0, debit: 0, credit: 0, description: "Expense Payment" },
            { account_type: 'Account', account_id: 0, debit: 0, credit: 0, description: "Cash Paid" },
        ]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isBalanced) return toast.error("Voucher is not balanced! Total Debit must equal Total Credit.");
    
    // Validation
    for (const entry of entries) {
        if (!entry.account_id) return toast.error("Please select all accounts");
    }

    createMutation.mutate({
        type: voucherType,
        date: voucherDate,
        ref_no: voucherRef,
        description: voucherDesc,
        total_amount: totalDebit,
        entries: entries
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500 print:hidden">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <Receipt className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Voucher Management</h1>
            <p className="text-white/80 mt-1">Post and manage CRV, CPV, and Journal Vouchers.</p>
          </div>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-white text-primary hover:bg-white/90 shadow-md transition-all px-6 font-bold">
              <Plus className="mr-2 h-4 w-4" /> New Voucher
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[900px] max-h-[90vh] flex flex-col p-0 overflow-hidden">
            <form onSubmit={handleSubmit} className="flex flex-col h-full">
              <DialogHeader className="p-6 pb-2">
                <DialogTitle className="text-2xl font-black flex items-center gap-2">
                    <PlusCircle className="h-6 w-6 text-primary" />
                    Record New Financial Voucher
                </DialogTitle>
              </DialogHeader>

              <div className="flex-1 overflow-y-auto p-6 pt-2 space-y-6 custom-scrollbar" style={{ maxHeight: 'calc(90vh - 180px)' }}>
                {/* Header Info */}
                <div className="grid grid-cols-4 gap-4 p-4 bg-slate-50 rounded-xl border border-dashed border-slate-300">
                    <div className="space-y-1.5">
                        <Label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest pl-1">Voucher Type</Label>
                        <Select value={voucherType} onValueChange={(v: any) => handleVoucherTypeChange(v)}>
                            <SelectTrigger className="h-10 font-bold bg-white ring-offset-0 focus:ring-1">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="CRV">Cash Receipt (CRV)</SelectItem>
                                <SelectItem value="CPV">Cash Payment (CPV)</SelectItem>
                                <SelectItem value="JV">Journal Voucher (JV)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1.5">
                        <Label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest pl-1">Voucher Date</Label>
                        <Input type="date" value={voucherDate} onChange={e => setVoucherDate(e.target.value)} className="h-10 font-bold bg-white" />
                    </div>
                    <div className="space-y-1.5 col-span-2">
                        <Label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest pl-1">Ref / Bill # (Optional)</Label>
                        <Input value={voucherRef} onChange={e => setVoucherRef(e.target.value)} placeholder="Ref Number" className="h-10 font-bold bg-white" />
                    </div>
                    <div className="space-y-1.5 col-span-4">
                        <Label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest pl-1">General Description</Label>
                        <Input value={voucherDesc} onChange={e => setVoucherDesc(e.target.value)} placeholder="Overall narration for this voucher..." className="h-10 bg-white" />
                    </div>
                </div>

                {/* Entry Lines */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between mb-1">
                        <h3 className="text-sm font-black text-slate-800 uppercase tracking-tighter">Transaction Details</h3>
                        {voucherType === 'JV' && (
                            <Button type="button" variant="outline" size="sm" onClick={addEntry} className="h-7 text-[10px] font-black border-primary text-primary hover:bg-primary/5">
                                <Plus className="h-3 w-3 mr-1" /> Add Entry Row
                            </Button>
                        )}
                    </div>

                    <div className="border rounded-xl overflow-hidden shadow-sm">
                        <Table>
                            <TableHeader className="bg-slate-100/50">
                                <TableRow className="hover:bg-transparent h-10">
                                    <TableHead className="w-[180px] text-[10px] font-black uppercase">Account Type</TableHead>
                                    <TableHead className="text-[10px] font-black uppercase">Account / Party</TableHead>
                                    <TableHead className="w-[120px] text-right text-[10px] font-black uppercase">Debit (Rs)</TableHead>
                                    <TableHead className="w-[120px] text-right text-[10px] font-black uppercase">Credit (Rs)</TableHead>
                                    <TableHead className="w-[40px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {entries.map((entry, idx) => (
                                    <TableRow key={idx} className="hover:bg-transparent h-14">
                                        <TableCell className="py-2">
                                            <Select value={entry.account_type} onValueChange={(v: AccountType) => updateEntry(idx, 'account_type', v)}>
                                                <SelectTrigger className="h-9 text-xs">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="MS Party">MS Party</SelectItem>
                                                    <SelectItem value="Vendor">Vendor</SelectItem>
                                                    <SelectItem value="Expense">Expense</SelectItem>
                                                    <SelectItem value="Account">Bank/Cash</SelectItem>
                                                    <SelectItem value="Asset">Asset</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell className="py-2">
                                            <Select value={String(entry.account_id)} onValueChange={(v) => updateEntry(idx, 'account_id', Number(v))}>
                                                <SelectTrigger className="h-9 text-xs">
                                                    <SelectValue placeholder="Select Account" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    {accountOptions[entry.account_type].map((opt: any) => (
                                                        <SelectItem key={opt.id} value={String(opt.id)}>{opt.name}</SelectItem>
                                                    ))}
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell className="py-2">
                                            <Input 
                                                type="number" 
                                                value={entry.debit || ""} 
                                                onChange={e => updateEntry(idx, 'debit', parseFloat(e.target.value) || 0)} 
                                                className="h-9 text-right font-bold text-blue-700 bg-blue-50/30 border-blue-100" 
                                                placeholder="0.00"
                                            />
                                        </TableCell>
                                        <TableCell className="py-2">
                                            <Input 
                                                type="number" 
                                                value={entry.credit || ""} 
                                                onChange={e => updateEntry(idx, 'credit', parseFloat(e.target.value) || 0)} 
                                                className="h-9 text-right font-bold text-red-700 bg-red-50/30 border-red-100" 
                                                placeholder="0.00"
                                            />
                                        </TableCell>
                                        <TableCell className="py-2 text-center">
                                            {voucherType === 'JV' && (
                                                <Button type="button" variant="ghost" size="icon" className="h-7 w-7 text-red-400 hover:text-red-600" onClick={() => removeEntry(idx)}>
                                                    <X className="h-4 w-4" />
                                                </Button>
                                            )}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </div>

                {/* Totals Section */}
                <div className="flex justify-between items-center p-5 bg-slate-900 rounded-xl text-white shadow-lg overflow-hidden relative">
                    <div className="absolute right-0 top-0 h-full w-1/3 opacity-10 pointer-events-none">
                        <Scale className="h-32 w-32 -rotate-12 translate-x-10 -translate-y-5" />
                    </div>
                    <div className="flex items-center gap-10">
                        <div className="space-y-0.5">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Total Debit</p>
                            <p className="text-2xl font-black text-blue-400">Rs {totalDebit.toLocaleString()}</p>
                        </div>
                        <div className="space-y-0.5">
                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Total Credit</p>
                            <p className="text-2xl font-black text-red-400">Rs {totalCredit.toLocaleString()}</p>
                        </div>
                    </div>
                    {isBalanced ? (
                        <div className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/50 px-4 py-2 rounded-lg flex items-center gap-2">
                            <Scale className="h-5 w-5" />
                            <span className="text-sm font-black uppercase italic">Voucher Balanced</span>
                        </div>
                    ) : (
                        <div className="bg-red-500/20 text-red-400 border border-red-500/50 px-4 py-2 rounded-lg flex items-center gap-2">
                            <Scale className="h-5 w-5 animate-bounce" />
                            <span className="text-sm font-black uppercase italic">Unbalanced (Diff: {Math.abs(totalDebit - totalCredit).toLocaleString()})</span>
                        </div>
                    )}
                </div>
              </div>

              <DialogFooter className="p-6 pt-2 border-t bg-slate-50/50">
                <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)} className="px-8">Discard</Button>
                <Button 
                    type="submit" 
                    disabled={!isBalanced || createMutation.isPending} 
                    className={cn(
                        "px-12 h-11 font-black shadow-lg shadow-primary/20",
                        !isBalanced && "opacity-50 cursor-not-allowed"
                    )}
                >
                  {createMutation.isPending ? "Posting..." : "Confirm & Post Voucher"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-100 flex items-center gap-4 shadow-sm group hover:border-primary/30 transition-all cursor-pointer" onClick={() => setTypeFilter('all')}>
            <div className="p-2.5 rounded-lg bg-slate-50 text-slate-400 group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                <Search className="h-5 w-5" />
            </div>
            <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Filter</p>
                <p className="text-sm font-black text-slate-800">All Vouchers</p>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100 flex items-center gap-4 shadow-sm group hover:border-emerald-300 transition-all cursor-pointer" onClick={() => setTypeFilter('CRV')}>
            <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-500 group-hover:bg-emerald-100 transition-colors">
                <ArrowDownCircle className="h-5 w-5" />
            </div>
            <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Receipts</p>
                <p className="text-sm font-black text-slate-800">CRV Vouchers</p>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100 flex items-center gap-4 shadow-sm group hover:border-rose-300 transition-all cursor-pointer" onClick={() => setTypeFilter('CPV')}>
            <div className="p-2.5 rounded-lg bg-rose-50 text-rose-500 group-hover:bg-rose-100 transition-colors">
                <ArrowUpCircle className="h-5 w-5" />
            </div>
            <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Payments</p>
                <p className="text-sm font-black text-slate-800">CPV Vouchers</p>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100 flex items-center gap-4 shadow-sm group hover:border-blue-300 transition-all cursor-pointer" onClick={() => setTypeFilter('JV')}>
            <div className="p-2.5 rounded-lg bg-blue-50 text-blue-500 group-hover:bg-blue-100 transition-colors">
                <Scale className="h-5 w-5" />
            </div>
            <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Adjustments</p>
                <p className="text-sm font-black text-slate-800">JV Vouchers</p>
            </div>
          </div>
      </div>

      <div className="bg-card shadow-card rounded-2xl overflow-hidden border">
        <div className="p-4 border-b bg-muted/30 flex flex-col sm:flex-row justify-between gap-4">
          <div className="relative max-w-sm w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search voucher # or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-white"
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-bold uppercase tracking-tight h-8 px-4 bg-white border-slate-200 text-slate-600">
                {typeFilter === 'all' ? 'All Types' : `${typeFilter} Filter`}
            </Badge>
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent bg-slate-50/50">
              <TableHead className="w-[120px]">Date</TableHead>
              <TableHead className="w-[120px]">Voucher #</TableHead>
              <TableHead className="w-[100px] text-center">Type</TableHead>
              <TableHead>Narration</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead className="text-center">Status</TableHead>
              <TableHead className="text-right px-6">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-20">
                  <div className="flex flex-col items-center gap-2 animate-pulse">
                    <Receipt className="h-10 w-10 text-muted-foreground/30" />
                    <p className="text-muted-foreground font-medium">Loading history...</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : vouchers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-20 text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                        <Receipt className="h-10 w-10 text-muted-foreground/20" />
                        <p>No vouchers found for this filter.</p>
                    </div>
                </TableCell>
              </TableRow>
            ) : (
              vouchers.map((v: any) => (
                <TableRow key={v.id} className="transition-colors hover:bg-muted/30 group">
                  <TableCell className="font-medium text-slate-500">{format(new Date(v.date), 'dd MMM yyyy')}</TableCell>
                  <TableCell className="font-black text-slate-900">{v.voucher_no}</TableCell>
                  <TableCell className="text-center">
                    <Badge className={cn(
                      "font-black text-[10px] w-14 justify-center",
                      v.type === 'CRV' ? "bg-emerald-500 hover:bg-emerald-600" :
                      v.type === 'CPV' ? "bg-rose-500 hover:bg-rose-600" :
                      "bg-blue-500 hover:bg-blue-600"
                    )}>
                      {v.type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <p className="text-xs text-slate-600 line-clamp-1">{v.description || "No narration"}</p>
                    <p className="text-[9px] text-slate-400 font-bold uppercase tracking-tight">Ref: {v.ref_no || "-"}</p>
                  </TableCell>
                  <TableCell className="text-right font-black text-slate-900">
                    Rs {Number(v.total_amount).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="secondary" className="bg-emerald-50 text-emerald-600 border border-emerald-100 text-[9px] font-black uppercase tracking-widest px-2.5">
                        {v.status || 'Posted'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right px-6">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:bg-blue-50" onClick={() => handlePrint(v.id)}>
                        <Printer className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:bg-red-50" onClick={() => {
                        if(confirm(`Delete voucher ${v.voucher_no}? All related ledger entries will be reversed.`)) {
                          deleteMutation.mutate(v.id);
                        }
                      }}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      {/* Hidden Print Template */}
      <div id="voucher-print-area" className="hidden print:block p-8 bg-white font-serif text-[12pt] leading-relaxed">
        {vouchers.filter((v: any) => selectedPrintId === null || v.id === selectedPrintId).map((v: any) => (
          <div key={v.id} id={`print-voucher-${v.id}`} className="space-y-8 page-break-after border p-10 rounded-lg relative overflow-hidden">
            {/* Watermark/Logo styling */}
            <div className="absolute top-0 right-0 opacity-[0.03] -translate-y-10 translate-x-10">
                <Receipt size={400} />
            </div>

            <div className="flex justify-between items-start border-b-2 border-slate-900 pb-6 relative z-10">
              <div>
                <h1 className="text-4xl font-black tracking-tighter text-slate-900 uppercase">Universal Dyeing</h1>
                <p className="text-sm font-bold text-slate-600 uppercase tracking-widest mt-1">Industrial Textile Solutions</p>
                <div className="mt-4 text-xs font-medium text-slate-500">
                    <p>Faisalabad, Pakistan</p>
                    <p>Tel: +92 3XX XXXXXXX</p>
                </div>
              </div>
              <div className="text-right">
                <div className="inline-block px-6 py-2 bg-slate-900 text-white rounded-md font-black text-xl uppercase tracking-tighter">
                  {v.type === 'CRV' ? 'Cash Receipt' : v.type === 'CPV' ? 'Cash Payment' : 'Journal Voucher'}
                </div>
                <div className="mt-4 space-y-1">
                    <p className="text-sm font-black text-slate-900">Voucher #: <span className="font-serif italic ml-1">{v.voucher_no}</span></p>
                    <p className="text-sm font-black text-slate-900">Date: <span className="font-serif italic ml-1">{format(new Date(v.date), 'dd MMM yyyy')}</span></p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-10 py-4 relative z-10">
                <div className="bg-slate-50 p-4 rounded-md border border-slate-200">
                    <p className="text-[10pt] font-black uppercase text-slate-400 tracking-widest mb-2">Narration / Description</p>
                    <p className="italic text-slate-800">{v.description || "No specific narration provided."}</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-md border border-slate-200">
                    <p className="text-[10pt] font-black uppercase text-slate-400 tracking-widest mb-2">Reference Info</p>
                    <p className="font-bold text-slate-900">{v.ref_no || "N/A"}</p>
                    <p className="text-[10pt] font-black uppercase text-slate-400 tracking-widest mb-1 mt-3">Total Amount</p>
                    <p className="text-2xl font-black text-slate-900">Rs {Number(v.total_amount).toLocaleString()}</p>
                </div>
            </div>

            <div className="mt-8 border rounded-lg overflow-hidden relative z-10">
              <Table className="w-full border-collapse">
                <TableHeader className="bg-slate-900 text-white">
                  <TableRow className="h-12">
                    <TableHead className="text-white font-black uppercase text-xs pl-6">Account Details</TableHead>
                    <TableHead className="text-white font-black uppercase text-xs">Entity Type</TableHead>
                    <TableHead className="text-white font-black uppercase text-xs text-right">Debit (PKR)</TableHead>
                    <TableHead className="text-white font-black uppercase text-xs text-right pr-6">Credit (PKR)</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {v.entries?.map((entry: any, eIdx: number) => (
                    <TableRow key={eIdx} className="h-10 border-b border-slate-100 italic">
                      <TableCell className="pl-6 font-bold text-slate-800">
                        {
                            entry.account_type === 'MS Party' ? msParties.find(p => p.id === entry.account_id)?.name :
                            entry.account_type === 'Vendor' ? vendors.find(p => p.id === entry.account_id)?.name :
                            entry.account_type === 'Expense' ? expenses.find(p => p.id === entry.account_id)?.name :
                            entry.account_type === 'Account' ? bankAccounts.find(p => p.id === entry.account_id)?.name :
                            assets.find(p => p.id === entry.account_id)?.name
                        }
                      </TableCell>
                      <TableCell className="text-sm font-bold text-slate-400 uppercase tracking-tighter">{entry.account_type}</TableCell>
                      <TableCell className="text-right font-black text-slate-900">{entry.debit > 0 ? Number(entry.debit).toLocaleString() : '-'}</TableCell>
                      <TableCell className="text-right font-black text-slate-900 pr-6">{entry.credit > 0 ? Number(entry.credit).toLocaleString() : '-'}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="h-14 bg-slate-50">
                    <TableCell colSpan={2} className="pl-6 font-black uppercase text-sm tracking-widest text-slate-900">Voucher Totals</TableCell>
                    <TableCell className="text-right font-black text-xl text-slate-900 border-l">Rs {Number(v.total_amount).toLocaleString()}</TableCell>
                    <TableCell className="text-right font-black text-xl text-slate-900 pr-6 border-l">Rs {Number(v.total_amount).toLocaleString()}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>

            <div className="grid grid-cols-3 gap-10 mt-24 relative z-10 pt-10">
                <div className="border-t border-slate-400 pt-3 text-center">
                    <p className="text-xs font-black uppercase tracking-widest text-slate-400">Prepared By</p>
                </div>
                <div className="border-t border-slate-400 pt-3 text-center">
                    <p className="text-xs font-black uppercase tracking-widest text-slate-400">Authorized Signature</p>
                </div>
                <div className="border-t border-slate-400 pt-3 text-center">
                    <p className="text-xs font-black uppercase tracking-widest text-slate-400">Received By</p>
                </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
