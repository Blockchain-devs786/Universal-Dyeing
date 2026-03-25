import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowUpFromLine, Plus, Search, Trash2, Pencil, Check, ChevronsUpDown } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  transfersApi,
  msPartiesApi,
  fromPartiesApi,
  itemsApi,
  reportsApi,
  type Transfer,
  type TransferItem,
} from "@/lib/api-client";

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

export default function TransferPage() {
  const queryClient = useQueryClient();

  // Filters State
  const [filterMsPartyId, setFilterMsPartyId] = useState<string>("all");
  const [filterTransferNo, setFilterTransferNo] = useState("");
  const [filterGpNo, setFilterGpNo] = useState("");
  const [filterFromDate, setFilterFromDate] = useState("");
  const [filterToDate, setFilterToDate] = useState("");

  const [isPartyDialogOpen, setIsPartyDialogOpen] = useState(false);
  const [isFormDialogOpen, setIsFormDialogOpen] = useState(false);
  
  const [editingTransfer, setEditingTransfer] = useState<Transfer | null>(null);

  // Combobox popover states
  const [partySelectOpen, setPartySelectOpen] = useState(false);
  const [fromPartyOpen, setFromPartyOpen] = useState(false);
  const [transferToGroupOpen, setTransferToGroupOpen] = useState(false);
  const [filterMsPartyOpen, setFilterMsPartyOpen] = useState(false);

  // Form State
  const [selectedPartyIdForNew, setSelectedPartyIdForNew] = useState<string>("");
  const [formData, setFormData] = useState({
    ms_party_id: "",
    from_party_id: "",
    transfer_to_party_id: "",
    vehicle_no: "",
    driver_name: "",
    date: format(new Date(), "yyyy-MM-dd"),
    items: [] as TransferItem[],
  });

  // Queries
  const { data: transfers = [], isLoading } = useQuery({
    queryKey: [
      "transfers",
      filterMsPartyId,
      filterTransferNo,
      filterGpNo,
      filterFromDate,
      filterToDate,
    ],
    queryFn: () =>
      transfersApi.list({
        ms_party_id: filterMsPartyId !== "all" ? Number(filterMsPartyId) : undefined,
        transfer_no: filterTransferNo || undefined,
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

  const { data: stocks = [] } = useQuery({
    queryKey: ["reports_stock"],
    queryFn: () => reportsApi.getStock("all", "all"),
  });

  // Derived stock data
  const msPartiesWithStock = useMemo(() => {
    return msParties.filter(party => 
      stocks.some(s => s.ms_party_id === party.id && s.remaining > 0)
    );
  }, [msParties, stocks]);

  const currentPartyId = editingTransfer ? String(editingTransfer.ms_party_id) : formData.ms_party_id;
  const currentPartyStocks = useMemo(() => {
    return stocks.filter(s => String(s.ms_party_id) === currentPartyId);
  }, [stocks, currentPartyId]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: Omit<Transfer, "id" | "transfer_no" | "gp_no" | "sr_no" | "created_at" | "updated_at">) =>
      transfersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
      queryClient.invalidateQueries({ queryKey: ["reports_stock"] });
      toast.success("Transfer entry created successfully");
      setIsFormDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Transfer> }) =>
      transfersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
      queryClient.invalidateQueries({ queryKey: ["reports_stock"] });
      toast.success("Transfer entry updated successfully");
      setIsFormDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => transfersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
      queryClient.invalidateQueries({ queryKey: ["reports_stock"] });
      toast.success("Transfer entry deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const handleOpenPartySelection = () => {
    setSelectedPartyIdForNew("");
    setIsPartyDialogOpen(true);
  };

  const handleProceedToForm = () => {
    if (!selectedPartyIdForNew) return toast.error("Please select an MS Party first");
    const defaultFromParty = fromParties.find((p: any) => p.is_default);
    
    setEditingTransfer(null);
    setFormData({
      ms_party_id: selectedPartyIdForNew,
      from_party_id: defaultFromParty ? String(defaultFromParty.id) : "",
      transfer_to_party_id: "",
      vehicle_no: "",
      driver_name: "",
      date: format(new Date(), "yyyy-MM-dd"),
      items: [{ id: 0, transfer_id: 0, item_id: 0, measurement: 15, quantity: 0 }],
    });
    setIsPartyDialogOpen(false);
    setIsFormDialogOpen(true);
  };

  const handleOpenEdit = async (id: number) => {
    try {
      const data = await transfersApi.getById(id);
      setEditingTransfer(data);
      setFormData({
        ms_party_id: String(data.ms_party_id),
        from_party_id: String(data.from_party_id),
        transfer_to_party_id: String(data.transfer_to_party_id),
        vehicle_no: data.vehicle_no || "",
        driver_name: data.driver_name || "",
        date: data.date ? data.date.substring(0, 10) : format(new Date(), "yyyy-MM-dd"),
        items: data.items || [],
      });
      setIsFormDialogOpen(true);
    } catch (err: any) {
      toast.error("Failed to fetch transfer details");
    }
  };

  const handleAddItem = () => {
    setFormData({
      ...formData,
      items: [
        ...formData.items,
        { id: 0, transfer_id: 0, item_id: 0, measurement: 15, quantity: 0 },
      ],
    });
  };

  const handleRemoveItem = (index: number) => {
    const newItems = [...formData.items];
    newItems.splice(index, 1);
    setFormData({ ...formData, items: newItems });
  };

  const handleItemChange = (index: number, field: keyof TransferItem, value: any) => {
    const newItems = [...formData.items];
    (newItems[index] as any)[field] = value;
    setFormData({ ...formData, items: newItems });
  };

  const getAvailableStock = (itemId: number, measurement: number) => {
    const stockRec = currentPartyStocks.find(s => s.item_id === itemId && s.msr === measurement);
    let stock = stockRec ? stockRec.remaining : 0;
    
    if (editingTransfer && editingTransfer.items) {
      const originalItem = editingTransfer.items.find(i => i.item_id === itemId && i.measurement === measurement);
      if (originalItem) {
        stock += originalItem.quantity;
      }
    }
    return stock;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.ms_party_id) return toast.error("MS Party is required");
    if (!formData.from_party_id) return toast.error("From Party is required");
    if (!formData.transfer_to_party_id) return toast.error("Transfer To Party is required");
    if (!formData.date) return toast.error("Date is required");
    if (formData.items.length === 0) return toast.error("At least one item is required");

    const seenItems = new Set();

    for (let i = 0; i < formData.items.length; i++) {
      const item = formData.items[i];
      if (!item.item_id) return toast.error(`Item name is required for row ${i + 1}`);
      if (item.quantity <= 0) return toast.error(`Quantity must be greater than 0 for row ${i + 1}`);
      
      const available = getAvailableStock(item.item_id, item.measurement);
      if (item.quantity > available) {
        return toast.error(`Row ${i + 1}: Transfer quantity (${item.quantity}) exceeds available stock (${available})`);
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
      transfer_to_party_id: Number(formData.transfer_to_party_id),
      vehicle_no: formData.vehicle_no,
      driver_name: formData.driver_name,
      date: formData.date,
      status: "active",
      items: formData.items.map(item => ({
        item_id: Number(item.item_id),
        measurement: item.measurement,
        quantity: Number(item.quantity)
      })) as Omit<TransferItem, "id" | "transfer_id">[] as any
    };

    if (editingTransfer) {
      updateMutation.mutate({ id: editingTransfer.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const totalQuantity = formData.items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
  
  const filterMsPartyObj = msParties.find(p => String(p.id) === filterMsPartyId);
  const selectedFromPartyObj = fromParties.find(p => String(p.id) === formData.from_party_id);
  const selectedTransferToPartyObj = fromParties.find(p => String(p.id) === formData.transfer_to_party_id);

  // Derive unique items and measurements available for current MS party
  const availableItems = useMemo(() => {
    const itemIds = new Set(currentPartyStocks.filter(s => s.remaining > 0 || (editingTransfer)).map(s => s.item_id));
    return items.filter(it => itemIds.has(it.id));
  }, [items, currentPartyStocks, editingTransfer]);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <ArrowUpFromLine className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Transfer Entries</h1>
            <p className="text-white/80 mt-1">Manage processing dispatches and transfer slips.</p>
          </div>
        </div>
        
        <Button onClick={handleOpenPartySelection} className="bg-white hover:bg-white/90 text-primary shadow-md transition-all">
          <Plus className="mr-2 h-4 w-4" /> Add Transfer
        </Button>
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
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Transfer No</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Filter by transfer no..."
              value={filterTransferNo}
              onChange={(e) => setFilterTransferNo(e.target.value)}
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
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Transfer No</TableHead>
              <TableHead>GP No</TableHead>
              <TableHead>Sr No</TableHead>
              <TableHead>MS Party</TableHead>
              <TableHead>From</TableHead>
              <TableHead>Transfer To</TableHead>
              <TableHead>Vehicle</TableHead>
              <TableHead>Driver</TableHead>
              <TableHead className="text-right">Total Qty</TableHead>
              <TableHead className="text-center w-28">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-10 text-muted-foreground">Loading transfer entries...</TableCell>
              </TableRow>
            ) : transfers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={11} className="text-center py-12 text-muted-foreground">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <ArrowUpFromLine className="h-8 w-8 text-muted-foreground/40" />
                    <span>No transfer entries found.</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              transfers.map((trans) => (
                <TableRow key={trans.id} className="transition-colors hover:bg-muted/50 group">
                  <TableCell className="whitespace-nowrap">
                    {format(new Date(trans.date), "MMM dd, yyyy")}
                  </TableCell>
                  <TableCell className="font-medium text-primary">{trans.transfer_no}</TableCell>
                  <TableCell>{trans.gp_no || "-"}</TableCell>
                  <TableCell>{trans.sr_no || "-"}</TableCell>
                  <TableCell className="font-medium">{trans.ms_party_name || "-"}</TableCell>
                  <TableCell>{trans.from_party_name || "-"}</TableCell>
                  <TableCell className="font-medium text-orange-600">{trans.transfer_to_party_name || "-"}</TableCell>
                  <TableCell>{trans.vehicle_no || "-"}</TableCell>
                  <TableCell>{trans.driver_name || "-"}</TableCell>
                  <TableCell className="text-right font-semibold text-emerald-600">
                    {Number(trans.total_qty || 0).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => handleOpenEdit(trans.id!)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                        if(confirm('Are you sure you want to delete this Transfer record?')) {
                          deleteMutation.mutate(trans.id!);
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

      {/* Primary Party Selection Dialog before Form */}
      <Dialog open={isPartyDialogOpen} onOpenChange={setIsPartyDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Select MS Party for Transfer</DialogTitle>
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
              <DialogTitle className="text-xl">{editingTransfer ? "Edit Transfer Entry" : "New Transfer Entry"}</DialogTitle>
            </DialogHeader>
            {!editingTransfer && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium text-muted-foreground bg-white p-3 rounded-lg border shadow-sm">
                <span>Transfer No: <span className="text-primary italic">Auto-generated</span></span>
                <span>GP No: <span className="text-primary italic">Auto-generated</span></span>
                <span>Sr No: <span className="text-primary italic">Auto relative to MS Party</span></span>
              </div>
            )}
            {editingTransfer && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium bg-white p-3 rounded-lg border shadow-sm">
                <span>Transfer No: <span className="text-primary">{editingTransfer.transfer_no}</span></span>
                <span>GP No: <span className="text-primary">{editingTransfer.gp_no}</span></span>
                <span>Sr No: <span className="text-primary">{editingTransfer.sr_no}</span></span>
              </div>
            )}
          </div>

          <div className="p-6 overflow-y-auto max-h-[60vh]">
            <form id="transfer-form" onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                <div className="space-y-2">
                  <Label>MS Party</Label>
                  <Input 
                    value={msParties.find(p => String(p.id) === formData.ms_party_id)?.name || ""} 
                    disabled 
                    className="bg-muted cursor-not-allowed"
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

                <div className="space-y-2">
                  <Label>Transfer To Party *</Label>
                  <Popover open={transferToGroupOpen} onOpenChange={setTransferToGroupOpen}>
                    <PopoverTrigger asChild>
                      <Button variant="outline" role="combobox" className="w-full justify-between font-normal text-orange-600 border-orange-200 hover:bg-orange-50">
                        <span className="truncate">{selectedTransferToPartyObj ? selectedTransferToPartyObj.name : "Select Transfer To..."}</span>
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[300px] p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Search party..." />
                        <CommandList>
                          <CommandEmpty>No records found.</CommandEmpty>
                          <CommandGroup>
                            {fromParties.map((party) => (
                              <CommandItem
                                key={party.id}
                                value={party.name}
                                onSelect={() => {
                                  setFormData({...formData, transfer_to_party_id: String(party.id)});
                                  setTransferToGroupOpen(false);
                                }}
                              >
                                <Check className={cn("mr-2 h-4 w-4", formData.transfer_to_party_id === String(party.id) ? "opacity-100" : "opacity-0")} />
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

                <div className="space-y-2">
                  <Label>Date *</Label>
                  <Input 
                    type="date"
                    value={formData.date} 
                    onChange={e => setFormData({...formData, date: e.target.value})} 
                  />
                </div>
              </div>

              {/* Items Section */}
              <div className="mt-8 bg-slate-50 rounded-xl p-4 border border-blue-100">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-lg text-blue-950">Transfer Items</h3>
                  <Button type="button" variant="outline" size="sm" onClick={handleAddItem} className="h-8 border-blue-200 hover:bg-blue-50">
                    <Plus className="mr-2 h-4 w-4 text-blue-600" /> Add Item
                  </Button>
                </div>

                <div className="space-y-3">
                  <div className="grid grid-cols-12 gap-3 pb-2 border-b text-xs sm:text-sm font-medium text-muted-foreground px-1">
                    <div className="col-span-12 sm:col-span-4">Item Name</div>
                    <div className="col-span-4 sm:col-span-2">MSR</div>
                    <div className="col-span-4 sm:col-span-2 text-center text-blue-600">Available</div>
                    <div className="col-span-4 sm:col-span-3 text-right">Transfer Qty</div>
                    <div className="col-span-1 text-center hidden sm:block"></div>
                  </div>

                  {formData.items.map((item, idx) => {
                    const availableStock = item.item_id ? getAvailableStock(item.item_id, item.measurement) : 0;
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
                                <SelectItem key={it.id} value={String(it.id)}>{it.name}</SelectItem>
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
                          <span className="font-semibold text-blue-600 bg-blue-50 py-1 px-3 rounded-md w-full text-sm">
                            {item.item_id ? availableStock : "-"}
                          </span>
                        </div>

                        <div className="col-span-5 sm:col-span-3">
                          <Input 
                            type="number" 
                            min="0"
                            step="0.01"
                            value={item.quantity === 0 && !editingTransfer ? '' : item.quantity} 
                            onChange={(e) => handleItemChange(idx, 'quantity', parseFloat(e.target.value) || 0)} 
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
                    <span className="font-semibold mr-2">Total Transfer:</span>
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
            <Button type="submit" form="transfer-form" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingTransfer ? 'Save Changes' : 'Save Transfer'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
