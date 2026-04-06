import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  Users, 
  UserPlus, 
  Mail, 
  User as UserIcon, 
  Lock, 
  ShieldCheck, 
  RefreshCw,
  AlertCircle,
  Pencil,
  Trash2,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  Check
} from "lucide-react";
import { authApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const AVAILABLE_MODULES = [
  { id: "define_ms_parties", label: "Define: MS Parties" },
  { id: "define_from_parties", label: "Define: From Parties" },
  { id: "define_suppliers", label: "Define: Suppliers" },
  { id: "define_items", label: "Define: Items" },
  { id: "define_assets", label: "Define: Assets" },
  { id: "define_expenses", label: "Define: Expenses" },
  { id: "define_accounts", label: "Define: Accounts" },
  { id: "inward", label: "Inward Entry" },
  { id: "outward", label: "Outward Entry" },
  { id: "transfer", label: "Transfer Stocks" },
  { id: "transfer_by_name", label: "Transfer By Name" },
  { id: "invoice", label: "Invoices" },
  { id: "vouchers", label: "Vouchers" },
  { id: "reports_stocks", label: "Stock Reports" },
  { id: "reports_ledger", label: "Ledgers" },
];

export default function UserManagement() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [selectedModules, setSelectedModules] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState("");

  const [editingUser, setEditingUser] = useState<any>(null);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);

  const queryClient = useQueryClient();

  const { data: users = [], isLoading: isLoadingUsers } = useQuery({
    queryKey: ["users"],
    queryFn: () => authApi.listUsers(),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => authApi.createUser(data),
    onSuccess: () => {
      toast.success("User created successfully!");
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to create user.");
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => authApi.updateUser(data),
    onSuccess: () => {
      toast.success("User updated successfully!");
      setIsEditDialogOpen(false);
      setEditingUser(null);
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to update user.");
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => authApi.deleteUser(id),
    onSuccess: () => {
      toast.success("User deleted successfully!");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to delete user.");
    }
  });

  const verifyManuallyMutation = useMutation({
    mutationFn: (id: number) => authApi.verifyManually(id),
    onSuccess: () => {
      toast.success("Account verified manually!");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: any) => {
      toast.error(error.message || "Manual verification failed.");
    }
  });

  const resetForm = () => {
    setEmail("");
    setUsername("");
    setPassword("");
    setRole("user");
    setSelectedModules([]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !username || !password) {
      toast.error("Please fill all required fields.");
      return;
    }
    
    const moduleAccess = role === "admin" ? "all" : selectedModules.join(",");
    createMutation.mutate({ 
      email, 
      username, 
      password, 
      role, 
      module_access: moduleAccess 
    });
  };

  const handleEdit = (user: any) => {
    setEditingUser({
      ...user,
      password: "", // Keep password empty unless changing
      module_access_list: user.module_access === "all" ? AVAILABLE_MODULES.map(m => m.id) : user.module_access.split(",")
    });
    setIsEditDialogOpen(true);
  };

  const handleUpdate = () => {
    const moduleAccess = editingUser.role === "admin" ? "all" : editingUser.module_access_list.join(",");
    updateMutation.mutate({
      ...editingUser,
      module_access: moduleAccess
    });
  };

  const filteredUsers = users.filter(u => 
    u.username.toLowerCase().includes(searchTerm.toLowerCase()) || 
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleModule = (id: string) => {
    setSelectedModules(prev => 
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    );
  };

  return (
    <div className="p-4 sm:p-6 space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-blue-600/10 rounded-xl">
            <Users className="h-8 w-8 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-900 uppercase">Universal Auth</h1>
            <p className="text-slate-500 text-sm mt-0.5 font-medium">Manage system access, roles and module permissions.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Left Column: Create User Form */}
        <div className="xl:col-span-5 space-y-6">
          <Card className="shadow-premium border-none overflow-hidden">
            <CardHeader className="bg-slate-900 py-6">
              <CardTitle className="text-white text-lg flex items-center gap-2">
                  <UserPlus className="h-5 w-5" /> Account Registration
              </CardTitle>
              <CardDescription className="text-slate-400">Add a new verified member to your organization.</CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="pt-6 space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="username" className="text-[10px] font-black uppercase text-slate-500">Username</Label>
                  <Input 
                    id="username" 
                    placeholder="e.g., malik_dyeing" 
                    value={username} 
                    onChange={e => setUsername(e.target.value)}
                    className="h-10 border-slate-200 bg-slate-50/50"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-[10px] font-black uppercase text-slate-500">Email Address</Label>
                  <Input 
                    id="email" 
                    type="email" 
                    placeholder="user@organization.com" 
                    value={email} 
                    onChange={e => setEmail(e.target.value)}
                    className="h-10 border-slate-200 bg-slate-50/50"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="role" className="text-[10px] font-black uppercase text-slate-500">System Role</Label>
                    <Select value={role} onValueChange={setRole}>
                      <SelectTrigger className="h-10 border-slate-200 bg-slate-50/50">
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="user">Standard User</SelectItem>
                        <SelectItem value="manager">Manager</SelectItem>
                        <SelectItem value="admin">Administrator</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password" className="text-[10px] font-black uppercase text-slate-500">Password</Label>
                    <Input 
                      id="password" 
                      type="password" 
                      placeholder="••••••••" 
                      value={password} 
                      onChange={e => setPassword(e.target.value)}
                      className="h-10 border-slate-200 bg-slate-50/50"
                    />
                  </div>
                </div>

                {role !== "admin" && (
                  <div className="space-y-3 pt-4 border-t border-slate-100">
                    <Label className="text-[10px] font-black uppercase text-slate-500">Module Access Control</Label>
                    <div className="max-h-[220px] overflow-y-auto pr-2 custom-scrollbar">
                        <div className="grid grid-cols-2 gap-y-3 gap-x-4">
                        {AVAILABLE_MODULES.map(module => (
                            <div key={module.id} className="flex items-center space-x-2">
                            <Checkbox 
                                id={module.id} 
                                checked={selectedModules.includes(module.id)}
                                onCheckedChange={() => toggleModule(module.id)}
                                className="data-[state=checked]:bg-blue-600 border-slate-300"
                            />
                            <label htmlFor={module.id} className="text-xs font-semibold text-slate-600 cursor-pointer">{module.label}</label>
                            </div>
                        ))}
                        </div>
                    </div>
                  </div>
                )}

                {role === "admin" && (
                    <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl flex gap-3 animate-in slide-in-from-top-2">
                        <ShieldCheck className="h-5 w-5 text-blue-600 shrink-0" />
                        <p className="text-[11px] text-blue-800 leading-normal font-medium">
                            <strong>Note:</strong> Administrators have unrestricted access to all modules automatically.
                        </p>
                    </div>
                )}
              </CardContent>
              <CardFooter className="bg-slate-50 border-t p-4 sm:p-6">
                <Button 
                    type="submit" 
                    className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg"
                    disabled={createMutation.isPending}
                >
                    {createMutation.isPending ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <UserPlus className="mr-2 h-4 w-4" />}
                    Authorize User 
                </Button>
              </CardFooter>
            </form>
          </Card>
        </div>

        {/* Right Column: User List */}
        <div className="xl:col-span-7 space-y-6">
          <Card className="shadow-premium border-none">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div>
                <CardTitle className="text-xl font-bold text-slate-900 flex items-center gap-2">
                    <Users className="h-6 w-6 text-blue-600" /> Active Users
                </CardTitle>
                <CardDescription>View and manage already registered accounts.</CardDescription>
              </div>
              <div className="relative w-48 sm:w-64">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input 
                        placeholder="Search profiles..." 
                        value={searchTerm}
                        onChange={e => setSearchTerm(e.target.value)}
                        className="pl-9 h-10 border-slate-200 bg-slate-50"
                    />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-slate-50">
                    <TableRow>
                      <TableHead className="text-[10px] font-black uppercase text-slate-500 pl-6 whitespace-nowrap">Profile</TableHead>
                      <TableHead className="text-[10px] font-black uppercase text-slate-500 whitespace-nowrap">Status</TableHead>
                      <TableHead className="text-[10px] font-black uppercase text-slate-500 whitespace-nowrap mobile-hide-column">Modules</TableHead>
                      <TableHead className="text-right text-[10px] font-black uppercase text-slate-500 pr-6 whitespace-nowrap">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                <TableBody>
                  {isLoadingUsers ? (
                    <TableRow>
                      <TableCell colSpan={4} className="h-64 text-center">
                        <RefreshCw className="h-8 w-8 text-blue-600 animate-spin mx-auto opacity-20" />
                      </TableCell>
                    </TableRow>
                  ) : filteredUsers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} className="h-64 text-center text-slate-400 italic font-medium">
                        No users found coordinating with your search.
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredUsers.map((user) => (
                      <TableRow key={user.id} className="hover:bg-slate-50 transition-colors group">
                        <TableCell className="pl-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-10 w-10 rounded-xl bg-slate-100 flex items-center justify-center font-bold text-slate-600 uppercase border border-slate-200">
                                {user.username.substring(0, 1)}
                            </div>
                            <div>
                                <p className="font-bold text-slate-900 text-sm">{user.username}</p>
                                <p className="text-xs text-slate-500">{user.email}</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                            <div className="flex flex-col gap-1">
                                <span className={`w-fit px-2 py-0.5 rounded-full text-[10px] font-black uppercase ${
                                    user.role === 'admin' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                                }`}>
                                    {user.role}
                                </span>
                                {user.is_verified ? (
                                    <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold"><CheckCircle2 className="h-3 w-3" /> VERIFIED</span>
                                ) : (
                                    <span className="flex items-center gap-1 text-[10px] text-amber-600 font-bold"><RefreshCw className="h-3 w-3" /> PENDING</span>
                                )}
                            </div>
                        </TableCell>
                        <TableCell className="mobile-hide-column">
                            <div className="max-w-[150px] truncate text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-1 rounded">
                                {user.module_access === 'all' ? 'ALL ACCESS' : user.module_access.replace(/_/g, ' ').toUpperCase() || 'NO ACCESS'}
                            </div>
                        </TableCell>
                        <TableCell className="pr-6 text-right space-x-2">
                          {!user.is_verified && (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-9 w-9 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                              onClick={() => {
                                  if(confirm(`Do you want to manually verify ${user.username}'s account? This bypasses the email check.`)) {
                                      verifyManuallyMutation.mutate(user.id);
                                  }
                              }}
                              title="Verify Manually"
                            >
                              <ShieldCheck className="h-4 w-4" />
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-9 w-9 text-slate-500 hover:text-blue-600 hover:bg-blue-50"
                            onClick={() => handleEdit(user)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-9 w-9 text-slate-500 hover:text-red-600 hover:bg-red-50"
                            onClick={() => {
                                if(confirm('Are you sure you want to delete this account?')) {
                                    deleteMutation.mutate(user.id);
                                }
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit User Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-xl border-none shadow-2xl p-0 overflow-hidden">
          <DialogHeader className="bg-slate-900 text-white p-6">
            <DialogTitle>Edit User Profile</DialogTitle>
            <DialogDescription className="text-slate-400">Modify credentials or module access permissions.</DialogDescription>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-y-auto custom-scrollbar">
            {editingUser && (
                <div className="p-6 space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label className="text-[10px] font-black uppercase text-slate-500">Username</Label>
                        <Input 
                            value={editingUser.username} 
                            onChange={e => setEditingUser({...editingUser, username: e.target.value})}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label className="text-[10px] font-black uppercase text-slate-500">Email</Label>
                        <Input 
                            value={editingUser.email} 
                            onChange={e => setEditingUser({...editingUser, email: e.target.value})}
                        />
                    </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label className="text-[10px] font-black uppercase text-slate-500">Change Password (Optional)</Label>
                            <Input 
                                type="password" 
                                placeholder="Type to change..." 
                                value={editingUser.password}
                                onChange={e => setEditingUser({...editingUser, password: e.target.value})}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label className="text-[10px] font-black uppercase text-slate-500">Role</Label>
                            <Select value={editingUser.role} onValueChange={r => setEditingUser({...editingUser, role: r})}>
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="user">User</SelectItem>
                                    <SelectItem value="manager">Manager</SelectItem>
                                    <SelectItem value="admin">Admin</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {editingUser.role !== "admin" && (
                    <div className="space-y-3">
                        <Label className="text-[10px] font-black uppercase text-slate-500">Update Module Access</Label>
                        <div className="max-h-52 overflow-y-auto pr-2 custom-scrollbar">
                            <div className="grid grid-cols-2 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-100">
                            {AVAILABLE_MODULES.map(module => (
                                <div key={module.id} className="flex items-center space-x-2">
                                <Checkbox 
                                    id={`edit-${module.id}`} 
                                    checked={editingUser.module_access_list.includes(module.id)}
                                    onCheckedChange={() => {
                                        const list = editingUser.module_access_list;
                                        const newList = list.includes(module.id) 
                                            ? list.filter((m: string) => m !== module.id) 
                                            : [...list, module.id];
                                        setEditingUser({...editingUser, module_access_list: newList});
                                    }}
                                />
                                <label htmlFor={`edit-${module.id}`} className="text-xs font-semibold text-slate-600">{module.label}</label>
                                </div>
                            ))}
                            </div>
                        </div>
                    </div>
                    )}
                </div>
            )}
          </div>
          <DialogFooter className="bg-slate-100 border-t p-4 px-6 flex justify-between gap-4">
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)} className="border-slate-300">Cancel</Button>
            <Button onClick={handleUpdate} className="bg-blue-600 hover:bg-blue-700 text-white font-bold" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
                Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
