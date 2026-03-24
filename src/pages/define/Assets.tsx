import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HardDrive, Plus, Search, Pencil, Trash2, FolderEdit } from "lucide-react";
import { toast } from "sonner";
import { assetCategoriesApi, assetsApi, type AssetCategory, type Asset } from "@/lib/api-client";

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

export default function Assets() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("assets");

  // Search States
  const [assetSearch, setAssetSearch] = useState("");
  const [categorySearch, setCategorySearch] = useState("");

  // Dialog States
  const [isAssetDialogOpen, setIsAssetDialogOpen] = useState(false);
  const [isCategoryDialogOpen, setIsCategoryDialogOpen] = useState(false);

  // Edit States
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const [editingCategory, setEditingCategory] = useState<AssetCategory | null>(null);

  // Form States
  const [assetForm, setAssetForm] = useState({
    name: "",
    category_id: "",
    description: "",
    value: 0,
    location: "",
    purchase_date: "",
    status: "active",
  });

  const [categoryForm, setCategoryForm] = useState({
    name: "",
    description: "",
    status: "active",
  });

  // ─── Queries ────────────────────────────────────────────────────────

  const { data: categories = [], isLoading: isLoadingCategories } = useQuery({
    queryKey: ["asset_categories", categorySearch],
    queryFn: () => assetCategoriesApi.list(categorySearch),
  });

  const { data: assets = [], isLoading: isLoadingAssets } = useQuery({
    queryKey: ["assets", assetSearch],
    queryFn: () => assetsApi.list(undefined, assetSearch),
  });

  // ─── Mutations (Categories) ─────────────────────────────────────────

  const createCategoryMutation = useMutation({
    mutationFn: (data: Omit<AssetCategory, 'id' | 'created_at' | 'updated_at'>) => assetCategoriesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset_categories"] });
      toast.success("Category created successfully");
      setIsCategoryDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateCategoryMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<AssetCategory> }) => assetCategoriesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset_categories"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Category updated successfully");
      setIsCategoryDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteCategoryMutation = useMutation({
    mutationFn: (id: number) => assetCategoriesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["asset_categories"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Category deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // ─── Mutations (Assets) ───────────────────────────────────────────

  const createAssetMutation = useMutation({
    mutationFn: (data: Omit<Asset, 'id' | 'category_name' | 'created_at' | 'updated_at'>) => assetsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset created successfully");
      setIsAssetDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const updateAssetMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Asset> }) => assetsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset updated successfully");
      setIsAssetDialogOpen(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const deleteAssetMutation = useMutation({
    mutationFn: (id: number) => assetsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset deleted successfully");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  // ─── Handlers (Categories) ──────────────────────────────────────────

  const openCategoryDialog = (cat?: AssetCategory) => {
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

  const toggleCategoryStatus = (cat: AssetCategory, checked: boolean) => {
    updateCategoryMutation.mutate({ id: cat.id, data: { status: checked ? "active" : "inactive" } });
  };

  // ─── Handlers (Assets) ────────────────────────────────────────────

  const openAssetDialog = (asset?: Asset) => {
    if (asset) {
      setEditingAsset(asset);
      setAssetForm({ 
        name: asset.name, 
        category_id: asset.category_id ? String(asset.category_id) : "none", 
        description: asset.description || "", 
        value: asset.value || 0,
        location: asset.location || "",
        purchase_date: asset.purchase_date ? asset.purchase_date.split('T')[0] : "",
        status: asset.status 
      });
    } else {
      setEditingAsset(null);
      setAssetForm({ 
        name: "", 
        category_id: "none", 
        description: "", 
        value: 0,
        location: "",
        purchase_date: "",
        status: "active" 
      });
    }
    setIsAssetDialogOpen(true);
  };

  const handleAssetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!assetForm.name) return toast.error("Asset name is required");

    const categoryIdVal = assetForm.category_id === "none" || !assetForm.category_id ? null : parseInt(assetForm.category_id, 10);

    const payload = {
      ...assetForm,
      category_id: categoryIdVal
    };

    if (editingAsset) {
      updateAssetMutation.mutate({ id: editingAsset.id!, data: payload });
    } else {
      createAssetMutation.mutate(payload);
    }
  };

  const toggleAssetStatus = (asset: Asset, checked: boolean) => {
    updateAssetMutation.mutate({ id: asset.id!, data: { status: checked ? "active" : "inactive" } });
  };

  // ─── Render ─────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl">
            <HardDrive className="h-8 w-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Assets</h1>
            <p className="text-white/80 mt-1">Manage asset categories and items.</p>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full sm:w-[400px] grid-cols-2 mb-6">
          <TabsTrigger value="assets">Asset Items</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
        </TabsList>

        {/* ─── ASSETS TAB ──────────────────────────────────────────────── */}
        <TabsContent value="assets" className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="relative max-w-sm w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search assets by name..."
                value={assetSearch}
                onChange={(e) => setAssetSearch(e.target.value)}
                className="pl-9 bg-white"
              />
            </div>
            
            <Dialog open={isAssetDialogOpen} onOpenChange={setIsAssetDialogOpen}>
              <DialogTrigger asChild>
                <Button onClick={() => openAssetDialog()} className="bg-primary text-white shadow-md">
                  <Plus className="mr-2 h-4 w-4" /> Add Asset
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
                <form onSubmit={handleAssetSubmit}>
                  <DialogHeader>
                    <DialogTitle>{editingAsset ? "Edit Asset" : "Add New Asset"}</DialogTitle>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="asset-name">Asset Name *</Label>
                      <Input 
                        id="asset-name" 
                        value={assetForm.name} 
                        onChange={e => setAssetForm({...assetForm, name: e.target.value})} 
                        placeholder="E.g. Generator" 
                        required 
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select 
                        value={assetForm.category_id} 
                        onValueChange={(val) => setAssetForm({...assetForm, category_id: val})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select a category (optional)" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">No Category</SelectItem>
                          {categories.map((cat) => (
                            <SelectItem key={cat.id} value={String(cat.id)}>
                              {cat.name} {cat.status !== 'active' && '(Inactive)'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="asset-desc">Description</Label>
                      <Input 
                        id="asset-desc" 
                        value={assetForm.description} 
                        onChange={e => setAssetForm({...assetForm, description: e.target.value})} 
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="asset-location">Location</Label>
                      <Input 
                        id="asset-location" 
                        value={assetForm.location} 
                        onChange={e => setAssetForm({...assetForm, location: e.target.value})} 
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="asset-value">Value</Label>
                        <Input 
                          id="asset-value" 
                          type="number"
                          step="0.01"
                          value={assetForm.value} 
                          onChange={e => setAssetForm({...assetForm, value: parseFloat(e.target.value) || 0})} 
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="asset-date">Purchase Date</Label>
                        <Input 
                          id="asset-date" 
                          type="date"
                          value={assetForm.purchase_date} 
                          onChange={e => setAssetForm({...assetForm, purchase_date: e.target.value})} 
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between mt-2">
                      <Label htmlFor="asset-status">Status</Label>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-muted-foreground">{assetForm.status === 'active' ? 'Active' : 'Inactive'}</span>
                        <Switch 
                          id="asset-status" 
                          checked={assetForm.status === "active"}
                          onCheckedChange={(c) => setAssetForm({...assetForm, status: c ? "active" : "inactive"})}
                        />
                      </div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setIsAssetDialogOpen(false)}>Cancel</Button>
                    <Button type="submit" disabled={createAssetMutation.isPending || updateAssetMutation.isPending}>
                      {editingAsset ? "Save Changes" : "Create Asset"}
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
                  <TableHead>Asset Name</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead className="text-center">Status</TableHead>
                  <TableHead className="text-center">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoadingAssets ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">Loading assets...</TableCell>
                  </TableRow>
                ) : assets.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                      No assets found.
                    </TableCell>
                  </TableRow>
                ) : (
                  assets.map((asset) => (
                    <TableRow key={asset.id} className="transition-colors hover:bg-muted/50 group">
                      <TableCell className="font-medium text-primary">{asset.name}</TableCell>
                      <TableCell>
                        {asset.category_name ? (
                          <span className="bg-secondary/50 text-secondary-foreground px-2 py-1 rounded-md text-xs font-medium">
                            {asset.category_name}
                          </span>
                        ) : "-"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{asset.location || "-"}</TableCell>
                      <TableCell className="text-right font-medium text-emerald-600">
                        Rs {Number(asset.value || 0).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-center">
                        <Switch 
                          checked={asset.status === "active"} 
                          onCheckedChange={(c) => toggleAssetStatus(asset, c)}
                          disabled={updateAssetMutation.isPending}
                        />
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-blue-600 hover:text-blue-700 hover:bg-blue-50" onClick={() => openAssetDialog(asset)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50" onClick={() => {
                            if(confirm('Are you sure you want to delete this asset?')) {
                              deleteAssetMutation.mutate(asset.id!);
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
                        placeholder="E.g. Machinery, Electronics" 
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
                            if(confirm('Warning: Deleting this category will delete all assets inside it! Are you sure?')) {
                              deleteCategoryMutation.mutate(cat.id!);
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
