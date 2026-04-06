import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, Plus, Search, Trash2, Pencil, Check, ChevronsUpDown, Printer } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  inwardsApi,
  msPartiesApi,
  fromPartiesApi,
  itemsApi,
  type Inward,
  type InwardItem,
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
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { cn } from "@/lib/utils";

export default function Inward() {
  const queryClient = useQueryClient();

  // Filters State
  const [filterMsPartyId, setFilterMsPartyId] = useState<string>("all");
  const [filterInwardNo, setFilterInwardNo] = useState("");
  const [filterGpNo, setFilterGpNo] = useState("");
  const [filterFromDate, setFilterFromDate] = useState("");
  const [filterToDate, setFilterToDate] = useState("");

  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [isPrinting, setIsPrinting] = useState(false);

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingInward, setEditingInward] = useState<Inward | null>(null);

  // Combobox popover states
  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [fromPartyOpen, setFromPartyOpen] = useState(false);
  const [filterMsPartyOpen, setFilterMsPartyOpen] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    ms_party_id: "",
    from_party_id: "",
    vehicle_no: "",
    driver_name: "",
    date: format(new Date(), "yyyy-MM-dd"),
    items: [] as InwardItem[],
  });

  // Queries
  const { data: inwards = [], isLoading } = useQuery({
    queryKey: [
      "inwards",
      filterMsPartyId,
      filterInwardNo,
      filterGpNo,
      filterFromDate,
      filterToDate,
    ],
    queryFn: () =>
      inwardsApi.list({
        ms_party_id: filterMsPartyId !== "all" ? Number(filterMsPartyId) : undefined,
        inward_no: filterInwardNo || undefined,
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

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: Omit<Inward, "id" | "inward_no" | "gp_no" | "sr_no" | "created_at" | "updated_at">) =>
      inwardsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inwards"] });
      toast.success("Inward entry created successfully");
      closeDialog();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Inward> }) =>
      inwardsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inwards"] });
      toast.success("Inward entry updated successfully");
      closeDialog();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => inwardsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inwards"] });
      toast.success("Inward entry deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const handlePrintSelected = async () => {
    if (selectedRows.size === 0) return;
    setIsPrinting(true);
    try {
      const documentsToPrint = [];
      for (const id of Array.from(selectedRows)) {
        const fullDoc = await inwardsApi.getById(id);
        documentsToPrint.push(fullDoc);
      }
      generateAndPrintHTML('inward', documentsToPrint);
      setSelectedRows(new Set());
    } catch (err) {
      toast.error("Failed to generate print document");
    } finally {
      setIsPrinting(false);
    }
  };

  const handlePrintSingle = async (id: number) => {
    setIsPrinting(true);
    try {
      const fullDoc = await inwardsApi.getById(id);
      generateAndPrintHTML('inward', [fullDoc]);
    } catch (err) {
      toast.error("Failed to generate print document");
    } finally {
      setIsPrinting(false);
    }
  };

  const handleOpenDialog = () => {
    setEditingInward(null);
    setFormData({
      ms_party_id: "",
      from_party_id: "",
      vehicle_no: "",
      driver_name: "",
      date: format(new Date(), "yyyy-MM-dd"),
      items: [{ id: 0, inward_id: 0, item_id: 0, measurement: 15, quantity: 0 }],
    });
    setIsDialogOpen(true);
  };

  const handleOpenEdit = async (id: number) => {
    try {
      const data = await inwardsApi.getById(id);
      setEditingInward(data);
      setFormData({
        ms_party_id: String(data.ms_party_id),
        from_party_id: String(data.from_party_id),
        vehicle_no: data.vehicle_no || "",
        driver_name: data.driver_name || "",
        date: data.date ? data.date.substring(0, 10) : format(new Date(), "yyyy-MM-dd"),
        items: data.items || [],
      });
      setIsDialogOpen(true);
    } catch (err: any) {
      toast.error("Failed to fetch inward details");
    }
  };

  const closeDialog = () => {
    setIsDialogOpen(false);
    setEditingInward(null);
  };

  const handleAddItem = () => {
    setFormData({
      ...formData,
      items: [
        ...formData.items,
        { id: 0, inward_id: 0, item_id: 0, measurement: 15, quantity: 0 },
      ],
    });
  };

  const handleRemoveItem = (index: number) => {
    const newItems = [...formData.items];
    newItems.splice(index, 1);
    setFormData({ ...formData, items: newItems });
  };

  const handleItemChange = (index: number, field: keyof InwardItem, value: any) => {
    const newItems = [...formData.items];
    (newItems[index] as any)[field] = value;
    setFormData({ ...formData, items: newItems });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.ms_party_id) return toast.error("MS Party is required");
    if (!formData.from_party_id) return toast.error("From Party is required");
    if (!formData.date) return toast.error("Date is required");
    if (formData.items.length === 0) return toast.error("At least one item is required");

    const seenItems = new Set();

    for (let i = 0; i < formData.items.length; i++) {
      const item = formData.items[i];
      if (!item.item_id) return toast.error(`Item name is required for row ${i + 1}`);
      if (item.quantity <= 0) return toast.error(`Quantity must be greater than 0 for row ${i + 1}`);
      
      const key = `${item.item_id}-${item.measurement}`;
      if (seenItems.has(key)) {
        return toast.error(`Conflict: Row ${i + 1} uses the same Item + Measurement combination as another row.`);
      }
      seenItems.add(key);
    }

    const payload = {
      ms_party_id: Number(formData.ms_party_id),
      from_party_id: Number(formData.from_party_id),
      vehicle_no: formData.vehicle_no,
      driver_name: formData.driver_name,
      date: formData.date,
      status: "active",
      items: formData.items.map(item => ({
        item_id: Number(item.item_id),
        measurement: item.measurement,
        quantity: Number(item.quantity)
      })) as Omit<InwardItem, "id" | "inward_id">[] as any
    };

    if (editingInward) {
      updateMutation.mutate({ id: editingInward.id, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const totalQuantity = formData.items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);
  const selectedMsPartyObj = msParties.find(p => String(p.id) === formData.ms_party_id);
  const selectedFromPartyObj = fromParties.find(p => String(p.id) === formData.from_party_id);
  const filterMsPartyObj = msParties.find(p => String(p.id) === filterMsPartyId);

  const toggleSelectAll = () => {
    if (selectedRows.size === inwards.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(inwards.map(i => i.id!)));
    }
  };

  const toggleSelectRow = (id: number) => {
    const newSet = new Set(selectedRows);
    if (newSet.has(id)) newSet.delete(id);
    else newSet.add(id);
    setSelectedRows(newSet);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <ArrowDownToLine className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Inward Entries</h1>
            <p className="text-white/80 mt-1">Manage receiving transactions and generate Auto-numbered MS slips.</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {selectedRows.size > 0 && (
            <Button onClick={handlePrintSelected} disabled={isPrinting} className="bg-white/20 hover:bg-white/30 text-white border-0 shadow-sm backdrop-blur-sm transition-all duration-300 rounded-xl">
              <Printer className="mr-2 h-4 w-4" /> Print Selected ({selectedRows.size})
            </Button>
          )}
          <Button onClick={handleOpenDialog} className="bg-white hover:bg-white/90 text-primary shadow-md transition-all">
            <Plus className="mr-2 h-4 w-4" /> Add Inward
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
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Inward No</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Filter by inward no..."
              value={filterInwardNo}
              onChange={(e) => setFilterInwardNo(e.target.value)}
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
                    checked={inwards.length > 0 && selectedRows.size === inwards.length}
                    onChange={toggleSelectAll}
                    className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4 ml-2 cursor-pointer"
                  />
                </TableHead>
                <TableHead className="whitespace-nowrap">Date</TableHead>
                <TableHead className="whitespace-nowrap">Inward No</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">GP No</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">Sr No</TableHead>
                <TableHead className="whitespace-nowrap">MS Party</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">From Party</TableHead>
                <TableHead className="text-right whitespace-nowrap">Total Qty</TableHead>
                <TableHead className="text-center w-28 whitespace-nowrap">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-10 text-muted-foreground">Loading inward entries...</TableCell>
                </TableRow>
              ) : inwards.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <ArrowDownToLine className="h-8 w-8 text-muted-foreground/40" />
                      <span>No inward entries found.</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                inwards.map((inward) => (
                  <TableRow key={inward.id} className="transition-colors hover:bg-muted/50 group">
                    <TableCell>
                      <input 
                        type="checkbox" 
                        checked={selectedRows.has(inward.id!)}
                        onChange={() => toggleSelectRow(inward.id!)}
                        className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4 ml-2 cursor-pointer"
                      />
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <span className="sm:inline hidden">{format(new Date(inward.date), "MMM dd, yyyy")}</span>
                      <span className="sm:hidden inline">{format(new Date(inward.date), "dd/MM")}</span>
                    </TableCell>
                    <TableCell className="font-medium text-primary">{inward.inward_no}</TableCell>
                    <TableCell className="mobile-hide-column">{inward.gp_no || "-"}</TableCell>
                    <TableCell className="mobile-hide-column">{inward.sr_no || "-"}</TableCell>
                    <TableCell className="font-medium truncate max-w-[120px]">{inward.ms_party_name || "-"}</TableCell>
                    <TableCell className="mobile-hide-column">{inward.from_party_name || "-"}</TableCell>
                    <TableCell className="text-right font-semibold text-emerald-600">
                      {Number(inward.total_qty || 0).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex justify-center gap-1 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50" onClick={() => handlePrintSingle(inward.id!)} disabled={isPrinting}>
                        <Printer className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => handleOpenEdit(inward.id!)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                        if(confirm('Are you sure you want to delete this Inward record?')) {
                          deleteMutation.mutate(inward.id!);
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
      </div>

      {/* Create / Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[700px] p-0 overflow-hidden">
          <div className="p-6 bg-slate-50/50 border-b">
            <DialogHeader>
              <DialogTitle className="text-xl">{editingInward ? "Edit Inward Entry" : "New Inward Entry"}</DialogTitle>
            </DialogHeader>
            {!editingInward && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium text-muted-foreground bg-white p-3 rounded-lg border shadow-sm">
                <span>Inward No: <span className="text-primary italic">Auto-generated</span></span>
                <span>GP No: <span className="text-primary italic">Auto-generated</span></span>
                <span>Sr No: <span className="text-primary italic">Auto relative to MS Party</span></span>
              </div>
            )}
            {editingInward && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium bg-white p-3 rounded-lg border shadow-sm">
                <span>Inward No: <span className="text-primary">{editingInward.inward_no}</span></span>
                <span>GP No: <span className="text-primary">{editingInward.gp_no}</span></span>
                <span>Sr No: <span className="text-primary">{editingInward.sr_no}</span></span>
              </div>
            )}
          </div>

          <div className="p-6 overflow-y-auto max-h-[60vh]">
            <form id="inward-form" onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                <div className="space-y-2">
                  <Label>MS Party *</Label>
                  <Popover open={msPartyOpen} onOpenChange={setMsPartyOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={msPartyOpen}
                        className="w-full justify-between font-normal"
                      >
                        <span className="truncate">{selectedMsPartyObj ? selectedMsPartyObj.name : "Select MS Party..."}</span>
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[300px] p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Search ms party..." />
                        <CommandList>
                          <CommandEmpty>No records found.</CommandEmpty>
                          <CommandGroup>
                            {msParties.map((party) => (
                              <CommandItem
                                key={party.id}
                                value={party.name}
                                onSelect={() => {
                                  setFormData({...formData, ms_party_id: String(party.id)});
                                  setMsPartyOpen(false);
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    formData.ms_party_id === String(party.id) ? "opacity-100" : "opacity-0"
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

                <div className="space-y-2">
                  <Label>From Party *</Label>
                  <Popover open={fromPartyOpen} onOpenChange={setFromPartyOpen}>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={fromPartyOpen}
                        className="w-full justify-between font-normal"
                      >
                        <span className="truncate">{selectedFromPartyObj ? selectedFromPartyObj.name : "Select From Party..."}</span>
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-[300px] p-0" align="start">
                      <Command>
                        <CommandInput placeholder="Search from party..." />
                        <CommandList>
                          <CommandEmpty>No records found.</CommandEmpty>
                          <CommandGroup>
                            {fromParties.map((party) => (
                              <CommandItem
                                key={party.id}
                                value={party.name}
                                onSelect={() => {
                                  setFormData({...formData, from_party_id: String(party.id)});
                                  setFromPartyOpen(false);
                                }}
                              >
                                <Check
                                  className={cn(
                                    "mr-2 h-4 w-4",
                                    formData.from_party_id === String(party.id) ? "opacity-100" : "opacity-0"
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
              <div className="mt-8 bg-slate-50 rounded-xl p-4 border">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-lg">Items</h3>
                  <Button type="button" variant="outline" size="sm" onClick={handleAddItem} className="h-8">
                    <Plus className="mr-2 h-4 w-4" /> Add Item
                  </Button>
                </div>

                <div className="space-y-3">
                  <div className="grid grid-cols-12 gap-3 pb-2 border-b text-sm font-medium text-muted-foreground px-1">
                    <div className="col-span-12 sm:col-span-6">Item Name</div>
                    <div className="col-span-6 sm:col-span-3">Measurement</div>
                    <div className="col-span-6 sm:col-span-2 text-right">Quantity</div>
                    <div className="col-span-1 text-center"></div>
                  </div>

                  {formData.items.map((item, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-3 items-center bg-white p-2 rounded-lg border shadow-sm">
                      <div className="col-span-12 sm:col-span-6">
                        <Select 
                          value={String(item.item_id || '')} 
                          onValueChange={(val) => handleItemChange(idx, 'item_id', Number(val))}
                        >
                          <SelectTrigger className="border-0 shadow-none bg-transparent">
                            <SelectValue placeholder="Item name..." />
                          </SelectTrigger>
                          <SelectContent>
                            {items.map((it) => (
                              <SelectItem key={it.id} value={String(it.id)}>{it.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="col-span-4 sm:col-span-3">
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

                      <div className="col-span-6 sm:col-span-2">
                        <Input 
                          type="number" 
                          min="0"
                          step="0.01"
                          value={item.quantity === 0 && !editingInward ? '' : item.quantity} 
                          onChange={(e) => handleItemChange(idx, 'quantity', parseFloat(e.target.value) || 0)} 
                          className="border-0 shadow-none bg-transparent text-right pr-2"
                          placeholder="0"
                        />
                      </div>

                      <div className="col-span-2 sm:col-span-1 text-center">
                        <Button 
                          type="button" 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                          onClick={() => handleRemoveItem(idx)}
                          disabled={formData.items.length <= 1}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}

                  <div className="flex justify-end pt-4 pr-12 text-lg">
                    <span className="font-semibold mr-2">Total Quantity:</span>
                    <span className="font-bold text-primary">
                      {totalQuantity.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </form>
          </div>
          
          <div className="p-4 border-t bg-slate-50 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={closeDialog}>
              Cancel
            </Button>
            <Button type="submit" form="inward-form" disabled={createMutation.isPending || updateMutation.isPending}>
              {editingInward ? 'Save Changes' : 'Save Inward'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
