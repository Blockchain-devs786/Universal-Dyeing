import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownToLine, Plus, Search, Trash2, CalendarIcon, Eye } from "lucide-react";
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

export default function Inward() {
  const queryClient = useQueryClient();

  // Filters State
  const [filterMsPartyId, setFilterMsPartyId] = useState<string>("all");
  const [filterInwardNo, setFilterInwardNo] = useState("");
  const [filterGpNo, setFilterGpNo] = useState("");
  const [filterFromDate, setFilterFromDate] = useState("");
  const [filterToDate, setFilterToDate] = useState("");

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [viewingInward, setViewingInward] = useState<Inward | null>(null);

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

  // Create Mutation
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

  // Handlers
  const handleOpenDialog = () => {
    setViewingInward(null);
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

  const handleOpenView = async (id: number) => {
    try {
      const data = await inwardsApi.getById(id);
      setViewingInward(data);
      setIsDialogOpen(true);
    } catch (err: any) {
      toast.error("Failed to fetch inward details");
    }
  };

  const closeDialog = () => {
    setIsDialogOpen(false);
    setViewingInward(null);
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

    for (let i = 0; i < formData.items.length; i++) {
      if (!formData.items[i].item_id) return toast.error(`Item name is required for row ${i + 1}`);
      if (formData.items[i].quantity <= 0) return toast.error(`Quantity must be greater than 0 for row ${i + 1}`);
    }

    createMutation.mutate({
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
      })) as Omit<InwardItem, "id" | "inward_id">[] as any // casting to satisfy Omit typing in mutator
    });
  };

  const totalQuantity = formData.items.reduce((sum, item) => sum + (Number(item.quantity) || 0), 0);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Inward Entries</h1>
        </div>
        
        <Button onClick={handleOpenDialog} className="bg-primary hover:bg-primary/90 text-white shadow-md transition-all">
          <Plus className="mr-2 h-4 w-4" /> Add Inward
        </Button>
      </div>

      {/* Filters Section */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-border/50 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="space-y-1.5">
          <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">MS Party</Label>
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Select value={filterMsPartyId} onValueChange={setFilterMsPartyId}>
              <SelectTrigger className="pl-9 h-9">
                <SelectValue placeholder="All MS Parties" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All MS Parties</SelectItem>
                {msParties.map(p => (
                  <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
        <Table>
          <TableHeader className="bg-muted/30">
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Inward No</TableHead>
              <TableHead>GP No</TableHead>
              <TableHead>Sr No</TableHead>
              <TableHead>MS Party</TableHead>
              <TableHead>From Party</TableHead>
              <TableHead className="text-right">Total Qty</TableHead>
              <TableHead className="text-center w-20">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-10 text-muted-foreground">Loading inward entries...</TableCell>
              </TableRow>
            ) : inwards.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-12 text-muted-foreground">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <ArrowDownToLine className="h-8 w-8 text-muted-foreground/40" />
                    <span>No inward entries found.</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              inwards.map((inward) => (
                <TableRow key={inward.id} className="transition-colors hover:bg-muted/50 group">
                  <TableCell className="whitespace-nowrap">
                    {format(new Date(inward.date), "MMM dd, yyyy")}
                  </TableCell>
                  <TableCell className="font-medium text-primary">{inward.inward_no}</TableCell>
                  <TableCell>{inward.gp_no || "-"}</TableCell>
                  <TableCell>{inward.sr_no || "-"}</TableCell>
                  <TableCell className="font-medium">{inward.ms_party_name || "-"}</TableCell>
                  <TableCell>{inward.from_party_name || "-"}</TableCell>
                  <TableCell className="text-right font-semibold text-emerald-600">
                    {Number(inward.total_qty || 0).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-center">
                    <Button variant="ghost" size="icon" className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity" onClick={() => handleOpenView(inward.id!)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create / View Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-[700px] p-0 overflow-hidden">
          <div className="p-6 bg-slate-50/50 border-b">
            <DialogHeader>
              <DialogTitle className="text-xl">{viewingInward ? "View Inward Entry" : "New Inward Entry"}</DialogTitle>
            </DialogHeader>
            {!viewingInward && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium text-muted-foreground bg-white p-3 rounded-lg border shadow-sm">
                <span>Inward No: <span className="text-primary italic">Auto-generated</span></span>
                <span>GP No: <span className="text-primary italic">Auto-generated</span></span>
                <span>Sr No: <span className="text-primary italic">Auto-generated</span></span>
              </div>
            )}
            {viewingInward && (
              <div className="flex items-center gap-6 mt-4 text-sm font-medium bg-white p-3 rounded-lg border shadow-sm">
                <span>Inward No: <span className="text-primary">{viewingInward.inward_no}</span></span>
                <span>GP No: <span className="text-primary">{viewingInward.gp_no}</span></span>
                <span>Sr No: <span className="text-primary">{viewingInward.sr_no}</span></span>
              </div>
            )}
          </div>

          <div className="p-6 overflow-y-auto max-h-[60vh]">
            <form id="inward-form" onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                <div className="space-y-2">
                  <Label>MS Party *</Label>
                  <Select 
                    value={viewingInward ? String(viewingInward.ms_party_id) : formData.ms_party_id} 
                    onValueChange={(v) => setFormData({...formData, ms_party_id: v})}
                    disabled={!!viewingInward}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select MS Party" />
                    </SelectTrigger>
                    <SelectContent>
                      {msParties.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>From Party *</Label>
                  <Select 
                    value={viewingInward ? String(viewingInward.from_party_id) : formData.from_party_id} 
                    onValueChange={(v) => setFormData({...formData, from_party_id: v})}
                    disabled={!!viewingInward}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select From Party" />
                    </SelectTrigger>
                    <SelectContent>
                      {fromParties.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Vehicle No</Label>
                  <Input 
                    value={viewingInward ? viewingInward.vehicle_no || '' : formData.vehicle_no} 
                    onChange={e => setFormData({...formData, vehicle_no: e.target.value})} 
                    placeholder="Vehicle No" 
                    readOnly={!!viewingInward}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Driver Name</Label>
                  <Input 
                    value={viewingInward ? viewingInward.driver_name || '' : formData.driver_name} 
                    onChange={e => setFormData({...formData, driver_name: e.target.value})} 
                    placeholder="Driver Name" 
                    readOnly={!!viewingInward}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Date *</Label>
                  <Input 
                    type="date"
                    value={viewingInward ? (viewingInward.date ? viewingInward.date.substring(0,10) : '') : formData.date} 
                    onChange={e => setFormData({...formData, date: e.target.value})} 
                    readOnly={!!viewingInward}
                  />
                </div>
              </div>

              {/* Items Section */}
              <div className="mt-8 bg-slate-50 rounded-xl p-4 border">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-semibold text-lg">Items</h3>
                  {!viewingInward && (
                    <Button type="button" variant="outline" size="sm" onClick={handleAddItem} className="h-8">
                      <Plus className="mr-2 h-4 w-4" /> Add Item
                    </Button>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="grid grid-cols-12 gap-3 pb-2 border-b text-sm font-medium text-muted-foreground px-1">
                    <div className="col-span-12 sm:col-span-6">Item Name</div>
                    <div className="col-span-6 sm:col-span-3">Measurement</div>
                    <div className="col-span-6 sm:col-span-2 text-right">Quantity</div>
                    <div className="col-span-1 text-center"></div>
                  </div>

                  {(viewingInward ? viewingInward.items || [] : formData.items).map((item, idx) => (
                    <div key={idx} className="grid grid-cols-12 gap-3 items-center bg-white p-2 rounded-lg border shadow-sm">
                      <div className="col-span-12 sm:col-span-6">
                        <Select 
                          value={String(item.item_id || '')} 
                          onValueChange={(val) => handleItemChange(idx, 'item_id', Number(val))}
                          disabled={!!viewingInward}
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
                          disabled={!!viewingInward}
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
                          value={item.quantity || ''} 
                          onChange={(e) => handleItemChange(idx, 'quantity', parseFloat(e.target.value) || 0)} 
                          className="border-0 shadow-none bg-transparent text-right pr-2"
                          placeholder="0"
                          readOnly={!!viewingInward}
                        />
                      </div>

                      {!viewingInward && (
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
                      )}
                    </div>
                  ))}

                  <div className="flex justify-end pt-4 pr-12 text-lg">
                    <span className="font-semibold mr-2">Total Quantity:</span>
                    <span className="font-bold text-primary">
                      {viewingInward ? (viewingInward.total_qty || 0) : totalQuantity.toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </form>
          </div>
          
          <div className="p-4 border-t bg-slate-50 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={closeDialog}>
              {viewingInward ? "Close" : "Cancel"}
            </Button>
            {!viewingInward && (
              <Button type="submit" form="inward-form" disabled={createMutation.isPending}>
                Save Inward
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
