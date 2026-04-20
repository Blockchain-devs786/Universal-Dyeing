import { useState, useMemo, Fragment } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowUpFromLine, ArrowDownToLine, Plus, Search, Trash2, Pencil, Check, ChevronsUpDown, Printer, ChevronRight, ChevronDown, Package } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  outwardsApi,
  msPartiesApi,
  fromPartiesApi,
  itemsApi,
  reportsApi,
  outwardPartiesApi,
  fifoApi,
  type Outward,
  type OutwardItem,
  type OutwardDeductionDetail,
} from "@/lib/api-client";

import { generateAndPrintHTML } from "@/lib/printGenerator";

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
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { cn } from "@/lib/utils";

export default function OutwardPage() {
  const queryClient = useQueryClient();
  
  // Get current user
  const currentUser = useMemo(() => {
    const userStr = localStorage.getItem("user");
    return userStr ? JSON.parse(userStr) : { username: 'System' };
  }, []);

  // Filters State
  const [filterMsPartyId, setFilterMsPartyId] = useState<string>("all");
  const [filterOutwardNo, setFilterOutwardNo] = useState("");
  const [filterGpNo, setFilterGpNo] = useState("");
  const [filterFromDate, setFilterFromDate] = useState("");
  const [filterToDate, setFilterToDate] = useState("");

  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [isPrinting, setIsPrinting] = useState(false);

  const [isPartyDialogOpen, setIsPartyDialogOpen] = useState(false);
  const [isFormDialogOpen, setIsFormDialogOpen] = useState(false);
  
  const [editingOutward, setEditingOutward] = useState<Outward | null>(null);

  // Combobox popover states
  const [partySelectOpen, setPartySelectOpen] = useState(false);
  const [fromPartyOpen, setFromPartyOpen] = useState(false);
  const [outwardToGroupOpen, setOutwardToGroupOpen] = useState(false);
  const [filterMsPartyOpen, setFilterMsPartyOpen] = useState(false);

  // Form State
  const [selectedPartyIdForNew, setSelectedPartyIdForNew] = useState<string>("");
  const [formData, setFormData] = useState({
    ms_party_id: "",
    from_party_id: "",
    outward_to_party_id: "",
    outward_to_party_name: "",
    vehicle_no: "",
    driver_name: "",
    date: format(new Date(), "yyyy-MM-dd"),
    items: [] as OutwardItem[],
  });

  // Queries
  const { data: outwards = [], isLoading } = useQuery({
    queryKey: [
      "outwards",
      filterMsPartyId,
      filterOutwardNo,
      filterGpNo,
      filterFromDate,
      filterToDate,
    ],
    queryFn: () =>
      outwardsApi.list({
        ms_party_id: filterMsPartyId !== "all" ? Number(filterMsPartyId) : undefined,
        outward_no: filterOutwardNo || undefined,
        gp_no: filterGpNo || undefined,
        from_date: filterFromDate || undefined,
        to_date: filterToDate || undefined,
      }),
  });

  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
  });

  const { data: fromParties = [] } = useQuery({
    queryKey: ["from_parties"],
    queryFn: () => fromPartiesApi.list(),
  });

  const { data: items = [] } = useQuery({
    queryKey: ["items"],
    queryFn: () => itemsApi.list(),
  });

  const { data: outwardParties = [] } = useQuery({
    queryKey: ["outward_parties"],
    queryFn: () => outwardPartiesApi.list(),
  });

  const { data: stocks = [] } = useQuery({
    queryKey: ["reports_stock"],
    queryFn: () => reportsApi.getStock("all", "all"),
  });

  const msPartiesWithStock = useMemo(() => {
    // Filter MS parties that actually have some remaining stock in any item
    const partiesWithStockIds = new Set(stocks.filter(s => (s.remaining || 0) > 0).map(s => s.ms_party_id));
    return msParties.filter(p => p.status === 'active' && partiesWithStockIds.has(p.id));
  }, [msParties, stocks]);

  const groupedOutwards = useMemo(() => {
    const groups: Record<number, { partyId: number; partyName: string; items: typeof outwards }> = {};
    outwards.forEach(outward => {
      const partyId = outward.ms_party_id;
      if (!groups[partyId]) {
        groups[partyId] = { 
          partyId,
          partyName: outward.ms_party_name || "Unknown Party", 
          items: [] 
        };
      }
      groups[partyId].items.push(outward);
    });
    return Object.values(groups).sort((a, b) => a.partyName.localeCompare(b.partyName));
  }, [outwards]);

  const currentPartyId = editingOutward ? String(editingOutward.ms_party_id) : formData.ms_party_id;
  const currentPartyStocks = useMemo(() => {
    return stocks.filter(s => String(s.ms_party_id) === currentPartyId);
  }, [stocks, currentPartyId]);

  const { data: fifoDeductions = {} } = useQuery({
    queryKey: ["fifo_deductions_by_party", filterMsPartyId],
    queryFn: () => fifoApi.getOutwardDeductionsByParty(
      filterMsPartyId !== "all" ? Number(filterMsPartyId) : undefined
    ),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: Omit<Outward, "id" | "outward_no" | "gp_no" | "sr_no" | "created_at" | "updated_at">) =>
      outwardsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outwards"] });
      queryClient.invalidateQueries({ queryKey: ["outward_parties"] });
      queryClient.invalidateQueries({ queryKey: ["reports_stock"] });
      queryClient.invalidateQueries({ queryKey: ["fifo_breakdowns"] });
      toast.success("Outward entry created successfully");
      setIsFormDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Outward> }) =>
      outwardsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outwards"] });
      queryClient.invalidateQueries({ queryKey: ["reports_stock"] });
      queryClient.invalidateQueries({ queryKey: ["fifo_breakdowns"] });
      toast.success("Outward entry updated successfully");
      setIsFormDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => outwardsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outwards"] });
      queryClient.invalidateQueries({ queryKey: ["reports_stock"] });
      queryClient.invalidateQueries({ queryKey: ["fifo_breakdowns"] });
      toast.success("Outward entry deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const handlePrintSelected = async () => {
    if (selectedRows.size === 0) return;
    const includeRefs = window.confirm("Include Inward FIFO references in the print layout?");
    setIsPrinting(true);
    try {
      const documentsToPrint = [];
      for (const id of Array.from(selectedRows)) {
        const fullDoc = await outwardsApi.getById(id);
        if (!includeRefs) fullDoc.deductions = [];
        documentsToPrint.push(fullDoc);
      }
      generateAndPrintHTML('outward', documentsToPrint);
      setSelectedRows(new Set());
    } catch (err) {
      toast.error("Failed to generate print document");
    } finally {
      setIsPrinting(false);
    }
  };

  const handlePrintSingle = async (id: number) => {
    const includeRefs = window.confirm("Include Inward FIFO references in the print layout?");
    setIsPrinting(true);
    try {
      const fullDoc = await outwardsApi.getById(id);
      if (!includeRefs) fullDoc.deductions = [];
      generateAndPrintHTML('outward', [fullDoc]);
    } catch (err) {
      toast.error("Failed to generate print document");
    } finally {
      setIsPrinting(false);
    }
  };


  const handleOpenPartySelection = () => {
    setSelectedPartyIdForNew("");
    setIsPartyDialogOpen(true);
  };

  const handleProceedToForm = () => {
    if (!selectedPartyIdForNew) return toast.error("Please select an MS Party first");
    const defaultFromParty = fromParties.find((p: any) => p.is_default);
    
    setEditingOutward(null);
    setFormData({
      ms_party_id: selectedPartyIdForNew,
      from_party_id: defaultFromParty ? String(defaultFromParty.id) : "",
      outward_to_party_id: "",
      outward_to_party_name: "",
      vehicle_no: "",
      driver_name: "",
      date: format(new Date(), "yyyy-MM-dd"),
      items: [{ id: 0, outward_id: 0, item_id: 0, measurement: 15, quantity: 0 }],
    });
    setIsPartyDialogOpen(false);
    setIsFormDialogOpen(true);
  };

  const handleOpenEdit = async (id: number) => {
    try {
      const data = await outwardsApi.getById(id);
      setEditingOutward(data);
      setFormData({
        ms_party_id: String(data.ms_party_id),
        from_party_id: String(data.from_party_id),
        outward_to_party_id: String(data.outward_to_party_id),
        outward_to_party_name: data.outward_to_party_name || "",
        vehicle_no: data.vehicle_no || "",
        driver_name: data.driver_name || "",
        date: data.date ? data.date.substring(0, 10) : format(new Date(), "yyyy-MM-dd"),
        items: data.items || [],
      });
      setIsFormDialogOpen(true);
    } catch (err: any) {
      toast.error("Failed to fetch outward details");
    }
  };

  const handleAddItem = () => {
    setFormData({
      ...formData,
      items: [
        ...formData.items,
        { id: 0, outward_id: 0, item_id: 0, measurement: 15, quantity: 0 },
      ],
    });
  };

  const handleRemoveItem = (index: number) => {
    const newItems = [...formData.items];
    newItems.splice(index, 1);
    setFormData({ ...formData, items: newItems });
  };

  const handleItemChange = (index: number, field: keyof OutwardItem, value: any) => {
    const newItems = formData.items.map((item, i) => {
      if (i !== index) return item;
      const updated = { ...item, [field]: value };
      if (field === 'item_id' || field === 'measurement') {
        updated.quantity = 0;
      }
      return updated;
    });
    setFormData({ ...formData, items: newItems });
  };

  const getAvailableStock = (itemId: number, measurement: number, currentFormQty: number = 0) => {
    const stockRec = currentPartyStocks.find(s => s.item_id === itemId && s.msr === measurement);
    let maxPool = stockRec ? Number(stockRec.remaining) : 0;
    
    // When editing, add back the original outward qty since remaining already has it deducted
    if (editingOutward && editingOutward.items) {
      const originalItem = editingOutward.items.find(i => i.item_id === itemId && i.measurement === measurement);
      if (originalItem) {
        maxPool += Number(originalItem.quantity);
      }
    }
    // Subtract the current form quantity to show dynamic available
    return maxPool - Number(currentFormQty);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.ms_party_id) return toast.error("MS Party is required");
    if (!formData.from_party_id) return toast.error("From Party is required");
    if (!formData.outward_to_party_id && !formData.outward_to_party_name) return toast.error("Outward To Party is required");
    if (!formData.date) return toast.error("Date is required");
    if (formData.items.length === 0) return toast.error("At least one item is required");

    const seenItems = new Set();

    for (let i = 0; i < formData.items.length; i++) {
      const item = formData.items[i];
      if (!item.item_id) return toast.error(`Item name is required for row ${i + 1}`);
      const available = getAvailableStock(item.item_id, item.measurement, item.quantity);
      if (item.quantity <= 0 && available <= 0) {
        return toast.error(`Row ${i + 1}: Both quantity and available stock are 0. Remove this row or select a different item.`);
      }
      if (item.quantity <= 0) return toast.error(`Quantity must be greater than 0 for row ${i + 1}`);
      if (available < 0) {
        return toast.error(`Row ${i + 1}: Outward quantity (${item.quantity}) exceeds available stock.`);
      }

      const key = `${item.item_id}-${item.measurement}`;
      if (seenItems.has(key)) {
        return toast.error(`Conflict: Row ${i + 1} uses the same Item + Measurement combination as another row.`);
      }
      seenItems.add(key);
    }

    const payload = {
      ms_party_id: Number(formData.ms_party_id),
      from_party_id: Number(formData.from_party_id),
      outward_to_party_id: formData.outward_to_party_id ? Number(formData.outward_to_party_id) : undefined,
      outward_to_party_name: !formData.outward_to_party_id ? formData.outward_to_party_name : undefined,
      vehicle_no: formData.vehicle_no,
      driver_name: formData.driver_name,
      date: formData.date,
      reference: formData.reference,
      inward_id: formData.inward_id,
      inward_sr_no: formData.inward_sr_no,
      inward_gp_no: formData.inward_gp_no,
      inward_ms_party_gp_no: formData.inward_ms_party_gp_no,
      created_by: currentUser.username,
      status: "active",
      items: formData.items.map(item => ({
        item_id: Number(item.item_id),
        measurement: item.measurement,
        quantity: Number(item.quantity)
      })) as Omit<OutwardItem, "id" | "outward_id">[] as any
    };

    if (editingOutward) {
      updateMutation.mutate({ id: editingOutward.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const totalQuantity = formData.items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
  
  const filterMsPartyObj = msParties.find(p => String(p.id) === filterMsPartyId);
  const selectedFromPartyObj = fromParties.find(p => String(p.id) === formData.from_party_id);
  const selectedOutwardToPartyObj = outwardParties.find(p => String(p.id) === formData.outward_to_party_id);

  // Derive unique items and measurements available for current MS party
  const availableItems = useMemo(() => {
    const itemIds = new Set(currentPartyStocks.filter(s => s.remaining > 0 || editingOutward).map(s => s.item_id));
    return items.filter(it => 
      (it.status === 'active' && itemIds.has(it.id)) || 
      formData.items.some(fi => fi.item_id === it.id)
    );
  }, [items, currentPartyStocks, editingOutward, formData.items]);

  
  const toggleSelectAll = () => {
    if (selectedRows.size === outwards.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(outwards.map(i => i.id!)));
    }
  };

  const toggleSelectRow = (id: number) => {
    const newSet = new Set(selectedRows);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedRows(newSet);
  };

  const toggleExpandRow = (id: number) => {
    const newSet = new Set(expandedRows);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setExpandedRows(newSet);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <ArrowUpFromLine className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Outward Entries</h1>
            <p className="text-white/80 mt-1">Manage processing dispatches and outward slips.</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {selectedRows.size > 0 && (
            <Button onClick={handlePrintSelected} disabled={isPrinting} className="bg-white/20 hover:bg-white/30 text-white border-0 shadow-sm backdrop-blur-sm transition-all duration-300 rounded-xl">
              <Printer className="mr-2 h-4 w-4" /> Print Selected ({selectedRows.size})
            </Button>
          )}
          <Button onClick={handleOpenPartySelection} className="bg-white hover:bg-white/90 text-primary shadow-md transition-all">
            <Plus className="mr-2 h-4 w-4" /> Add Outward
          </Button>
        </div>
      </div>

      {/* Filters Section */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-border/50 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">MS Party</Label>
          <Popover open={filterMsPartyOpen} onOpenChange={setFilterMsPartyOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={filterMsPartyOpen}
                className="w-full justify-between font-normal text-left h-9 px-3"
              >
                <div className="flex items-center gap-2 overflow-hidden text-ellipsis whitespace-nowrap">
                  <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span>{filterMsPartyId === "all" ? "All MS Parties" : filterMsPartyObj?.name || "Select Party..."}</span>
                </div>
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[300px] p-0" align="start">
              <Command>
                <CommandInput placeholder="Search MS Party..." />
                <CommandList>
                  <CommandEmpty>No party found.</CommandEmpty>
                  <CommandGroup>
                    <CommandItem
                      value="all"
                      onSelect={() => {
                        setFilterMsPartyId("all");
                        setFilterMsPartyOpen(false);
                      }}
                    >
                      <Check className={cn("mr-2 h-4 w-4", filterMsPartyId === "all" ? "opacity-100" : "opacity-0")} />
                      All MS Parties
                    </CommandItem>
                    {msParties.map((party) => (
                      <CommandItem
                        key={party.id}
                        value={party.name}
                        onSelect={() => {
                          setFilterMsPartyId(String(party.id));
                          setFilterMsPartyOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            filterMsPartyId === String(party.id) ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {party.name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Outward No</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Filter by outward no..."
              value={filterOutwardNo}
              onChange={(e) => setFilterOutwardNo(e.target.value)}
              className="pl-9 h-9"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">GP No</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Filter by GP no..."
              value={filterGpNo}
              onChange={(e) => setFilterGpNo(e.target.value)}
              className="pl-9 h-9"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">From Date</Label>
          <Input
            type="date"
            value={filterFromDate}
            onChange={(e) => setFilterFromDate(e.target.value)}
            className="h-9"
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">To Date</Label>
          <Input
            type="date"
            value={filterToDate}
            onChange={(e) => setFilterToDate(e.target.value)}
            className="h-9"
          />
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white shadow-sm rounded-xl overflow-hidden border">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-muted/30">
              <TableRow>
                <TableHead className="w-[50px]">
                  <input 
                    type="checkbox" 
                    checked={outwards.length > 0 && selectedRows.size === outwards.length}
                    onChange={toggleSelectAll}
                    className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4 ml-2 cursor-pointer"
                  />
                </TableHead>
                <TableHead className="whitespace-nowrap">Date</TableHead>
                <TableHead className="whitespace-nowrap">Outward No</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">GP No</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">Sr No</TableHead>
                <TableHead className="whitespace-nowrap">From</TableHead>
                <TableHead className="whitespace-nowrap">Reference</TableHead>
                <TableHead className="whitespace-nowrap">Outward To</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">Vehicle</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">Driver</TableHead>
                <TableHead className="text-right whitespace-nowrap">Total Qty</TableHead>
                <TableHead className="text-center w-28 whitespace-nowrap">Actions</TableHead>
              </TableRow>
            </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center py-10 text-muted-foreground">Loading outward entries...</TableCell>
              </TableRow>
            ) : groupedOutwards.length === 0 ? (
              <TableRow>
                <TableCell colSpan={13} className="text-center py-12 text-muted-foreground">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <ArrowUpFromLine className="h-8 w-8 text-muted-foreground/40" />
                    <span>No outward entries found.</span>
                  </div>
                </TableCell>
              </TableRow>
              ) : (
                groupedOutwards.map((group) => (
                  <Fragment key={group.partyId}>
                    <TableRow className="bg-slate-50/80 hover:bg-slate-50/80 border-y shadow-sm">
                      <TableCell colSpan={13} className="py-2.5 px-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                             <div className="h-5 w-1 rounded-full bg-blue-600" />
                             <span className="text-sm font-bold text-slate-900 uppercase tracking-tight">{group.partyName}</span>
                             <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-[10px] font-bold">
                                {group.items.length} Entries
                             </span>
                          </div>
                          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hidden sm:block">
                             Subtotal Qty: {group.items.reduce((s, i) => s + (Number(i.total_qty) || 0), 0).toLocaleString()}
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                    {group.items.map((outw) => {
                      const isExpanded = expandedRows.has(outw.id!);
                      const deductions = (fifoDeductions as Record<number, OutwardDeductionDetail[]>)[outw.id!] || [];
                      
                      return (
                        <Fragment key={outw.id}>
                          <TableRow 
                            className="transition-colors hover:bg-muted/50 group cursor-pointer"
                            onClick={() => toggleExpandRow(outw.id!)}
                          >
                            <TableCell onClick={(e) => e.stopPropagation()}>
                              <div className="flex items-center gap-1">
                                <button className="p-1 hover:bg-slate-200 rounded text-slate-500 transition-colors">
                                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                                </button>
                                <input 
                                  type="checkbox" 
                                  checked={selectedRows.has(outw.id!)}
                                  onChange={() => toggleSelectRow(outw.id!)}
                                  className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4 ml-1 cursor-pointer"
                                />
                              </div>
                            </TableCell>
                            <TableCell className="whitespace-nowrap">
                              <span className="sm:inline hidden">{format(new Date(outw.date), "MMM dd, yyyy")}</span>
                              <span className="sm:hidden inline">{format(new Date(outw.date), "dd/MM")}</span>
                            </TableCell>
                            <TableCell className="font-medium text-primary">{outw.outward_no}</TableCell>
                            <TableCell className="mobile-hide-column">{outw.gp_no || "-"}</TableCell>
                            <TableCell className="mobile-hide-column">{outw.sr_no || "-"}</TableCell>
                            <TableCell className="whitespace-nowrap">{outw.from_party_name || "-"}</TableCell>
                            <TableCell>
                              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold">
                                {deductions.length > 0 ? (
                                  <span>{deductions.length} Inwards</span>
                                ) : (
                                  <span className="text-muted-foreground">-</span>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="font-medium text-orange-600 truncate max-w-[120px]">
                              {outw.outward_to_party_name || "-"}
                            </TableCell>
                            <TableCell className="mobile-hide-column">{outw.vehicle_no || "-"}</TableCell>
                            <TableCell className="mobile-hide-column">{outw.driver_name || "-"}</TableCell>
                            <TableCell className="text-right font-semibold text-emerald-600">
                              {Number(outw.total_qty || 0).toLocaleString()}
                            </TableCell>
                            <TableCell className="text-center" onClick={(e) => e.stopPropagation()}>
                              <div className="flex justify-center gap-1 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                                <Button variant="ghost" size="icon" className="h-8 w-8 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50" onClick={() => handlePrintSingle(outw.id!)} disabled={isPrinting}>
                                  <Printer className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => handleOpenEdit(outw.id!)}>
                                  <Pencil className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                                  if(confirm('Are you sure you want to delete this Outward record?')) {
                                    deleteMutation.mutate(outw.id!);
                                  }
                                }}>
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                          
                          {/* Automated FIFO References - Block */}
                          {isExpanded && deductions.length > 0 && (
                            <TableRow className="bg-slate-50/60 hover:bg-slate-50/60">
                              <TableCell colSpan={12} className="p-0">
                                <div className="mx-4 my-2 sm:mx-8 sm:ml-12 border-l-2 border-indigo-200 pl-4">
                                  <div className="flex items-center gap-2 mb-2">
                                    <Package className="h-3.5 w-3.5 text-indigo-500" />
                                    <span className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest">Inward Deductions Source</span>
                                  </div>
                                  <div className="bg-white rounded-lg border border-indigo-100 shadow-sm overflow-hidden mb-3">
                                    <table className="w-full text-xs">
                                      <thead>
                                        <tr className="bg-indigo-50/80 text-indigo-900 border-b border-indigo-100">
                                          <th className="px-3 py-1.5 text-left font-bold text-[10px] uppercase tracking-wider">Item Name</th>
                                          <th className="px-3 py-1.5 text-left font-bold text-[10px] uppercase tracking-wider">Inward Ref</th>
                                          <th className="px-3 py-1.5 text-left font-bold text-[10px] uppercase tracking-wider mobile-hide-column">From Party</th>
                                          <th className="px-3 py-1.5 text-right font-bold text-[10px] uppercase tracking-wider">Deducted Qty</th>
                                        </tr>
                                      </thead>
                                      <tbody>
                                        {deductions.map((deduct, idx) => (
                                          <tr key={deduct.id || idx} className={idx % 2 === 0 ? '' : 'bg-slate-50/50'}>
                                            <td className="px-3 py-2 font-semibold text-slate-800">{deduct.item_name}</td>
                                            <td className="px-3 py-2 text-slate-600">
                                              <div className="flex flex-col">
                                                <span className="font-semibold text-blue-700">{deduct.inward_no}</span>
                                                <span className="text-[10px] text-muted-foreground font-medium">GP: {deduct.inward_gp_no || '-'} | MS GP: {deduct.inward_ms_party_gp_no || '-'}</span>
                                              </div>
                                            </td>
                                            <td className="px-3 py-2 text-slate-600 mobile-hide-column">{deduct.from_party_name || '-'}</td>
                                            <td className="px-3 py-2 text-right font-bold text-red-600">-{Number(deduct.deducted_qty).toLocaleString()}</td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                          {isExpanded && deductions.length === 0 && (
                            <TableRow className="bg-slate-50/60 hover:bg-slate-50/60">
                              <TableCell colSpan={12} className="py-4 text-center text-sm text-slate-500">
                                No inward deductions found for this outward record. Run FIFO Migration if this is old data.
                              </TableCell>
                            </TableRow>
                          )}
                        </Fragment>
                      );
                    })}
                  </Fragment>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Primary Party Selection Dialog before Form */}
      <Dialog open={isPartyDialogOpen} onOpenChange={setIsPartyDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Select MS Party for Outward</DialogTitle>
          </DialogHeader>
          <div className="py-6 space-y-4">
            <div className="space-y-2">
              <Label>MS Party (Only parties with available stock)</Label>
              <Popover open={partySelectOpen} onOpenChange={setPartySelectOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between"
                  >
                    {selectedPartyIdForNew
                      ? msParties.find((party) => String(party.id) === selectedPartyIdForNew)?.name
                      : "Search MS Party..."}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[380px] p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search party..." />
                    <CommandList>
                      <CommandEmpty>
                        <span className="text-red-500 italic">No MS Parties found with available stock.</span>
                      </CommandEmpty>
                      <CommandGroup>
                        {msPartiesWithStock.map((party) => (
                          <CommandItem
                            key={party.id}
                            value={party.name}
                            onSelect={() => {
                              setSelectedPartyIdForNew(String(party.id));
                              setPartySelectOpen(false);
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                selectedPartyIdForNew === String(party.id) ? "opacity-100" : "opacity-0"
                              )}
                            />
                            {party.name}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
            <Button className="w-full" onClick={handleProceedToForm}>
              Proceed
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Main Create / Edit Form Dialog */}
      <Dialog open={isFormDialogOpen} onOpenChange={setIsFormDialogOpen}>
        <DialogContent className="sm:max-w-[700px] p-0 overflow-hidden">
          <div className="p-6 bg-slate-50/50 border-b">
            <DialogHeader>
              <DialogTitle className="text-xl">{editingOutward ? "Edit Outward Entry" : "New Outward Entry"}</DialogTitle>
            </DialogHeader>
            {!editingOutward && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium text-muted-foreground bg-white p-3 rounded-lg border shadow-sm">
                <span>Outward No: <span className="text-primary italic">Auto-generated</span></span>
                <span>GP No: <span className="text-primary italic">Auto-generated</span></span>
                <span>Sr No: <span className="text-primary italic">Auto relative to MS Party</span></span>
              </div>
            )}
            {editingOutward && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium bg-white p-3 rounded-lg border shadow-sm">
                <span>Outward No: <span className="text-primary">{editingOutward.outward_no}</span></span>
                <span>GP No: <span className="text-primary">{editingOutward.gp_no}</span></span>
                <span>Sr No: <span className="text-primary">{editingOutward.sr_no}</span></span>
              </div>
            )}
          </div>

          <div className="p-6 overflow-y-auto max-h-[60vh]">
            <form id="outward-form" onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-6 pt-2 pb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label>MS Party</Label>
                    <Input 
                      value={msParties.find(p => String(p.id) === formData.ms_party_id)?.name || ""} 
                      disabled 
                      className="bg-muted cursor-not-allowed font-medium text-slate-700"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>From Party (Default) *</Label>
                    <Input 
                      value={fromParties.find(p => String(p.id) === formData.from_party_id)?.name || ""} 
                      disabled 
                      className="bg-muted cursor-not-allowed font-medium text-slate-700"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label>Outward To Party *</Label>
                    <Popover open={outwardToGroupOpen} onOpenChange={setOutwardToGroupOpen}>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          role="combobox"
                          aria-expanded={outwardToGroupOpen}
                          className="w-full justify-between font-normal"
                        >
                          {formData.outward_to_party_id
                            ? outwardParties.find((p) => String(p.id) === formData.outward_to_party_id)?.name
                            : (formData.outward_to_party_name || "Select or Type Outward To...")}
                          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
                        <Command className="w-full">
                          <CommandInput 
                            placeholder="Search or type new party..." 
                            value={formData.outward_to_party_name}
                            onValueChange={(val) => {
                              if (!outwardParties.some(p => p.name.toLowerCase() === val.toLowerCase())) {
                                setFormData({ ...formData, outward_to_party_id: "", outward_to_party_name: val });
                              }
                            }}
                          />
                          <CommandList>
                            <CommandEmpty>
                              {formData.outward_to_party_name && (
                                <div 
                                  className="p-2 cursor-pointer hover:bg-muted text-primary font-medium"
                                  onClick={() => {
                                    setOutwardToGroupOpen(false);
                                  }}
                                >
                                  Add "{formData.outward_to_party_name}"
                                </div>
                              )}
                              {!formData.outward_to_party_name && "No records found."}
                            </CommandEmpty>
                            <CommandGroup>
                              {outwardParties.filter(p => p.status === 'active').map((party) => (
                                <CommandItem
                                  key={party.id}
                                  value={party.name}
                                  onSelect={() => {
                                    setFormData({...formData, outward_to_party_id: String(party.id), outward_to_party_name: party.name});
                                    setOutwardToGroupOpen(false);
                                  }}
                                >
                                  <Check className={cn("mr-2 h-4 w-4", formData.outward_to_party_id === String(party.id) ? "opacity-100" : "opacity-0")} />
                                  {party.name}
                                </CommandItem>
                              ))}
                            </CommandGroup>
                          </CommandList>
                        </Command>
                      </PopoverContent>
                    </Popover>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Vehicle No</Label>
                      <Input 
                        value={formData.vehicle_no} 
                        onChange={e => setFormData({...formData, vehicle_no: e.target.value})} 
                        placeholder="Vehicle No" 
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Driver Name</Label>
                      <Input 
                        value={formData.driver_name} 
                        onChange={e => setFormData({...formData, driver_name: e.target.value})} 
                        placeholder="Driver Name" 
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-6">
                  <div className="space-y-2">
                    <Label>Date *</Label>
                    <Input 
                      type="date"
                      value={formData.date} 
                      onChange={e => setFormData({...formData, date: e.target.value})} 
                    />
                  </div>
                </div>
              </div>

              {/* Items Section */}
              <div className="mt-8 bg-slate-50 rounded-xl p-4 border border-blue-100">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-lg text-blue-950">Outward Items</h3>
                  <Button type="button" variant="outline" size="sm" onClick={handleAddItem} className="h-8 border-blue-200 hover:bg-blue-50">
                    <Plus className="mr-2 h-4 w-4 text-blue-600" /> Add Item
                  </Button>
                </div>

                <div className="space-y-3">
                  <div className="grid grid-cols-12 gap-3 pb-2 border-b text-xs sm:text-sm font-medium text-muted-foreground px-1">
                    <div className="col-span-12 sm:col-span-4">Item Name</div>
                    <div className="col-span-4 sm:col-span-2">MSR</div>
                    <div className="col-span-4 sm:col-span-2 text-center text-blue-600">Available</div>
                    <div className="col-span-4 sm:col-span-3 text-right">Outward Qty</div>
                    <div className="col-span-1 text-center hidden sm:block"></div>
                  </div>

                  {formData.items.map((item, idx) => {
                    const availableStock = item.item_id ? getAvailableStock(item.item_id, item.measurement, item.quantity) : 0;
                    return (
                      <div key={idx} className="grid grid-cols-12 gap-2 sm:gap-3 items-center bg-white p-2 rounded-lg border border-blue-50 shadow-sm relative">
                        <div className="col-span-12 sm:col-span-4">
                          <Select 
                            value={String(item.item_id || '')} 
                            onValueChange={(val) => handleItemChange(idx, 'item_id', Number(val))}
                          >
                            <SelectTrigger className="border-0 shadow-none bg-transparent">
                              <SelectValue placeholder="Item name..." />
                            </SelectTrigger>
                            <SelectContent>
                              {availableItems.map((it) => (
                                <SelectItem key={it.id} value={String(it.id)}>{it.name}{it.status !== 'active' ? ' (Inactive)' : ''}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        
                        <div className="col-span-4 sm:col-span-2">
                          <Select 
                            value={String(item.measurement)} 
                            onValueChange={(val) => handleItemChange(idx, 'measurement', Number(val) as 15 | 22)}
                          >
                            <SelectTrigger className="border-0 shadow-none bg-transparent">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="15">15</SelectItem>
                              <SelectItem value="22">22</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="col-span-3 sm:col-span-2 text-center flex items-center justify-center">
                          <span className={`font-semibold py-1 px-3 rounded-md w-full text-sm ${item.item_id && availableStock <= 0 ? 'text-red-600 bg-red-50' : 'text-blue-600 bg-blue-50'}`}>
                            {item.item_id ? availableStock.toFixed(2) : "-"}
                          </span>
                        </div>

                        <div className="col-span-5 sm:col-span-3">
                          <Input 
                            type="number" 
                            min="0"
                            step="0.001"
                            value={item.quantity === 0 && !editingOutward ? '' : item.quantity} 
                            onChange={(e) => {
                              const val = e.target.value.replace(/-/g, '');
                              handleItemChange(idx, 'quantity', parseFloat(val) || 0);
                            }}
                            onKeyDown={(e) => { if (e.key === '-' || e.key === 'e') e.preventDefault(); }}
                            className="border bg-transparent text-right pr-2"
                            placeholder="Qty..."
                          />
                        </div>

                        <div className="absolute -top-2 -right-2 sm:static sm:col-span-1 flex justify-center">
                          <Button 
                            type="button" 
                            variant="ghost" 
                            size="icon" 
                            className="h-6 w-6 sm:h-8 sm:w-8 text-red-500 hover:text-red-700 bg-white sm:bg-transparent shadow-sm sm:shadow-none hover:bg-red-50 rounded-full"
                            onClick={() => handleRemoveItem(idx)}
                            disabled={formData.items.length <= 1}
                          >
                            <Trash2 className="h-3 w-3 sm:h-4 sm:w-4" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}

                  <div className="flex justify-end pt-4 pr-2 sm:pr-12 text-lg">
                    <span className="font-semibold mr-2">Total Outward:</span>
                    <span className="font-bold text-orange-600">
                      {totalQuantity.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </form>
          </div>
          
          <div className="p-4 border-t bg-slate-50 flex justify-end gap-3 rounded-b-lg">
            <Button type="button" variant="outline" onClick={() => setIsFormDialogOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="outward-form" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingOutward ? 'Save Changes' : 'Save Outward'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
