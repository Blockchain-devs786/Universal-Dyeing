import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wallet, Plus, Search, Pencil, Trash2, Landmark, CreditCard } from "lucide-react";
import { toast } from "sonner";
import { accountsApi, type Account } from "@/lib/api-client";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
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

export default function Accounts() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    type: "Cash" as "Cash" | "Bank",
    account_number: "",
    bank_name: "",
    opening_balance: 0,
    status: "active",
  });

  // Fetch
  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts", search],
    queryFn: () => accountsApi.list(search),
  });

  // Create
  const createMutation = useMutation({
    mutationFn: (data: any) => accountsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account created successfully");
      setIsDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Update
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => accountsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account updated successfully");
      setIsDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Delete
  const deleteMutation = useMutation({
    mutationFn: (id: number) => accountsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const handleOpenDialog = (account?: Account) => {
    if (account) {
      setEditingAccount(account);
      setFormData({
        name: account.name,
        type: account.type,
        account_number: account.account_number || "",
        bank_name: account.bank_name || "",
        opening_balance: account.opening_balance || 0,
        status: account.status || "active",
      });
    } else {
      setEditingAccount(null);
      setFormData({
        name: "",
        type: "Cash",
        account_number: "",
        bank_name: "",
        opening_balance: 0,
        status: "active",
      });
    }
    setIsDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) return toast.error("Account name is required");

    if (editingAccount) {
      updateMutation.mutate({ id: editingAccount.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <Wallet className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Accounts Management</h1>
            <p className="text-white/80 mt-1">Define Cash and Bank accounts for financial transactions.</p>
          </div>
        </div>
        
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => handleOpenDialog()} className="bg-white text-primary hover:bg-white/90 shadow-md transition-all">
              <Plus className="mr-2 h-4 w-4" /> Add Account
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[450px]">
            <form onSubmit={handleSubmit}>
              <DialogHeader>
                <DialogTitle>{editingAccount ? "Edit Account" : "Add New Account"}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-5 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Account Type *</Label>
                    <Select 
                      value={formData.type} 
                      onValueChange={(v: "Cash" | "Bank") => setFormData({...formData, type: v})}
                    >
                      <SelectTrigger className="h-11">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Cash">Cash Account</SelectItem>
                        <SelectItem value="Bank">Bank Account</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="status">Status</Label>
                    <div className="flex items-center space-x-2 h-11 border rounded-md px-3 bg-slate-50">
                      <Switch 
                        checked={formData.status === "active"}
                        onCheckedChange={(c) => setFormData({...formData, status: c ? "active" : "inactive"})}
                      />
                      <span className="text-xs font-bold uppercase tracking-tighter">
                        {formData.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="name">Account Title / Name *</Label>
                  <Input 
                    id="name" 
                    value={formData.name} 
                    onChange={e => setFormData({...formData, name: e.target.value})} 
                    placeholder="E.g. Main Cash Vault or HBL Operating" 
                    required 
                    className="h-11"
                  />
                </div>

                {formData.type === "Bank" && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="bank_name">Bank Name</Label>
                      <Input 
                        id="bank_name" 
                        value={formData.bank_name} 
                        onChange={e => setFormData({...formData, bank_name: e.target.value})} 
                        placeholder="E.g. Habib Bank Limited" 
                        className="h-11"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="account_number">Account Number</Label>
                      <Input 
                        id="account_number" 
                        value={formData.account_number} 
                        onChange={e => setFormData({...formData, account_number: e.target.value})} 
                        placeholder="E.g. 0123-4567-8901" 
                        className="h-11"
                      />
                    </div>
                  </>
                )}

                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 space-y-2">
                   <Label htmlFor="opening_balance" className="text-emerald-800 font-bold uppercase text-[10px] tracking-widest">Initial Opening Balance</Label>
                   <Input 
                    id="opening_balance" 
                    type="number" 
                    step="0.01" 
                    value={formData.opening_balance} 
                    onChange={e => setFormData({...formData, opening_balance: parseFloat(e.target.value) || 0})} 
                    className="h-12 text-xl font-black bg-white border-emerald-200 focus:ring-emerald-500"
                    disabled={!!editingAccount} // Prevent changing opening balance after creation for audit integrity
                  />
                  {editingAccount && <p className="text-[10px] text-emerald-600 font-medium italic">* Opening balance cannot be edited after creation.</p>}
                </div>
              </div>
              <DialogFooter className="pt-4 border-t">
                <Button type="button" variant="ghost" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
                <Button type="submit" className="bg-primary px-8" disabled={createMutation.isPending || updateMutation.isPending}>
                  {editingAccount ? "Update Account" : "Create Account"}
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
              placeholder="Search accounts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-white"
            />
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent bg-slate-50/50">
              <TableHead className="w-[30%]">Account Detail</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Account #</TableHead>
              <TableHead className="text-right">Balance</TableHead>
              <TableHead className="text-center">Status</TableHead>
              <TableHead className="text-right px-6">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-20">
                  <div className="flex flex-col items-center gap-2 animate-pulse">
                    <Wallet className="h-10 w-10 text-muted-foreground/30" />
                    <p className="text-muted-foreground font-medium">Loading accounts...</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : accounts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-20 text-muted-foreground">
                  <div className="flex flex-col items-center gap-2">
                    <Wallet className="h-10 w-10 text-muted-foreground/20" />
                    <p>No accounts defined yet.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              accounts.map((account) => (
                <TableRow key={account.id} className="transition-colors hover:bg-muted/30 group">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "p-2.5 rounded-xl border shadow-sm",
                        account.type === 'Cash' ? "bg-amber-50 text-amber-600 border-amber-100" : "bg-blue-50 text-blue-600 border-blue-100"
                      )}>
                        {account.type === 'Cash' ? <CreditCard className="h-4 w-4" /> : <Landmark className="h-4 w-4" />}
                      </div>
                      <div>
                        <p className="font-bold text-slate-800 leading-none mb-1">{account.name}</p>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tight">{account.bank_name || 'Physical Cash'}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={cn(
                      "font-bold text-[10px] uppercase",
                      account.type === 'Cash' ? "text-amber-600 border-amber-200 bg-amber-50" : "text-blue-600 border-blue-200 bg-blue-50"
                    )}>
                      {account.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-slate-500">
                    {account.account_number || "-"}
                  </TableCell>
                  <TableCell className="text-right font-black text-slate-900 tabular-nums">
                    <div className="flex flex-col items-end">
                      <span>Rs {Number(account.current_balance).toLocaleString()}</span>
                      <span className="text-[9px] text-slate-400 uppercase tracking-tighter font-bold">Current</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <div className={cn(
                      "inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider",
                      account.status === "active" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                    )}>
                      {account.status}
                    </div>
                  </TableCell>
                  <TableCell className="text-right px-6">
                    <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:bg-blue-50" onClick={() => handleOpenDialog(account)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:bg-red-50" onClick={() => {
                        if(confirm(`Delete account "${account.name}"? This action cannot be undone.`)) {
                          deleteMutation.mutate(account.id);
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
