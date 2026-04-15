import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus, Search, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { fromPartiesApi, type FromParty } from "@/lib/api-client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

export default function FromParties() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingParty, setEditingParty] = useState<FromParty | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    phone: "",
    address: "",
    city: "",
    city: "",
    opening_balance: 0,
    balance_type: "debit" as "debit" | "credit",
    status: "active",
  });

  // Fetch
  const { data: parties = [], isLoading } = useQuery({
    queryKey: ["from_parties", search],
    queryFn: () => fromPartiesApi.list(search),
  });

  // Create
  const createMutation = useMutation({
    mutationFn: (data: Omit<FromParty, 'id' | 'debit' | 'credit' | 'created_at' | 'updated_at'>) => fromPartiesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["from_parties"] });
      toast.success("From Party created successfully");
      closeDialog();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Update
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FromParty> }) => fromPartiesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["from_parties"] });
      toast.success("From Party updated successfully");
      closeDialog();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Delete
  const deleteMutation = useMutation({
    mutationFn: (id: number) => fromPartiesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["from_parties"] });
      toast.success("From Party deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const handleOpenDialog = (party?: FromParty) => {
    if (party) {
      setEditingParty(party);
      setFormData({
        name: party.name,
        phone: party.phone || "",
        address: party.address || "",
        city: party.city || "",
        opening_balance: Math.abs(party.opening_balance || 0),
        balance_type: (party.opening_balance || 0) < 0 ? "credit" : "debit",
        status: party.status || "active",
      });
    } else {
      setEditingParty(null);
      setFormData({
        name: "",
        phone: "",
        address: "",
        city: "",
        city: "",
        opening_balance: 0,
        balance_type: "debit",
        status: "active",
      });
    }
    setIsDialogOpen(true);
  };

  const closeDialog = () => {
    setIsDialogOpen(false);
    setEditingParty(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) return toast.error("Name is required");

    const finalData = {
      ...formData,
      opening_balance: formData.balance_type === 'credit' ? -Math.abs(formData.opening_balance) : Math.abs(formData.opening_balance)
    };
    
    // remove balance_type before sending
    const { balance_type, ...submitData } = finalData;

    if (editingParty) {
      updateMutation.mutate({ id: editingParty.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleStatusToggle = (party: FromParty, checked: boolean) => {
    const newStatus = checked ? "active" : "inactive";
    updateMutation.mutate({ id: party.id, data: { status: newStatus } });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <Building2 className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">From Parties</h1>
            <p className="text-white/80 mt-1">Manage from-parties. This also syncs with MS Parties automatically.</p>
          </div>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()} className="bg-white text-primary hover:bg-white/90 shadow-md transition-all">
              <Plus className="mr-2 h-4 w-4" /> Add Party
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <form onSubmit={handleSubmit}>
              <DialogHeader>
                <DialogTitle>{editingParty ? "Edit Party" : "Add New Party"}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input 
                    id="name" 
                    value={formData.name} 
                    onChange={e => setFormData({...formData, name: e.target.value})} 
                    placeholder="E.g. ABC Textiles" 
                    required 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input 
                    id="phone" 
                    value={formData.phone} 
                    onChange={e => setFormData({...formData, phone: e.target.value})} 
                    placeholder="Phone number" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="city">City</Label>
                  <Input 
                    id="city" 
                    value={formData.city} 
                    onChange={e => setFormData({...formData, city: e.target.value})} 
                    placeholder="City name" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="address">Address</Label>
                  <Input 
                    id="address" 
                    value={formData.address} 
                    onChange={e => setFormData({...formData, address: e.target.value})} 
                    placeholder="Full address" 
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="space-y-2 col-span-2">
                    <Label htmlFor="opening_balance">Opening Balance</Label>
                    <Input 
                      id="opening_balance" 
                      type="number" 
                      step="0.01" 
                      min="0"
                      value={formData.opening_balance} 
                      onChange={e => setFormData({...formData, opening_balance: parseFloat(e.target.value) || 0})} 
                    />
                  </div>
                  <div className="space-y-2 col-span-1">
                    <Label htmlFor="balance_type">Type</Label>
                    <Select value={formData.balance_type} onValueChange={(v: any) => setFormData({...formData, balance_type: v})}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="debit">Debit (Dr)</SelectItem>
                        <SelectItem value="credit">Credit (Cr)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <Label htmlFor="status">Status</Label>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-muted-foreground">{formData.status === 'active' ? 'Active' : 'Inactive'}</span>
                    <Switch 
                      id="status" 
                      checked={formData.status === "active"}
                      onCheckedChange={(c) => setFormData({...formData, status: c ? "active" : "inactive"})}
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={closeDialog}>Cancel</Button>
                <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                  {editingParty ? "Save Changes" : "Create Party"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-card shadow-card rounded-2xl overflow-hidden border">
        <div className="p-4 border-b bg-muted/30">
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search specific party..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-white"
            />
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Name</TableHead>
              <TableHead>Contact</TableHead>
              <TableHead>City</TableHead>
              <TableHead className="text-right">Balance</TableHead>
              <TableHead className="text-center">Status</TableHead>
              <TableHead className="text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">Loading parties...</TableCell>
              </TableRow>
            ) : parties.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">No parties found.</TableCell>
              </TableRow>
            ) : (
              parties.map((party) => (
                <TableRow key={party.id} className="transition-colors hover:bg-muted/50 group">
                  <TableCell className="font-medium">{party.name}</TableCell>
                  <TableCell className="text-muted-foreground">{party.phone || "-"}</TableCell>
                  <TableCell className="text-muted-foreground">{party.city || "-"}</TableCell>
                  <TableCell className="text-right font-medium">
                    <span className={Number(party.opening_balance || 0) < 0 ? "text-red-600" : "text-emerald-600"}>
                      Rs {Math.abs(Number(party.opening_balance || 0)).toLocaleString()}
                    </span>
                    <span className="text-[10px] ml-1 font-bold text-slate-400">
                      {Number(party.opening_balance || 0) < 0 ? "Cr" : "Dr"}
                    </span>
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch 
                      checked={party.status === "active"} 
                      onCheckedChange={(c) => handleStatusToggle(party, c)}
                      disabled={updateMutation.isPending}
                    />
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => handleOpenDialog(party)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                        if(confirm('Are you sure you want to delete this party?')) {
                          deleteMutation.mutate(party.id);
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
  );
}
