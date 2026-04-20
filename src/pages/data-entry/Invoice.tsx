import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { 
  FileText, 
  Plus, 
  Search, 
  Printer, 
  Trash2, 
  RefreshCw, 
  Check, 
  ChevronsUpDown,
  FileSearch,
  Receipt,
  Pencil,
  ChevronRight,
  ChevronDown
} from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { invoicesApi, msPartiesApi, accountsApi, type Invoice } from "@/lib/api-client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  DialogFooter,
} from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

export default function Invoice() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isPrintOpen, setIsPrintOpen] = useState(false);
  
  // States for printing
  const [selectedInvoicesForPrint, setSelectedInvoicesForPrint] = useState<any[]>([]);
  const [bulkSelectedIds, setBulkSelectedIds] = useState<number[]>([]);

  // Get current user
  const currentUser = useMemo(() => {
    const userStr = localStorage.getItem("user");
    return userStr ? JSON.parse(userStr) : { username: 'System' };
  }, []);

  // Form State for Creation
  const [step, setStep] = useState(1);
  const [msPartyId, setMsPartyId] = useState<string>("all");
  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [selectedOutwardIds, setSelectedOutwardIds] = useState<number[]>([]);
  const [rate15, setRate15] = useState(0);
  const [rate22, setRate22] = useState(0);
  const [discountPercent, setDiscountPercent] = useState(0);
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [type, setType] = useState<'credit'|'debit'>('credit');
  const [cashAccountId, setCashAccountId] = useState<string>("");
  const [invoiceDays, setInvoiceDays] = useState<number | ''>("");

  // Edit State
  const [selectedInvoice, setSelectedInvoice] = useState<any>(null);
  const [editRate15, setEditRate15] = useState(0);
  const [editRate22, setEditRate22] = useState(0);
  const [editDiscountPercent, setEditDiscountPercent] = useState(0);
  const [editType, setEditType] = useState<'credit'|'debit'>('credit');
  const [editCashAccountId, setEditCashAccountId] = useState<string>("");
  const [editInvoiceDays, setEditInvoiceDays] = useState<number | ''>("");

  // Queries
  const { data: invoices = [], isLoading, refetch } = useQuery({
    queryKey: ["invoices", search],
    queryFn: () => invoicesApi.list(search),
  });

  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => accountsApi.list(),
  });

  const { data: availableOutwards = [], isLoading: isLoadingOutwards } = useQuery({
    queryKey: ["available_outwards", msPartyId],
    queryFn: () => invoicesApi.getAvailableOutwards(Number(msPartyId)),
    enabled: msPartyId !== "all" && isCreateOpen && step === 2
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: any) => invoicesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice created successfully");
      setIsCreateOpen(false);
      resetForm();
    },
    onError: (e: any) => toast.error(e.message)
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number, data: any }) => invoicesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice updated successfully");
      setIsEditOpen(false);
    },
    onError: (e: any) => toast.error(e.message)
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => invoicesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      toast.success("Invoice deleted successfully");
    },
    onError: (e: any) => toast.error(e.message)
  });

  const resetForm = () => {
    setStep(1);
    setMsPartyId("all");
    setSelectedOutwardIds([]);
    setRate15(0);
    setRate22(0);
    setDiscountPercent(0);
    setDate(format(new Date(), 'yyyy-MM-dd'));
    setType('credit');
    setCashAccountId("");
    setInvoiceDays("");
  };

  // Calculations
  const previewItems = useMemo(() => {
    if (msPartyId === "all" || selectedOutwardIds.length === 0) return [];
    
    return availableOutwards
      .filter((o: any) => selectedOutwardIds.includes(o.id))
      .flatMap((o: any) => o.items.map((item: any) => ({
        ...item,
        outward_no: o.outward_no,
        gp_no: o.gp_no,
        rate: item.measurement === 15 ? rate15 : rate22,
        amount: (item.measurement === 15 ? rate15 : rate22) * item.quantity
      })));
  }, [availableOutwards, selectedOutwardIds, rate15, rate22]);

  const subTotal = previewItems.reduce((sum, item) => sum + item.amount, 0);
  const discountAmount = (subTotal * discountPercent) / 100;
  const totalAmount = subTotal - discountAmount;

  // Edit Calculations
  const editSubTotal = useMemo(() => {
    if (!selectedInvoice) return 0;
    return selectedInvoice.items?.reduce((sum: number, item: any) => {
        const rate = item.measurement === 15 ? editRate15 : editRate22;
        return sum + (rate * item.quantity);
    }, 0) || 0;
  }, [selectedInvoice, editRate15, editRate22]);

  const editDiscountAmount = (editSubTotal * editDiscountPercent) / 100;
  const editTotalAmount = editSubTotal - editDiscountAmount;

  const handleCreateSubmit = () => {
    createMutation.mutate({
      ms_party_id: Number(msPartyId),
      date,
      sub_total: subTotal,
      discount_percent: discountPercent,
      discount_amount: discountAmount,
      total_amount: totalAmount,
      rate_15: rate15,
      rate_22: rate22,
      type,
      cash_account_id: type === 'debit' && cashAccountId ? Number(cashAccountId) : undefined,
      invoice_days: type === 'credit' && invoiceDays ? Number(invoiceDays) : undefined,
      outward_ids: selectedOutwardIds,
      created_by: currentUser.username
    });
  };

  const handleEditOpen = async (id: number) => {
    const data = await invoicesApi.getById(id);
    setSelectedInvoice(data);
    setEditRate15(Number(data.rate_15));
    setEditRate22(Number(data.rate_22));
    setEditDiscountPercent(Number(data.discount_percent));
    setEditType(data.type || 'credit');
    setEditCashAccountId(data.cash_account_id ? String(data.cash_account_id) : "");
    setEditInvoiceDays(data.invoice_days !== null && data.invoice_days !== undefined ? Number(data.invoice_days) : "");
    setIsEditOpen(true);
  };

  const handleEditSubmit = () => {
    updateMutation.mutate({
      id: selectedInvoice.id,
      data: {
        rate_15: editRate15,
        rate_22: editRate22,
        discount_percent: editDiscountPercent,
        sub_total: editSubTotal,
        discount_amount: editDiscountAmount,
        total_amount: editTotalAmount,
        type: editType,
        cash_account_id: editType === 'debit' && editCashAccountId ? Number(editCashAccountId) : null,
        invoice_days: editType === 'credit' && editInvoiceDays ? Number(editInvoiceDays) : null,
        edited_by: currentUser.username
      }
    });
  };

  const handlePrint = async (invoice: any) => {
      const full = await invoicesApi.getById(invoice.id);
      setSelectedInvoicesForPrint([full]);
      setIsPrintOpen(true);
      setTimeout(() => window.print(), 500);
  };

  const handleBulkPrint = async () => {
     if (bulkSelectedIds.length === 0) return;
     const fullInvoices = await Promise.all(
        bulkSelectedIds.map(id => invoicesApi.getById(id))
     );
     setSelectedInvoicesForPrint(fullInvoices);
     setIsPrintOpen(true);
     setTimeout(() => window.print(), 500);
  };

  const toggleSelectAll = () => {
    if (bulkSelectedIds.length === invoices.length) {
      setBulkSelectedIds([]);
    } else {
      setBulkSelectedIds(invoices.map((i: any) => i.id));
    }
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900 p-6 rounded-2xl text-white shadow-xl print:hidden">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-blue-600/20 rounded-xl">
            <Receipt className="h-8 w-8 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Invoice Management</h1>
            <p className="text-slate-400 text-sm mt-1">Generate invoices for party outwards.</p>
          </div>
        </div>
        <div className="flex gap-3">
          {bulkSelectedIds.length > 0 && (
            <Button onClick={handleBulkPrint} className="bg-emerald-600 hover:bg-emerald-700 shadow-lg font-bold">
               <Printer className="h-4 w-4 mr-2" /> Print Selected ({bulkSelectedIds.length})
            </Button>
          )}
          <Button variant="outline" onClick={() => refetch()} className="bg-slate-800 border-slate-700 hover:bg-slate-700">
             <RefreshCw className="h-4 w-4 mr-2" /> Refresh
          </Button>
          <Button onClick={() => setIsCreateOpen(true)} className="bg-blue-600 hover:bg-blue-700 shadow-lg font-bold">
            <Plus className="h-4 w-4 mr-2" /> Add Invoice
          </Button>
        </div>
      </div>

      {/* List Table */}
      <div className="bg-white rounded-2xl shadow-sm border overflow-hidden print:hidden">
        <div className="p-4 border-b bg-slate-50">
           <div className="relative max-w-sm">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
             <Input placeholder="Search invoice or party..." value={search} onChange={e => setSearch(e.target.value)} className="pl-10 h-10 bg-white" />
           </div>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[50px]">
                   <Checkbox checked={bulkSelectedIds.length > 0 && bulkSelectedIds.length === invoices.length} onCheckedChange={toggleSelectAll} />
                </TableHead>
                <TableHead className="whitespace-nowrap">Invoice #</TableHead>
                <TableHead className="whitespace-nowrap">MS Party</TableHead>
                <TableHead className="whitespace-nowrap">Type</TableHead>
                <TableHead className="text-center whitespace-nowrap mobile-hide-column">Items</TableHead>
                <TableHead className="text-right whitespace-nowrap mobile-hide-column">Discount</TableHead>
                <TableHead className="text-right whitespace-nowrap">Amount</TableHead>
                <TableHead className="text-center whitespace-nowrap mobile-hide-column">Date</TableHead>
                <TableHead className="text-center whitespace-nowrap">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                 <TableRow><TableCell colSpan={8} className="text-center py-20 text-slate-400">Loading invoices...</TableCell></TableRow>
              ) : invoices.length === 0 ? (
                 <TableRow><TableCell colSpan={8} className="text-center py-20 text-slate-400">No invoices found.</TableCell></TableRow>
              ) : invoices.map((invoice: any) => (
                <TableRow key={invoice.id} className="group transition-colors hover:bg-slate-50">
                  <TableCell>
                     <Checkbox checked={bulkSelectedIds.includes(invoice.id)} onCheckedChange={() => {
                        setBulkSelectedIds(prev => prev.includes(invoice.id) ? prev.filter(id => id !== invoice.id) : [...prev, invoice.id]);
                     }} />
                  </TableCell>
                  <TableCell className="font-bold">{invoice.invoice_no}</TableCell>
                  <TableCell className="font-medium truncate max-w-[120px]">{invoice.ms_party_name}</TableCell>
                  <TableCell>
                     {invoice.type === 'debit' ? (
                       <span className="bg-red-100 text-red-800 text-[10px] uppercase font-bold py-1 px-2 rounded-md">
                         Debit (Cash)
                       </span>
                     ) : (
                       <span className="bg-emerald-100 text-emerald-800 text-[10px] uppercase font-bold py-1 px-2 rounded-md">
                         Credit {invoice.invoice_days ? `(${invoice.invoice_days} Days)` : ''}
                       </span>
                     )}
                  </TableCell>
                  <TableCell className="text-center mobile-hide-column">{invoice.item_count}</TableCell>
                  <TableCell className="text-right text-orange-600 font-medium mobile-hide-column">{Number(invoice.discount_amount).toLocaleString()}</TableCell>
                  <TableCell className="text-right font-black text-blue-600 sm:text-lg">{Number(invoice.total_amount).toLocaleString()}</TableCell>
                  <TableCell className="text-center text-slate-500 font-medium mobile-hide-column">{format(new Date(invoice.date), 'yyyy-MM-dd')}</TableCell>
                  <TableCell className="text-center">
                     <div className="flex justify-center gap-1 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="icon" onClick={() => handlePrint(invoice)} className="h-8 w-8 text-blue-600">
                          <Printer className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleEditOpen(invoice.id)} className="h-8 w-8 text-emerald-600">
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => confirm('Delete this invoice?') && deleteMutation.mutate(invoice.id)} className="h-8 w-8 text-red-600">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                     </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Wizard and Edit Dialogs (Keeping them همان طور) ... */}
      {/* (Creation Wizard Dialog) */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
           <DialogHeader>
             <DialogTitle className="flex items-center gap-2 text-2xl font-black text-slate-800">
               <Receipt className="h-6 w-6 text-blue-600" />
               Create Invoice - Step {step}
             </DialogTitle>
           </DialogHeader>

           {step === 1 && (
             <div className="space-y-6 py-4">
                <div className="space-y-2">
                   <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">1. Select MS Party</Label>
                   <Popover open={msPartyOpen} onOpenChange={setMsPartyOpen}>
                    <PopoverTrigger asChild>
                      <Button variant="outline" className="w-full justify-between h-12 bg-slate-50 shadow-inner text-left">
                         {msPartyId === "all" ? "Choose MS Party..." : msParties.find(p => String(p.id) === msPartyId)?.name}
                         <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[400px] p-0">
                       <Command>
                         <CommandInput placeholder="Search party..." />
                         <CommandList>
                           <CommandEmpty>No records found.</CommandEmpty>
                           <CommandGroup>
                             {msParties.map((party) => (
                               <CommandItem key={party.id} value={party.name} onSelect={() => { 
                                 setMsPartyId(String(party.id)); 
                                 setRate15(Number(party.rate_15 || 0));
                                 setRate22(Number(party.rate_22 || 0));
                                 setMsPartyOpen(false); 
                               }}>
                                 <Check className={cn("mr-2 h-4 w-4", msPartyId === String(party.id) ? "opacity-100" : "opacity-0")} />
                                 {party.name}
                               </CommandItem>
                             ))}
                           </CommandGroup>
                         </CommandList>
                       </Command>
                    </PopoverContent>
                   </Popover>
                </div>
                <div className="grid grid-cols-2 gap-4 mt-6">
                  <div className="space-y-2">
                    <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">2. Invoice Type</Label>
                    <select 
                      value={type} 
                      onChange={e => setType(e.target.value as 'credit' | 'debit')}
                      className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-slate-50 px-3 py-2 text-sm shadow-inner ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    >
                      <option value="credit">Credit Invoice</option>
                      <option value="debit">Cash / Debit Invoice</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">3. Invoice Date</Label>
                    <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="h-12 bg-slate-50 shadow-inner" />
                  </div>
                </div>

                {type === 'credit' && (
                  <div className="space-y-2 border-t pt-4">
                    <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">Invoice Days (Credit)</Label>
                    <Input type="number" placeholder="Enter days... (e.g. 30)" value={invoiceDays} onChange={e => setInvoiceDays(e.target.value ? parseInt(e.target.value) : '')} className="h-12 bg-slate-50 shadow-inner" />
                  </div>
                )}

                {type === 'debit' && (
                  <div className="space-y-2 border-t pt-4">
                    <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">Receiving Cash Account</Label>
                    <select 
                      value={cashAccountId} 
                      onChange={e => setCashAccountId(e.target.value)}
                      className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-slate-50 px-3 py-2 text-sm shadow-inner ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                    >
                      <option value="">Select Cash Account...</option>
                      {accounts.map((acc: any) => (
                        <option key={acc.id} value={acc.id}>{acc.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div className="flex justify-end pt-6">
                   <Button onClick={() => setStep(2)} disabled={msPartyId === "all" || (type === "debit" && !cashAccountId)} className="px-10 h-12 bg-blue-600 hover:bg-blue-700 shadow-lg font-bold">
                     Next Step <ChevronRight className="ml-2 h-4 w-4" />
                   </Button>
                </div>
             </div>
           )}

           {step === 2 && (
             <div className="space-y-6 py-4">
                <div className="flex justify-between items-center bg-slate-50 p-4 rounded-xl border border-dashed border-slate-300">
                   <div>
                     <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Selected Party</p>
                     <p className="text-lg font-black text-slate-900">{msParties.find(p => String(p.id) === msPartyId)?.name}</p>
                   </div>
                   <Button variant="ghost" size="sm" onClick={() => setStep(1)} className="text-blue-600">Change Party</Button>
                </div>

                <div className="space-y-3">
                   <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">3. Select Outwards Tracking</Label>
                   <div className="border rounded-xl max-h-[300px] overflow-y-auto shadow-inner bg-slate-50/50">
                     <Table>
                       <TableHeader className="bg-white sticky top-0 shadow-sm z-10">
                         <TableRow>
                           <TableHead className="w-[50px]"></TableHead>
                           <TableHead>Outward #</TableHead>
                           <TableHead>GP # / SR #</TableHead>
                           <TableHead>Date</TableHead>
                           <TableHead className="text-right">Total Qty</TableHead>
                         </TableRow>
                       </TableHeader>
                       <TableBody>
                         {isLoadingOutwards ? (
                            <TableRow><TableCell colSpan={5} className="text-center py-10">Searching outwards...</TableCell></TableRow>
                         ) : availableOutwards.length === 0 ? (
                           <TableRow><TableCell colSpan={5} className="text-center py-10 text-slate-400">No pending outwards found for this party.</TableCell></TableRow>
                         ) : availableOutwards.map((o: any) => (
                           <TableRow key={o.id} className="cursor-pointer hover:bg-blue-50/50" onClick={() => {
                             setSelectedOutwardIds(prev => prev.includes(o.id) ? prev.filter(id => id !== o.id) : [...prev, o.id]);
                           }}>
                             <TableCell><Checkbox checked={selectedOutwardIds.includes(o.id)} onCheckedChange={() => {}} /></TableCell>
                             <TableCell className="font-bold">{o.outward_no}</TableCell>
                             <TableCell>{o.gp_no} / {o.sr_no}</TableCell>
                             <TableCell className="text-slate-500 whitespace-nowrap">{format(new Date(o.date), 'dd MMM yyyy')}</TableCell>
                             <TableCell className="text-right font-bold text-slate-900">{o.total_quantity.toLocaleString()}</TableCell>
                           </TableRow>
                         ))}
                       </TableBody>
                     </Table>
                   </div>
                </div>

                <div className="flex justify-between pt-6 border-t font-sans">
                   <Button variant="ghost" onClick={() => setStep(1)}>Back</Button>
                   <Button onClick={() => setStep(3)} disabled={selectedOutwardIds.length === 0} className="px-10 h-10 bg-blue-600 hover:bg-blue-700 shadow-lg font-bold">
                      Step 3: Rates & Finalize <ChevronRight className="ml-2 h-4 w-4" />
                   </Button>
                </div>
             </div>
           )}

           {step === 3 && (
             <div className="space-y-6 py-4">
                <div className="grid grid-cols-2 gap-6 bg-slate-900 p-6 rounded-2xl text-white shadow-xl">
                   <div className="space-y-2">
                     <Label className="text-xs uppercase font-bold tracking-widest text-slate-400">15 MSR Rate</Label>
                     <Input type="number" value={rate15} onChange={e => setRate15(parseFloat(e.target.value) || 0)} className="bg-slate-800 text-white border-slate-700 h-12 text-xl font-bold" />
                   </div>
                   <div className="space-y-2">
                     <Label className="text-xs uppercase font-bold tracking-widest text-slate-400">22 MSR Rate</Label>
                     <Input type="number" value={rate22} onChange={e => setRate22(parseFloat(e.target.value) || 0)} className="bg-slate-800 text-white border-slate-700 h-12 text-xl font-bold" />
                   </div>
                </div>

                <div className="border rounded-2xl overflow-hidden shadow-inner bg-slate-50/50">
                  <Table>
                    <TableHeader className="bg-white">
                      <TableRow>
                        <TableHead>Item / Outward</TableHead>
                        <TableHead className="text-center">Yards</TableHead>
                        <TableHead className="text-right">Quantity</TableHead>
                        <TableHead className="text-right">Rate</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewItems.map((item, idx) => (
                        <TableRow key={idx} className="hover:bg-white transition-colors">
                          <TableCell>
                            <div className="font-bold text-slate-900">{item.item_name}</div>
                            <div className="text-[10px] text-slate-400 uppercase tracking-tighter">OUT: {item.outward_no} | GP: {item.gp_no}</div>
                          </TableCell>
                          <TableCell className="text-center font-bold text-slate-600">{item.measurement}</TableCell>
                          <TableCell className="text-right font-medium">{item.quantity.toLocaleString()}</TableCell>
                          <TableCell className="text-right text-slate-500">{item.rate.toLocaleString()}</TableCell>
                          <TableCell className="text-right font-bold text-slate-800">{item.amount.toLocaleString()}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  <div className="bg-slate-900/5 p-6 space-y-4 border-t-2 border-slate-200">
                     <div className="flex justify-between items-center px-4">
                        <span className="text-sm font-bold text-slate-500 uppercase tracking-widest">Sub Total</span>
                        <span className="text-xl font-black text-slate-900">Rs {subTotal.toLocaleString()}</span>
                     </div>
                     <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-slate-200">
                        <div className="flex items-center gap-2">
                           <Label className="text-sm font-bold text-slate-700">Discount (%)</Label>
                           <Input type="number" value={discountPercent} onChange={e => setDiscountPercent(parseFloat(e.target.value) || 0)} className="w-24 h-10 font-bold border-slate-300" />
                        </div>
                        <span className="text-red-600 font-bold">- Rs {discountAmount.toLocaleString()}</span>
                     </div>
                     <div className="flex justify-between items-center px-4 pt-2">
                        <span className="text-base font-black text-slate-800 uppercase tracking-widest">Final Total</span>
                        <span className="text-3xl font-black text-blue-600">Rs {totalAmount.toLocaleString()}</span>
                     </div>
                  </div>
                </div>

                <div className="flex justify-end pt-6">
                   <Button onClick={handleCreateSubmit} disabled={createMutation.isPending} className="px-12 h-12 bg-emerald-600 hover:bg-emerald-700 shadow-lg font-black text-lg">
                      {createMutation.isPending ? <RefreshCw className="h-5 w-5 animate-spin" /> : "Save & Generate Invoice"}
                   </Button>
                </div>
             </div>
           )}
        </DialogContent>
      </Dialog>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl">
           <DialogHeader>
             <DialogTitle className="flex items-center gap-2 text-2xl font-black text-slate-800 uppercase tracking-tight">
               <Receipt className="h-6 w-6 text-emerald-600" />
               Edit Internal Invoice Values
             </DialogTitle>
             <p className="text-slate-400 text-xs">Modifying invoice rates and discounts for {selectedInvoice?.invoice_no}</p>
           </DialogHeader>

           <div className="space-y-6 py-4">
              <div className="grid grid-cols-2 gap-4">
                 <div className="space-y-2">
                   <Label className="text-xs font-bold text-slate-400 uppercase">Rate 15 MSR</Label>
                   <Input type="number" value={editRate15} onChange={e => setEditRate15(parseFloat(e.target.value) || 0)} className="h-12 text-xl font-black" />
                 </div>
                 <div className="space-y-2">
                   <Label className="text-xs font-bold text-slate-400 uppercase">Rate 22 MSR</Label>
                   <Input type="number" value={editRate22} onChange={e => setEditRate22(parseFloat(e.target.value) || 0)} className="h-12 text-xl font-black" />
                 </div>
              </div>
              <div className="space-y-2">
                 <Label className="text-xs font-bold text-slate-400 uppercase">Discount (%)</Label>
                 <Input type="number" value={editDiscountPercent} onChange={e => setEditDiscountPercent(parseFloat(e.target.value) || 0)} className="h-12 text-xl font-black text-red-600" />
              </div>

              <div className="border-t pt-4 mt-6">
                <Label className="text-sm font-bold text-slate-800 uppercase tracking-tight mb-2 block">Invoice Type & Terms</Label>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                     <Label className="text-xs font-bold text-slate-400 uppercase">Type</Label>
                     <select 
                       value={editType} 
                       onChange={e => setEditType(e.target.value as 'credit' | 'debit')}
                       className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-white px-3 py-2 text-sm shadow-sm"
                     >
                       <option value="credit">Credit</option>
                       <option value="debit">Debit (Cash)</option>
                     </select>
                  </div>
                  {editType === 'credit' ? (
                    <div className="space-y-2">
                       <Label className="text-xs font-bold text-slate-400 uppercase">Invoice Days</Label>
                       <Input type="number" placeholder="none" value={editInvoiceDays} onChange={e => setEditInvoiceDays(e.target.value ? parseInt(e.target.value) : '')} className="h-12 font-bold" />
                    </div>
                  ) : (
                    <div className="space-y-2">
                       <Label className="text-xs font-bold text-slate-400 uppercase">Cash Account</Label>
                       <select 
                         value={editCashAccountId} 
                         onChange={e => setEditCashAccountId(e.target.value)}
                         className="flex h-12 w-full items-center justify-between rounded-md border border-input bg-white px-3 py-2 text-sm shadow-sm"
                       >
                         <option value="">Select Account...</option>
                         {accounts.map((acc: any) => (
                           <option key={acc.id} value={acc.id}>{acc.name}</option>
                         ))}
                       </select>
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-slate-50 p-6 rounded-2xl border flex justify-between items-center shadow-inner mt-4">
                 <div className="space-y-1">
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest leading-none">New Total Amount</p>
                    <p className="text-3xl font-black text-slate-900 leading-none">Rs {editTotalAmount.toLocaleString()}</p>
                 </div>
                 <div className="text-right">
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest leading-none">Reduction</p>
                    <p className="text-lg font-bold text-red-600 leading-none">- Rs {editDiscountAmount.toLocaleString()}</p>
                 </div>
              </div>
           </div>

           <DialogFooter className="pt-4 border-t">
              <Button variant="ghost" onClick={() => setIsEditOpen(false)}>Cancel</Button>
              <Button onClick={handleEditSubmit} disabled={updateMutation.isPending} className="bg-emerald-600 hover:bg-emerald-700 px-10 h-10 font-bold shadow-lg">
                Update Invoice
              </Button>
           </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── PRINT TEMPLATE ─────────────────────────────────────────── */}
      <div id="invoice-print" className="hidden print:block bg-white text-black p-0">
          {selectedInvoicesForPrint.map((invoice, idx) => (
            <div key={invoice.id} className={cn(
               "w-[210mm] min-h-[297mm] mx-auto box-border bg-transparent mb-10 flex flex-col items-center py-4 relative",
               idx < selectedInvoicesForPrint.length - 1 && "page-break-after-always"
            )}>
              <div className="w-[195mm] min-h-[280mm] border-[2px] border-slate-200 rounded-xl relative font-sans box-border flex flex-col bg-white overflow-hidden shadow-sm">
                
                <div className="p-8 flex flex-col flex-1 relative z-10 h-full bg-transparent">
                  {/* Header */}
                  <div className="text-center space-y-4 mb-8">
                     <h1 className="text-3xl font-black tracking-tighter text-blue-900 uppercase pt-2">
                       Momina lace Dyeing & Universal Dyeing
                     </h1>
                     <div className="space-y-1">
                        <p className="text-sm font-bold text-slate-800 uppercase tracking-widest">
                          GHULAM MUSTAFA <span className="text-slate-300 mx-2">|</span> Shahid, Naveed
                        </p>
                        <div className="text-xs font-bold text-slate-600 tracking-wider flex justify-center gap-4 flex-wrap mt-2">
                          <span className="text-slate-400">Contact #:</span>
                          <span>0321-7651815</span>
                          <span>0300-8651815</span>
                          <span>0304-6166663</span>
                          <span>0300-5479191</span>
                        </div>
                     </div>
                     <div className="mt-4">
                       <h2 className="inline-block text-xl font-black bg-blue-50 border-2 border-blue-600 text-blue-800 px-8 py-1 rounded-full uppercase shadow-sm tracking-widest">
                         INVOICE
                       </h2>
                     </div>
                  </div>

                  {/* Meta Bar */}
                  <div className="flex justify-between items-center bg-blue-50/80 border-y-2 border-blue-600 py-3 px-8 mb-8 rounded-sm">
                     <div className="space-y-1">
                        <div className="text-[10px] font-black text-blue-800 uppercase tracking-wider">Invoice #</div>
                        <div className="text-sm font-bold text-slate-900">{invoice.invoice_no}</div>
                     </div>
                     <div className="space-y-1 text-center">
                        <div className="text-[10px] font-black text-blue-800 uppercase tracking-wider">MS Party</div>
                        <div className="text-lg font-black text-slate-900 uppercase">{invoice.ms_party_name}</div>
                     </div>
                     <div className="space-y-1 text-right">
                        <div className="text-[10px] font-black text-blue-800 uppercase tracking-wider">Date</div>
                        <div className="text-sm font-bold text-slate-900">
                          {invoice.date ? format(new Date(invoice.date), 'dd MMM yyyy') : ''}
                        </div>
                     </div>
                  </div>

                  {/* Items Table */}
                  <div className="w-full mb-8 flex-1">
                    <div className="border-2 border-slate-200 rounded-lg overflow-hidden bg-white shadow-sm">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-[#f0f4f8] border-b-2 border-slate-300">
                               <tr className="[&>th]:p-3 [&>th]:text-[11px] [&>th]:font-black [&>th]:text-slate-700 [&>th]:uppercase [&>th]:tracking-wider [&>th]:border-r last:[&>th]:border-0 border-slate-200">
                                  <th className="text-center w-20">Qty</th>
                                  <th>Detail</th>
                                  <th className="text-right w-24">Rate</th>
                                  <th className="text-right w-32">Amount</th>
                               </tr>
                            </thead>
                            <tbody className="text-slate-800">
                               {invoice.items?.map((item: any, i: number) => {
                                 const rate = Number(item.measurement === 15 ? invoice.rate_15 : invoice.rate_22);
                                 const outDate = item.outward_date ? format(new Date(item.outward_date), 'dd-MM-yyyy') : '';
                                 return (
                                   <tr key={i} className="border-b border-slate-100 last:border-0 [&>td]:p-3 [&>td]:text-xs [&>td]:font-bold [&>td]:border-r [&>td]:border-slate-100 last:[&>td]:border-0">
                                      <td className="text-center text-sm">{Number(item.quantity).toFixed(2)}</td>
                                      <td>
                                        <div className="text-sm font-black text-slate-900 mb-0.5">{item.item_name}</div>
                                        <div className="text-[10px] text-slate-500 uppercase tracking-wide flex flex-wrap gap-x-3 gap-y-1 items-center">
                                          <span><strong className="text-slate-700">MSR:</strong> {item.measurement}</span>
                                          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                                          <span><strong className="text-slate-700">OUTWARD #:</strong> {item.outward_no}</span>
                                          {outDate && (
                                            <>
                                              <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                                              <span><strong className="text-slate-700">DATE:</strong> {outDate}</span>
                                            </>
                                          )}
                                        </div>
                                      </td>
                                      <td className="text-right">{rate.toFixed(2)}</td>
                                      <td className="text-right font-black text-sm">{Number(item.quantity * rate).toFixed(2)}</td>
                                   </tr>
                                 );
                               })}
                            </tbody>
                        </table>
                    </div>
                  </div>

                  {/* Bottom Totals */}
                  <div className="flex justify-end mb-16 w-full">
                    <div className="w-[320px] border-2 border-slate-200 rounded-lg overflow-hidden shadow-sm bg-white">
                       <div className="p-2 border-b border-slate-100 flex justify-between items-center px-4 bg-slate-50/50">
                          <span className="text-[10px] font-black text-slate-500 uppercase tracking-wider flex-1">Sub Total</span>
                          <span className="text-sm font-black text-slate-800">{Number(invoice.sub_total).toFixed(2)}</span>
                       </div>
                       {Number(invoice.discount_amount) > 0 && (
                         <div className="p-2 border-b border-slate-100 flex justify-between items-center px-4 bg-red-50/10">
                            <span className="text-[10px] font-black text-red-400 uppercase tracking-wider flex-1">Discount</span>
                            <span className="text-sm font-black text-red-600">-{Number(invoice.discount_amount).toFixed(2)}</span>
                         </div>
                       )}
                       <div className="p-3 bg-[#eef2f6] flex justify-between items-center px-4 border-t border-slate-200">
                          <span className="text-sm font-black text-blue-900 uppercase tracking-widest flex-1">Total Amount</span>
                          <span className="text-xl font-black text-blue-700">{Number(invoice.total_amount).toFixed(2)}</span>
                       </div>
                    </div>
                  </div>

                  {/* Footer */}
                  <div className="mt-auto page-break-inside-avoid w-full">
                      {/* Signatures */}
                      <div className="flex justify-between items-end mb-8 px-4">
                         <div className="text-center w-48">
                            <div className="border-t border-slate-400 mb-2"></div>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Customer Signature</p>
                         </div>
                         <div className="text-center w-48">
                            <div className="border-t border-slate-400 mb-2"></div>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Authorized Signature</p>
                         </div>
                      </div>
                      
                      {/* Created/Edited By */}
                      <div className="flex justify-between items-center text-[9px] font-bold text-slate-400 uppercase mb-4 px-2">
                         <p>Created By: <span className="text-slate-700 ml-1">{invoice.created_by || 'Mehmood'}</span></p>
                         <p>Edited By: <span className="text-slate-700 ml-1">{invoice.edited_by || 'None'}</span></p>
                      </div>
                  </div>
                </div>

                {/* Bottom Address Box */}
                <div className="bg-slate-900 text-white p-4 relative z-10 w-full mt-auto">
                   <p className="text-[10.5px] font-black uppercase text-center tracking-widest text-slate-400">
                      Address: <span className="text-white font-medium ml-2">Punjab Small Industries Estate, Ground Floor, Faisalabad</span>
                   </p>
                   <p className="text-[10.5px] font-black uppercase text-center tracking-widest text-slate-400 mt-2">
                      Branches: <span className="text-white font-medium ml-2">100/2 and 150/2, quality yarn</span>
                   </p>
                </div>

                {/* Background Watermark Layer (Now on top of everything) */}
                <div className="absolute inset-0 z-50 flex items-center justify-center opacity-[0.05] pointer-events-none select-none">
                   <img src="/logo.png" className="w-[80%] max-w-[500px] object-contain" alt="Watermark" />
                </div>

              </div>
            </div>
          ))}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @media print {
          body * { visibility: hidden; }
          #invoice-print, #invoice-print * { 
            visibility: visible; 
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          #invoice-print { position: absolute; left: 0; top: 0; width: 100%; border: none; }
          .page-break-after-always { page-break-after: always; display: block; }
          .page-break-inside-avoid { page-break-inside: avoid; }
          @page { margin: 0; size: A4 portrait; }
        }
      `}} />

    </div>
  );
}
