import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wallet, Plus, Search, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { expensesApi, type Expense } from "@/lib/api-client";

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

export default function Expenses() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);

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
  const { data: expenses = [], isLoading } = useQuery({
    queryKey: ["expenses", search],
    queryFn: () => expensesApi.list(undefined, search),
  });

  // Create
  const createMutation = useMutation({
    mutationFn: (data: Omit<Expense, 'id' | 'created_at' | 'updated_at'>) => expensesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense created successfully");
      closeDialog();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Update
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Expense> }) => expensesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense updated successfully");
      closeDialog();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Delete
  const deleteMutation = useMutation({
    mutationFn: (id: number) => expensesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const handleOpenDialog = (expense?: Expense) => {
    if (expense) {
      setEditingExpense(expense);
      setFormData({
        name: expense.name,
        phone: expense.phone || "",
        address: expense.address || "",
        city: expense.city || "",
        opening_balance: Math.abs(expense.opening_balance || 0),
        balance_type: (expense.opening_balance || 0) < 0 ? "credit" : "debit",
        status: expense.status || "active",
      });
    } else {
      setEditingExpense(null);
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
    setEditingExpense(null);
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

    if (editingExpense) {
      updateMutation.mutate({ id: editingExpense.id!, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleStatusToggle = (expense: Expense, checked: boolean) => {
    const newStatus = checked ? "active" : "inactive";
    updateMutation.mutate({ id: expense.id!, data: { status: newStatus } });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <Wallet className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Expenses</h1>
            <p className="text-white/80 mt-1">Manage expense parties and opening balances.</p>
          </div>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()} className="bg-white text-primary hover:bg-white/90 shadow-md transition-all">
              <Plus className="mr-2 h-4 w-4" /> Add Expense Party
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <form onSubmit={handleSubmit}>
              <DialogHeader>
                <DialogTitle>{editingExpense ? "Edit Expense Party" : "Add New Expense Party"}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input 
                    id="name" 
                    value={formData.name} 
                    onChange={e => setFormData({...formData, name: e.target.value})} 
                    placeholder="E.g. Electricity Bill" 
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
                  {editingExpense ? "Save Changes" : "Create Expense Party"}
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
              placeholder="Search specific expense party..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-white"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="whitespace-nowrap">Name</TableHead>
                <TableHead className="whitespace-nowrap">Contact</TableHead>
                <TableHead className="whitespace-nowrap mobile-hide-column">City</TableHead>
                <TableHead className="text-right whitespace-nowrap">Balance</TableHead>
                <TableHead className="text-center whitespace-nowrap mobile-hide-column">Status</TableHead>
                <TableHead className="text-center whitespace-nowrap">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">Loading expenses...</TableCell>
                </TableRow>
              ) : expenses.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">No expenses found.</TableCell>
                </TableRow>
              ) : (
                expenses.map((expense) => (
                  <TableRow key={expense.id} className="transition-colors hover:bg-muted/50 group">
                    <TableCell className="font-medium whitespace-nowrap">{expense.name}</TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap">{expense.phone || "-"}</TableCell>
                    <TableCell className="text-muted-foreground whitespace-nowrap mobile-hide-column">{expense.city || "-"}</TableCell>
                    <TableCell className="text-right font-medium whitespace-nowrap">
                      <span className={Number(expense.balance || 0) < 0 ? "text-red-600" : "text-emerald-600"}>
                        Rs {Math.abs(Number(expense.balance || 0)).toLocaleString()}
                      </span>
                      <span className="text-[10px] ml-1 font-bold text-slate-400">
                        {Number(expense.balance || 0) < 0 ? "Cr" : "Dr"}
                      </span>
                    </TableCell>
                    <TableCell className="text-center mobile-hide-column">
                      <Switch 
                        checked={expense.status === "active"} 
                        onCheckedChange={(c) => handleStatusToggle(expense, c)}
                        disabled={updateMutation.isPending}
                      />
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => handleOpenDialog(expense)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" 
                          onClick={() => {
                            if(confirm('Are you sure you want to delete this expense party?')) {
                              if(expense.id) deleteMutation.mutate(expense.id);
                            }
                          }}
                        >
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
    </div>
  );
}
