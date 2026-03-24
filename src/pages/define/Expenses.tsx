import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Wallet, Plus, Search, Pencil, Trash2, FolderEdit } from "lucide-react";
import { toast } from "sonner";
import { expenseCategoriesApi, expensesApi, type ExpenseCategory, type Expense } from "@/lib/api-client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

export default function Expenses() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("expenses");

  // Search States
  const [expenseSearch, setExpenseSearch] = useState("");
  const [categorySearch, setCategorySearch] = useState("");

  // Dialog States
  const [isExpenseDialogOpen, setIsExpenseDialogOpen] = useState(false);
  const [isCategoryDialogOpen, setIsCategoryDialogOpen] = useState(false);

  // Edit States
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [editingCategory, setEditingCategory] = useState<ExpenseCategory | null>(null);

  // Form States
  const [expenseForm, setExpenseForm] = useState({
    name: "",
    category_id: "",
    description: "",
    status: "active",
  });

  const [categoryForm, setCategoryForm] = useState({
    name: "",
    description: "",
    status: "active",
  });

  // ─── Queries ────────────────────────────────────────────────────────

  const { data: categories = [], isLoading: isLoadingCategories } = useQuery({
    queryKey: ["expense_categories", categorySearch],
    queryFn: () => expenseCategoriesApi.list(categorySearch),
  });

  const { data: expenses = [], isLoading: isLoadingExpenses } = useQuery({
    queryKey: ["expenses", expenseSearch],
    queryFn: () => expensesApi.list(undefined, expenseSearch),
  });

  // ─── Mutations (Categories) ─────────────────────────────────────────

  const createCategoryMutation = useMutation({
    mutationFn: (data: Omit<ExpenseCategory, 'id' | 'created_at' | 'updated_at'>) => expenseCategoriesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expense_categories"] });
      toast.success("Category created successfully");
      setIsCategoryDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateCategoryMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ExpenseCategory> }) => expenseCategoriesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expense_categories"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] }); // Names might update
      toast.success("Category updated successfully");
      setIsCategoryDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteCategoryMutation = useMutation({
    mutationFn: (id: number) => expenseCategoriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expense_categories"] });
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Category deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // ─── Mutations (Expenses) ───────────────────────────────────────────

  const createExpenseMutation = useMutation({
    mutationFn: (data: Omit<Expense, 'id' | 'category_name' | 'created_at' | 'updated_at'>) => expensesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense created successfully");
      setIsExpenseDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateExpenseMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Expense> }) => expensesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense updated successfully");
      setIsExpenseDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteExpenseMutation = useMutation({
    mutationFn: (id: number) => expensesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["expenses"] });
      toast.success("Expense deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // ─── Handlers (Categories) ──────────────────────────────────────────

  const openCategoryDialog = (cat?: ExpenseCategory) => {
    if (cat) {
      setEditingCategory(cat);
      setCategoryForm({ name: cat.name, description: cat.description || "", status: cat.status });
    } else {
      setEditingCategory(null);
      setCategoryForm({ name: "", description: "", status: "active" });
    }
    setIsCategoryDialogOpen(true);
  };

  const handleCategorySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryForm.name) return toast.error("Category name is required");

    if (editingCategory) {
      updateCategoryMutation.mutate({ id: editingCategory.id, data: categoryForm });
    } else {
      createCategoryMutation.mutate(categoryForm);
    }
  };

  const toggleCategoryStatus = (cat: ExpenseCategory, checked: boolean) => {
    updateCategoryMutation.mutate({ id: cat.id, data: { status: checked ? "active" : "inactive" } });
  };

  // ─── Handlers (Expenses) ────────────────────────────────────────────

  const openExpenseDialog = (exp?: Expense) => {
    if (exp) {
      setEditingExpense(exp);
      setExpenseForm({ 
        name: exp.name, 
        category_id: String(exp.category_id), 
        description: exp.description || "", 
        status: exp.status 
      });
    } else {
      setEditingExpense(null);
      setExpenseForm({ name: "", category_id: "", description: "", status: "active" });
    }
    setIsExpenseDialogOpen(true);
  };

  const handleExpenseSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!expenseForm.name) return toast.error("Expense name is required");
    if (!expenseForm.category_id) return toast.error("Please select a category");

    const payload = {
      ...expenseForm,
      category_id: parseInt(expenseForm.category_id, 10)
    };

    if (editingExpense) {
      updateExpenseMutation.mutate({ id: editingExpense.id, data: payload });
    } else {
      createExpenseMutation.mutate(payload);
    }
  };

  const toggleExpenseStatus = (exp: Expense, checked: boolean) => {
    updateExpenseMutation.mutate({ id: exp.id, data: { status: checked ? "active" : "inactive" } });
  };

  // ─── Render ─────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <Wallet className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Expenses</h1>
            <p className="text-white/80 mt-1">Manage expense categories and items.</p>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full sm:w-[400px] grid-cols-2 mb-6">
          <TabsTrigger value="expenses">Expense Items</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
        </TabsList>

        {/* ─── EXPENSES TAB ──────────────────────────────────────────────── */}
        <TabsContent value="expenses" className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="relative max-w-sm w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search expenses by name..."
                value={expenseSearch}
                onChange={(e) => setExpenseSearch(e.target.value)}
                className="pl-9 bg-white"
              />
            </div>
            
            <Dialog open={isExpenseDialogOpen} onOpenChange={setIsExpenseDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={() => openExpenseDialog()} className="bg-primary text-white shadow-md">
                  <Plus className="mr-2 h-4 w-4" /> Add Expense
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <form onSubmit={handleExpenseSubmit}>
                  <DialogHeader>
                    <DialogTitle>{editingExpense ? "Edit Expense" : "Add New Expense"}</DialogTitle>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label>Category *</Label>
                      <Select 
                        value={expenseForm.category_id} 
                        onValueChange={(val) => setExpenseForm({...expenseForm, category_id: val})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select a category" />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map((cat) => (
                            <SelectItem key={cat.id} value={String(cat.id)}>
                              {cat.name} {cat.status !== 'active' && '(Inactive)'}
                            </SelectItem>
                          ))}
                          {categories.length === 0 && (
                            <div className="p-2 text-sm text-muted-foreground">No categories found. Please add a category first.</div>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="exp-name">Expense Name *</Label>
                      <Input 
                        id="exp-name" 
                        value={expenseForm.name} 
                        onChange={e => setExpenseForm({...expenseForm, name: e.target.value})} 
                        placeholder="E.g. Office Rent" 
                        required 
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="exp-desc">Description</Label>
                      <Input 
                        id="exp-desc" 
                        value={expenseForm.description} 
                        onChange={e => setExpenseForm({...expenseForm, description: e.target.value})} 
                        placeholder="Optional description" 
                      />
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <Label htmlFor="exp-status">Status</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">{expenseForm.status === 'active' ? 'Active' : 'Inactive'}</span>
                        <Switch 
                          id="exp-status" 
                          checked={expenseForm.status === "active"}
                          onCheckedChange={(c) => setExpenseForm({...expenseForm, status: c ? "active" : "inactive"})}
                        />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setIsExpenseDialogOpen(false)}>Cancel</Button>
                    <Button type="submit" disabled={createExpenseMutation.isPending || updateExpenseMutation.isPending}>
                      {editingExpense ? "Save Changes" : "Create Expense"}
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
                  <TableHead>Expense Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="hidden md:table-cell">Description</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoadingExpenses ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-10 text-muted-foreground">Loading expenses...</TableCell>
                  </TableRow>
                ) : expenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-10 text-muted-foreground">
                      No expenses found. Add categories first, then add expenses.
                    </TableCell>
                  </TableRow>
                ) : (
                  expenses.map((expense) => (
                    <TableRow key={expense.id} className="transition-colors hover:bg-muted/50 group">
                      <TableCell className="font-medium">{expense.name}</TableCell>
                      <TableCell>
                        <span className="bg-primary/10 text-primary border border-primary/20 px-2 py-1 rounded-md text-xs font-semibold uppercase tracking-wider">
                          {expense.category_name}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground hidden md:table-cell">{expense.description || "-"}</TableCell>
                      <TableCell className="text-center">
                        <Switch 
                          checked={expense.status === "active"} 
                          onCheckedChange={(c) => toggleExpenseStatus(expense, c)}
                          disabled={updateExpenseMutation.isPending}
                        />
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => openExpenseDialog(expense)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                            if(confirm('Are you sure you want to delete this expense?')) {
                              deleteExpenseMutation.mutate(expense.id);
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
        </TabsContent>

        {/* ─── CATEGORIES TAB ────────────────────────────────────────────── */}
        <TabsContent value="categories" className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="relative max-w-sm w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search categories..."
                value={categorySearch}
                onChange={(e) => setCategorySearch(e.target.value)}
                className="pl-9 bg-white"
              />
            </div>
            
            <Dialog open={isCategoryDialogOpen} onOpenChange={setIsCategoryDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={() => openCategoryDialog()} className="bg-secondary text-secondary-foreground hover:bg-secondary/80 shadow-md">
                  <FolderEdit className="mr-2 h-4 w-4" /> Add Category
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <form onSubmit={handleCategorySubmit}>
                  <DialogHeader>
                    <DialogTitle>{editingCategory ? "Edit Category" : "Add New Category"}</DialogTitle>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="cat-name">Category Name *</Label>
                      <Input 
                        id="cat-name" 
                        value={categoryForm.name} 
                        onChange={e => setCategoryForm({...categoryForm, name: e.target.value})} 
                        placeholder="E.g. Travel, Utilities" 
                        required 
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="cat-desc">Description</Label>
                      <Input 
                        id="cat-desc" 
                        value={categoryForm.description} 
                        onChange={e => setCategoryForm({...categoryForm, description: e.target.value})} 
                        placeholder="Optional description" 
                      />
                    </div>
                    <div className="flex items-center justify-between mt-2">
                      <Label htmlFor="cat-status">Status</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">{categoryForm.status === 'active' ? 'Active' : 'Inactive'}</span>
                        <Switch 
                          id="cat-status" 
                          checked={categoryForm.status === "active"}
                          onCheckedChange={(c) => setCategoryForm({...categoryForm, status: c ? "active" : "inactive"})}
                        />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setIsCategoryDialogOpen(false)}>Cancel</Button>
                    <Button type="submit" disabled={createCategoryMutation.isPending || updateCategoryMutation.isPending}>
                      {editingCategory ? "Save Changes" : "Create Category"}
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
                  <TableHead>Category Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoadingCategories ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center py-10 text-muted-foreground">Loading categories...</TableCell>
                  </TableRow>
                ) : categories.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center py-10 text-muted-foreground">No categories found.</TableCell>
                  </TableRow>
                ) : (
                  categories.map((cat) => (
                    <TableRow key={cat.id} className="transition-colors hover:bg-muted/50 group">
                      <TableCell className="font-semibold text-primary">{cat.name}</TableCell>
                      <TableCell className="text-muted-foreground">{cat.description || "-"}</TableCell>
                      <TableCell className="text-center">
                        <Switch 
                          checked={cat.status === "active"} 
                          onCheckedChange={(c) => toggleCategoryStatus(cat, c)}
                          disabled={updateCategoryMutation.isPending}
                        />
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => openCategoryDialog(cat)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                            if(confirm('Warning: Deleting this category will delete all expenses inside it! Are you sure?')) {
                              deleteCategoryMutation.mutate(cat.id);
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
        </TabsContent>
      </Tabs>
    </div>
  );
}
