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
import { invoicesApi, msPartiesApi, type Invoice } from "@/lib/api-client";

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

  // Form State for Creation
  const [step, setStep] = useState(1);
  const [msPartyId, setMsPartyId] = useState<string>("all");
  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [selectedOutwardIds, setSelectedOutwardIds] = useState<number[]>([]);
  const [rate15, setRate15] = useState(0);
  const [rate22, setRate22] = useState(0);
  const [discountPercent, setDiscountPercent] = useState(0);
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'));

  // Edit State
  const [selectedInvoice, setSelectedInvoice] = useState<any>(null);
  const [editRate15, setEditRate15] = useState(0);
  const [editRate22, setEditRate22] = useState(0);
  const [editDiscountPercent, setEditDiscountPercent] = useState(0);

  // Queries
  const { data: invoices = [], isLoading, refetch } = useQuery({
    queryKey: ["invoices", search],
    queryFn: () => invoicesApi.list(search),
  });

  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
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
      outward_ids: selectedOutwardIds,
      created_by: 'Momin'
    });
  };

  const handleEditOpen = async (id: number) => {
    const data = await invoicesApi.getById(id);
    setSelectedInvoice(data);
    setEditRate15(Number(data.rate_15));
    setEditRate22(Number(data.rate_22));
    setEditDiscountPercent(Number(data.discount_percent));
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
        edited_by: 'Momin'
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
        <div className="p-4 border-b bg-slate-50 flex items-center gap-4">
           <div className="relative flex-1 max-w-sm">
             <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
             <Input placeholder="Search invoice or party..." value={search} onChange={e => setSearch(e.target.value)} className="pl-10 h-10 bg-white" />
           </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">
                 <Checkbox checked={bulkSelectedIds.length > 0 && bulkSelectedIds.length === invoices.length} onCheckedChange={toggleSelectAll} />
              </TableHead>
              <TableHead>Invoice #</TableHead>
              <TableHead>MS Party</TableHead>
              <TableHead className="text-center">No. of Items</TableHead>
              <TableHead className="text-right">Discount</TableHead>
              <TableHead className="text-right">Total Amount</TableHead>
              <TableHead className="text-center">Date</TableHead>
              <TableHead className="text-center">Actions</TableHead>
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
                <TableCell className="font-medium">{invoice.ms_party_name}</TableCell>
                <TableCell className="text-center">{invoice.item_count}</TableCell>
                <TableCell className="text-right text-orange-600 font-medium">{Number(invoice.discount_amount).toLocaleString()}</TableCell>
                <TableCell className="text-right font-black text-blue-600 text-lg">{Number(invoice.total_amount).toLocaleString()}</TableCell>
                <TableCell className="text-center text-slate-500 font-medium">{format(new Date(invoice.date), 'yyyy-MM-dd')}</TableCell>
                <TableCell className="text-center">
                   <div className="flex justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
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
                               <CommandItem key={party.id} value={party.name} onSelect={() => { setMsPartyId(String(party.id)); setMsPartyOpen(false); }}>
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
                <div className="space-y-2">
                   <Label className="text-sm font-bold uppercase tracking-widest text-slate-500">2. Invoice Date</Label>
                   <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="h-12 bg-slate-50" />
                </div>
                <div className="flex justify-end pt-6">
                   <Button onClick={() => setStep(2)} disabled={msPartyId === "all"} className="px-10 h-12 bg-blue-600 hover:bg-blue-700 shadow-lg font-bold">
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

              <div className="bg-slate-50 p-6 rounded-2xl border flex justify-between items-center shadow-inner">
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
               "w-[210mm] mx-auto box-border bg-white mb-20",
               idx < selectedInvoicesForPrint.length - 1 && "page-break-after-always"
            )}>
              <div className="w-[195mm] mx-auto border-[4px] border-blue-600 rounded-xl p-8 relative font-sans box-border flex flex-col">
                {/* Logo Area */}
                <div className="absolute top-12 right-12 w-32 h-32 opacity-90 rotate-12">
                   <img src="/logo.png" className="w-full" />
                </div>

                {/* Header */}
                <div className="text-center space-y-4 mb-10 relative z-10">
                   <h1 className="text-4xl font-black tracking-tighter text-blue-700 uppercase">MOMINA LACE DYEING</h1>
                   <div className="space-y-0.5">
                      <p className="text-xs font-bold text-slate-600 uppercase tracking-widest">Owner: GHULAM MUSTAFA</p>
                      <p className="text-xs font-medium text-slate-500 uppercase tracking-widest">GM : Shahid, Naveed</p>
                   </div>
                   <h2 className="inline-block text-xl font-black border-b-2 border-red-600 text-red-600 px-6 py-0.5 mx-auto uppercase mt-2">INVOICE</h2>
                </div>

                {/* Meta Grid */}
                <div className="grid grid-cols-2 gap-x-20 mb-8 px-10">
                   <div className="space-y-2">
                      <div className="grid grid-cols-[100px_1fr] items-center">
                         <span className="text-[10px] font-black text-blue-700 uppercase">Invoice #:</span>
                         <span className="text-sm font-bold border-b border-slate-900 pb-0.5">{invoice.invoice_no}</span>
                      </div>
                      <div className="grid grid-cols-[100px_1fr] items-center">
                         <span className="text-[10px] font-black text-blue-700 uppercase">MS Party:</span>
                         <span className="text-sm font-bold border-b border-slate-900 pb-0.5">{invoice.ms_party_name}</span>
                      </div>
                      <div className="grid grid-cols-[100px_1fr] items-center">
                         <span className="text-[10px] font-black text-blue-700 uppercase">Date:</span>
                         <span className="text-sm font-bold border-b border-slate-900 pb-0.5">
                           {invoice.date ? format(new Date(invoice.date), 'yyyy-MM-dd') : ''}
                         </span>
                      </div>
                   </div>
                   <div className="space-y-2">
                      <div className="grid grid-cols-[100px_1fr] items-center">
                         <span className="text-[10px] font-black text-blue-700 uppercase">Created By:</span>
                         <span className="text-sm font-bold border-b border-slate-900 pb-0.5">{invoice.created_by || 'momin'}</span>
                      </div>
                      <div className="grid grid-cols-[100px_1fr] items-center">
                         <span className="text-[10px] font-black text-blue-700 uppercase">Edited By:</span>
                         <span className="text-sm font-bold border-b border-slate-900 pb-0.5">{invoice.edited_by || 'None'}</span>
                      </div>
                   </div>
                </div>

                {/* Items Table */}
                <div className="w-full px-4 mb-16">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4 italic">Outward Documents Information</p>
                  <div className="border border-green-700 rounded-sm overflow-hidden bg-white">
                      <table className="w-full text-left border-collapse">
                          <thead className="bg-[#f0f9f1] border-b border-green-700">
                             <tr className="[&>th]:p-3 [&>th]:text-[10px] [&>th]:font-black [&>th]:text-slate-500 [&>th]:uppercase [&>th]:tracking-tight [&>th]:border-r [&>th]:border-green-700 last:[&>th]:border-0">
                                <th>Outward#/Transfer#</th>
                                <th className="text-center">GP #</th>
                                <th>Item Name</th>
                                <th className="text-center">Yards</th>
                                <th className="text-right">Quantity</th>
                                <th className="text-right">Rate</th>
                                <th className="text-right">Amount</th>
                             </tr>
                          </thead>
                          <tbody>
                             {invoice.items?.map((item: any, i: number) => (
                               <tr key={i} className="border-b border-slate-100 last:border-0 [&>td]:p-3 [&>td]:text-xs [&>td]:font-bold [&>td]:border-r [&>td]:border-slate-100 last:[&>td]:border-0">
                                  <td>{item.outward_no}</td>
                                  <td className="text-center">{item.gp_no}</td>
                                  <td>{item.item_name}</td>
                                  <td className="text-center underline underline-offset-4 decoration-slate-300">{item.measurement}</td>
                                  <td className="text-right">{Number(item.quantity).toFixed(2)}</td>
                                  <td className="text-right">{Number(item.measurement === 15 ? invoice.rate_15 : invoice.rate_22).toFixed(2)}</td>
                                  <td className="text-right font-black">{Number(item.quantity * (item.measurement === 15 ? invoice.rate_15 : invoice.rate_22)).toFixed(2)}</td>
                               </tr>
                             ))}
                          </tbody>
                      </table>
                  </div>
                </div>

                {/* Bottom Totals */}
                <div className="w-[400px] ml-auto border-2 border-amber-400 rounded-lg overflow-hidden mb-16 shadow-sm bg-white">
                   <div className="p-3 border-b border-amber-200 flex justify-between items-center px-6">
                      <span className="text-[10px] font-black text-slate-500 uppercase">Sub Total:</span>
                      <span className="text-sm font-black text-blue-700">{Number(invoice.sub_total).toFixed(2)}</span>
                   </div>
                   <div className="p-3 border-b-4 border-red-600 flex justify-between items-center px-6">
                      <span className="text-[10px] font-black text-slate-500 uppercase">Discount:</span>
                      <span className="text-sm font-black text-blue-700">{Number(invoice.discount_amount).toFixed(2)}</span>
                   </div>
                   <div className="p-4 bg-white flex justify-between items-center px-6">
                      <span className="text-sm font-black text-slate-800 uppercase tracking-widest">Total Amount:</span>
                      <span className="text-xl font-black text-blue-700">{Number(invoice.total_amount).toFixed(2)}</span>
                   </div>
                </div>

                {/* Footer */}
                <div className="mt-8 pt-4 border-t border-slate-100 space-y-1 page-break-inside-avoid">
                    <p className="text-[9px] font-black text-blue-800 uppercase">SITE: <span className="text-slate-500 font-medium">Small Industrial State, Sargodha Road, Faisalabad</span></p>
                    <p className="text-[9px] font-black text-blue-800 uppercase">CONTACTS: <span className="text-slate-500 font-medium">0321-7651815, 0300-8651815, 0304-6166663, 0300-8636129</span></p>
                </div>
              </div>
            </div>
          ))}
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @media print {
          body * { visibility: hidden; }
          #invoice-print, #invoice-print * { visibility: visible; }
          #invoice-print { position: absolute; left: 0; top: 0; width: 100%; border: none; }
          .page-break-after-always { page-break-after: always; display: block; }
          .page-break-inside-avoid { page-break-inside: avoid; }
          @page { margin: 0; size: A4; }
        }
      `}} />

    </div>
  );
}
