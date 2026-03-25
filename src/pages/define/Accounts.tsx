import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wallet, Plus, Search, Pencil, Trash2, Building2, Banknote } from "lucide-react";
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

  const [form, setForm] = useState({
    name: "",
    type: "Cash" as "Cash" | "Bank",
    account_no: "",
    bank_name: "",
    opening_balance: 0,
    status: "active",
  });

  // Queries
  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts", search],
    queryFn: () => accountsApi.list(search),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: any) => accountsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account created successfully");
      setIsDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => accountsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account updated successfully");
      setIsDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => accountsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      toast.success("Account deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // Handlers
  const openDialog = (account?: Account) => {
    if (account) {
      setEditingAccount(account);
      setForm({
        name: account.name,
        type: account.type,
        account_no: account.account_no || "",
        bank_name: account.bank_name || "",
        opening_balance: account.opening_balance,
        status: account.status,
      });
    } else {
      setEditingAccount(null);
      setForm({
        name: "",
        type: "Cash",
        account_no: "",
        bank_name: "",
        opening_balance: 0,
        status: "active",
      });
    }
    setIsDialogOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name) return toast.error("Account name is required");

    if (editingAccount) {
      updateMutation.mutate({ id: editingAccount.id, data: form });
    } else {
      createMutation.mutate(form);
    }
  };

  const toggleStatus = (account: Account, checked: boolean) => {
    updateMutation.mutate({ 
      id: account.id, 
      data: { ...account, status: checked ? "active" : "inactive" } 
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <Wallet className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Accounts</h1>
            <p className="text-white/80 mt-1">Manage cash and bank accounts.</p>
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center gap-4">
        <div className="relative max-w-sm w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search accounts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 bg-white"
          />
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => openDialog()} className="bg-primary text-white shadow-md">
              <Plus className="mr-2 h-4 w-4" /> Add Account
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <form onSubmit={handleSubmit}>
              <DialogHeader>
                <DialogTitle>{editingAccount ? "Edit Account" : "Add New Account"}</DialogTitle>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="type">Account Type</Label>
                  <Select 
                    value={form.type} 
                    onValueChange={(val: any) => setForm({...form, type: val})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Cash">Cash Account</SelectItem>
                      <SelectItem value="Bank">Bank Account</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="name">Account Name *</Label>
                  <Input 
                    id="name" 
                    value={form.name} 
                    onChange={e => setForm({...form, name: e.target.value})} 
                    placeholder="E.g. Main Cash Vault, HBL Operations" 
                    required 
                  />
                </div>

                {form.type === "Bank" && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="bank_name">Bank Name</Label>
                      <Input 
                        id="bank_name" 
                        value={form.bank_name} 
                        onChange={e => setForm({...form, bank_name: e.target.value})} 
                        placeholder="E.g. HBL, MCB" 
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="account_no">Account Number</Label>
                      <Input 
                        id="account_no" 
                        value={form.account_no} 
                        onChange={e => setForm({...form, account_no: e.target.value})} 
                        placeholder="Optional" 
                      />
                    </div>
                  </>
                )}

                <div className="space-y-2">
                  <Label htmlFor="opening_balance">Opening Balance</Label>
                  <Input 
                    id="opening_balance" 
                    type="number"
                    value={form.opening_balance} 
                    onChange={e => setForm({...form, opening_balance: parseFloat(e.target.value) || 0})} 
                  />
                </div>

                <div className="flex items-center justify-between mt-2">
                  <Label htmlFor="status">Status</Label>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-muted-foreground">{form.status === 'active' ? 'Active' : 'Inactive'}</span>
                    <Switch 
                      id="status" 
                      checked={form.status === "active"}
                      onCheckedChange={(c) => setForm({...form, status: c ? "active" : "inactive"})}
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                  {editingAccount ? "Save Changes" : "Create Account"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-card shadow-card rounded-2xl overflow-hidden border">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent bg-muted/30">
              <TableHead className="w-[80px] text-center">Type</TableHead>
              <TableHead>Account Details</TableHead>
              <TableHead>Bank / Branch</TableHead>
              <TableHead className="text-right">Balance</TableHead>
              <TableHead className="text-center">Status</TableHead>
              <TableHead className="text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-10 text-muted-foreground animate-pulse">
                  Loading accounts...
                </TableCell>
              </TableRow>
            ) : accounts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-20 text-muted-foreground">
                  <div className="flex flex-col items-center gap-2">
                    <Wallet className="h-10 w-10 opacity-20" />
                    <p>No accounts found. Add your first cash or bank account.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              accounts.map((account) => (
                <TableRow key={account.id} className="transition-colors hover:bg-muted/50 group">
                  <TableCell className="text-center">
                    {account.type === "Cash" ? (
                      <div className="p-2 bg-amber-50 rounded-lg inline-block">
                        <Banknote className="h-5 w-5 text-amber-600" />
                      </div>
                    ) : (
                      <div className="p-2 bg-blue-50 rounded-lg inline-block">
                        <Building2 className="h-5 w-5 text-blue-600" />
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-bold text-slate-800">{account.name}</span>
                      {account.account_no && (
                        <span className="text-[10px] text-slate-400 font-mono">#{account.account_no}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-slate-600 font-medium whitespace-nowrap">
                    {account.bank_name || "-"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex flex-col">
                      <span className="text-lg font-black text-emerald-600 leading-none">
                        Rs {Number(account.current_balance).toLocaleString()}
                      </span>
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter mt-1">
                        Opening: {Number(account.opening_balance).toLocaleString()}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge 
                      variant="outline" 
                      className={cn(
                        "rounded-full uppercase text-[10px] font-bold",
                        account.status === 'active' ? "border-emerald-500 text-emerald-600 bg-emerald-50" : "border-slate-300 text-slate-500 bg-slate-50"
                      )}
                    >
                      {account.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => openDialog(account)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                        if(confirm('Are you sure you want to delete this account?')) {
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
