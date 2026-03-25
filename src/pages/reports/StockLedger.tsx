import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { 
  FileText, 
  Search, 
  RefreshCw, 
  Printer, 
  Eraser, 
  Calendar, 
  ArrowRight,
  Filter,
  Check,
  ChevronsUpDown,
  Table as TableIcon
} from "lucide-react";
import { 
  reportsApi, 
  msPartiesApi, 
  itemsApi, 
  type MsParty, 
  type Item,
  type StockLedgerRow 
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { format, subDays } from "date-fns";

export default function StockLedger() {
  // Filter States
  const [msPartyId, setMsPartyId] = useState<string>("all");
  const [fromDate, setFromDate] = useState<string>(format(subDays(new Date(), 365), 'yyyy-MM-dd'));
  const [toDate, setToDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'));
  const [transactionType, setTransactionType] = useState<string>("all");
  const [particulars, setParticulars] = useState<string>("all");
  const [itemId, setItemId] = useState<string>("all");
  const [measurement, setMeasurement] = useState<{ [key: string]: boolean }>({ "15": false, "22": false });
  const [amountType, setAmountType] = useState<{ [key: string]: boolean }>({ "debit": false, "credit": false });

  // UI States
  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [itemOpen, setItemOpen] = useState(false);
  const [typeOpen, setTypeOpen] = useState(false);
  const [partOpen, setPartOpen] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);

  // Queries
  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
  });

  const { data: items = [] } = useQuery({
    queryKey: ["items"],
    queryFn: () => itemsApi.list(),
  });

  // Fetch full ledger data for the selected party to build dynamic filters
  const { data: rawLedgerData = [] } = useQuery({
    queryKey: ["raw_stock_ledger", msPartyId],
    queryFn: () => msPartyId !== "all" 
      ? reportsApi.getStockLedger({ ms_party_id: msPartyId }) 
      : Promise.resolve([]),
    enabled: msPartyId !== "all"
  });

  // The actual report query triggered by "Generate Report"
  const { 
    data: ledger = [], 
    isLoading, 
    refetch, 
    isFetching 
  } = useQuery({
    queryKey: ["stock_ledger_report"], // Query key doesn't depend on filters to avoid auto-trigger
    queryFn: () => {
      const activeMeasurement = Object.keys(measurement).find(k => measurement[k]);
      const activeAmountType = Object.keys(amountType).find(k => amountType[k]) as 'debit'|'credit'|undefined;

      return reportsApi.getStockLedger({
        ms_party_id: msPartyId === "all" ? undefined : Number(msPartyId),
        item_id: itemId === "all" ? undefined : Number(itemId),
        from_date: fromDate,
        to_date: toDate,
        transaction_type: transactionType === "all" ? undefined : transactionType,
        particulars: particulars === "all" ? undefined : particulars,
        measurement: activeMeasurement ? Number(activeMeasurement) : undefined,
        amount_type: activeAmountType
      });
    },
    enabled: false // Only manual refetch
  });

  // Effect to set default party "Dyeing"
  useEffect(() => {
    if (msParties.length > 0 && msPartyId === "all") {
       const defaultParty = msParties.find(p => 
          p.name.toLowerCase().includes('dyeing') || 
          p.name.toLowerCase().includes('ud')
       );
       if (defaultParty) {
          setMsPartyId(String(defaultParty.id));
       }
    }
  }, [msParties]);

  // Dynamic filter options based on raw selection data
  const dynamicFilters = useMemo(() => {
    const types = new Set<string>();
    const details = new Set<string>();
    const partyItems = new Set<string>();

    rawLedgerData.forEach(row => {
      if (row.type) types.add(row.type);
      if (row.particulars) details.add(row.particulars);
      if (row.item_name) partyItems.add(row.item_name);
    });

    return {
      types: Array.from(types).sort(),
      particulars: Array.from(details).sort(),
      items: rawLedgerData.reduce((acc: {id: number, name: string}[], row) => {
        if (!acc.find(a => a.id === row.item_id)) {
           acc.push({ id: row.item_id, name: row.item_name });
        }
        return acc;
      }, []).sort((a,b) => a.name.localeCompare(b.name))
    };
  }, [rawLedgerData]);

  const handleGenerate = () => {
    if (msPartyId === "all") {
      alert("Please select a ledger first.");
      return;
    }
    setIsGenerated(true);
    refetch();
  };

  const handleClear = () => {
    setTransactionType("all");
    setParticulars("all");
    setItemId("all");
    setMeasurement({ "15": false, "22": false });
    setAmountType({ "debit": false, "credit": false });
    setIsGenerated(false);
  };

  const selectedMsPartyObj = msParties.find(p => String(p.id) === msPartyId);
  const selectedItemObj = items.find(i => String(i.id) === itemId);

  // Calculate Running Balance
  const reportWithBalance = useMemo(() => {
    let balance = 0;
    return ledger.map(row => {
      balance += (row.debit || 0) - (row.credit || 0);
      return { ...row, balance };
    });
  }, [ledger]);

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Top Header Card */}
      <div className="bg-slate-900 text-white rounded-2xl shadow-elevated border border-slate-800 p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-600/20 rounded-xl">
              <FileText className="h-8 w-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Stock Ledgers</h1>
              <p className="text-slate-400 text-sm mt-1">Detailed transaction history for individual parties.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto items-end">
            <div className="space-y-1.5 w-full sm:w-64">
              <Label className="text-slate-400 text-[10px] uppercase font-bold tracking-widest px-1 flex items-center gap-1.5">
                <Search className="h-3 w-3" /> Search Ledger:
              </Label>
              <Popover open={msPartyOpen} onOpenChange={setMsPartyOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between bg-white text-slate-900 border-none h-11 shadow-inner"
                  >
                    <span className="truncate">
                      {msPartyId === "all" ? "-- Select Ledger --" : 
                        (selectedMsPartyObj?.name.toLowerCase().includes('dyeing') ? "\u2B50 " : "") + 
                        selectedMsPartyObj?.name || "-- Select Ledger --"}
                    </span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[300px] p-0" align="end">
                  <Command>
                    <CommandInput placeholder="Search party..." />
                    <CommandList>
                      <CommandEmpty>No records found.</CommandEmpty>
                      <CommandGroup>
                        {msParties.map((party) => (
                          <CommandItem
                            key={party.id}
                            value={party.name + party.id}
                            onSelect={() => {
                              setMsPartyId(String(party.id));
                              setMsPartyOpen(false);
                            }}
                          >
                            <Check className={cn("mr-2 h-4 w-4", msPartyId === String(party.id) ? "opacity-100" : "opacity-0")} />
                            <span>{party.name.toLowerCase().includes('dyeing') ? "\u2B50 " : ""}{party.name}</span>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Filters Box */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50/80 border-b px-6 py-3 flex items-center gap-2">
          <Filter className="h-4 w-4 text-blue-600" />
          <span className="font-bold text-slate-700 text-sm uppercase tracking-wide">Advanced Filters</span>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-end">
            
            {/* Date Range */}
            <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
               <div className="space-y-2">
                 <Label className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2">
                   <Calendar className="h-3 w-3" /> Date Range: <span className="text-slate-900">From:</span>
                 </Label>
                 <Input 
                   type="date" 
                   value={fromDate} 
                   onChange={(e) => setFromDate(e.target.value)}
                   className="h-10 bg-slate-50"
                 />
               </div>
               <div className="space-y-2">
                 <Label className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2">
                   <ArrowRight className="h-3 w-3" /> To:
                 </Label>
                 <Input 
                   type="date" 
                   value={toDate} 
                   onChange={(e) => setToDate(e.target.value)}
                   className="h-10 bg-slate-50"
                 />
               </div>
            </div>

            {/* Trans Type */}
            <div className="lg:col-span-3 space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase">Transaction Type:</Label>
              <Popover open={typeOpen} onOpenChange={setTypeOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-full justify-between h-10 font-normal bg-slate-50">
                    {transactionType === "all" ? "All Types" : transactionType}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                  <Command>
                    <CommandList>
                      <CommandGroup>
                        <CommandItem onSelect={() => { setTransactionType("all"); setTypeOpen(false); }}>All Types</CommandItem>
                        {dynamicFilters.types.map(t => (
                          <CommandItem key={t} onSelect={() => { setTransactionType(t); setTypeOpen(false); }}>{t}</CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {/* Particulars */}
            <div className="lg:col-span-3 space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase">Particulars:</Label>
              <Popover open={partOpen} onOpenChange={setPartOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-full justify-between h-10 font-normal bg-slate-50">
                    <span className="truncate">{particulars === "all" ? "All Particulars" : particulars}</span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                  <Command>
                    <CommandInput placeholder="Search party..." />
                    <CommandList>
                      <CommandEmpty>No parties found.</CommandEmpty>
                      <CommandGroup>
                        <CommandItem onSelect={() => { setParticulars("all"); setPartOpen(false); }}>All Particulars</CommandItem>
                        {dynamicFilters.particulars.map(p => (
                          <CommandItem key={p} value={p} onSelect={() => { setParticulars(p); setPartOpen(false); }}>{p}</CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-end">
            {/* Item Select */}
            <div className="lg:col-span-4 space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase">Item:</Label>
              <Popover open={itemOpen} onOpenChange={setItemOpen}>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-full justify-between h-10 font-normal bg-slate-50">
                    <span className="truncate">{itemId === "all" ? "All Items" : dynamicFilters.items.find(i => String(i.id) === itemId)?.name || "All Items"}</span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[200px] p-0">
                  <Command>
                    <CommandList>
                      <CommandGroup>
                        <CommandItem onSelect={() => { setItemId("all"); setItemOpen(false); }}>All Items</CommandItem>
                        {dynamicFilters.items.map(i => (
                          <CommandItem key={i.id} value={i.name} onSelect={() => { setItemId(String(i.id)); setItemOpen(false); }}>{i.name}</CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {/* Yard Checkboxes */}
            <div className="lg:col-span-3 space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase px-1">Yard:</Label>
              <div className="flex gap-4 p-2 bg-slate-50 rounded-lg border h-10 items-center px-4">
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="y15" 
                    checked={measurement["15"]} 
                    onCheckedChange={(val) => setMeasurement({ "15": !!val, "22": false })}
                  />
                  <label htmlFor="y15" className="text-xs font-medium leading-none cursor-pointer">15 Yards</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="y22" 
                    checked={measurement["22"]} 
                    onCheckedChange={(val) => setMeasurement({ "22": !!val, "15": false })}
                  />
                  <label htmlFor="y22" className="text-xs font-medium leading-none cursor-pointer">22 Yards</label>
                </div>
              </div>
            </div>

            {/* Amount Type */}
            <div className="lg:col-span-3 space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase px-1">Amount Type:</Label>
              <div className="flex gap-6 p-2 bg-slate-50 rounded-lg border h-10 items-center px-4">
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="debit" 
                    checked={amountType["debit"]} 
                    onCheckedChange={(val) => setAmountType({ "debit": !!val, "credit": false })}
                  />
                  <label htmlFor="debit" className="text-xs font-medium text-blue-600 leading-none cursor-pointer">Debit</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="credit" 
                    checked={amountType["credit"]} 
                    onCheckedChange={(val) => setAmountType({ "credit": !!val, "debit": false })}
                  />
                  <label htmlFor="credit" className="text-xs font-medium text-orange-600 leading-none cursor-pointer">Credit</label>
                </div>
              </div>
            </div>

            <div className="lg:col-span-2 flex gap-2">
               <Button variant="destructive" onClick={handleClear} className="w-full h-10 shadow-sm transition-all hover:brightness-110">
                 <Eraser className="h-4 w-4 mr-2" /> Clear
               </Button>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-4 flex justify-end">
            <Button 
               onClick={handleGenerate} 
               disabled={isFetching}
               className="h-12 px-8 bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg transition-all active:scale-95 text-base"
            >
              {isFetching ? <RefreshCw className="mr-2 h-5 w-5 animate-spin" /> : <TableIcon className="mr-2 h-5 w-5" />}
              Generate Report
            </Button>
          </div>
        </div>
      </div>

      {/* Results Section */}
      {isGenerated && (
        <div className="bg-white rounded-2xl shadow-elevated border border-slate-200 overflow-hidden animate-in slide-in-from-bottom-4 duration-500">
          <div className="bg-slate-900 text-white px-6 py-4 flex justify-between items-center">
            <h2 className="font-bold tracking-tight flex items-center gap-2">
              <TableIcon className="h-5 w-5 text-blue-400" />
              Stock Transactions Ledger
            </h2>
            <Button size="sm" variant="outline" className="bg-white/10 border-white/20 text-white hover:bg-white/20" onClick={() => window.print()}>
              <Printer className="h-4 w-4 mr-2" /> Print
            </Button>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow>
                  <TableHead className="w-[100px] font-bold text-slate-700 uppercase tracking-tighter text-[10px]">Date</TableHead>
                  <TableHead className="font-bold text-slate-700 uppercase tracking-tighter text-[10px]">Trans Type</TableHead>
                  <TableHead className="font-bold text-slate-700 uppercase tracking-tighter text-[10px]">Particulars</TableHead>
                  <TableHead className="font-bold text-slate-700 uppercase tracking-tighter text-[10px]">Description</TableHead>
                  <TableHead className="font-bold text-slate-700 uppercase tracking-tighter text-[10px]">Item Name</TableHead>
                  <TableHead className="font-bold text-slate-700 uppercase tracking-tighter text-[10px] text-center">15 Yard Qty</TableHead>
                  <TableHead className="font-bold text-slate-700 uppercase tracking-tighter text-[10px] text-center">22 Yard Qty</TableHead>
                  <TableHead className="font-bold text-blue-600 uppercase tracking-tighter text-[10px] text-center bg-blue-50/50">Total Qty (Debit)</TableHead>
                  <TableHead className="font-bold text-orange-600 uppercase tracking-tighter text-[10px] text-center bg-orange-50/50">Total Qty (Credit)</TableHead>
                  <TableHead className="font-bold text-slate-900 uppercase tracking-tighter text-[10px] text-center bg-slate-100/80">Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-20 text-slate-400">Loading ledger entries...</TableCell>
                  </TableRow>
                ) : reportWithBalance.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-20 text-slate-400 font-medium">No transactions found for the selected filters.</TableCell>
                  </TableRow>
                ) : (
                  reportWithBalance.map((row, idx) => (
                    <TableRow key={idx} className="hover:bg-slate-50 transition-colors group">
                      <TableCell className="text-[11px] font-medium text-slate-500 whitespace-nowrap">
                        {format(new Date(row.date), 'dd/MM/yyyy')}
                      </TableCell>
                      <TableCell className="text-[11px] font-bold text-slate-700">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[9px] uppercase tracking-wide",
                          row.type?.includes('Inward') ? "bg-blue-100 text-blue-800" :
                          row.type?.includes('Outward') ? "bg-orange-100 text-orange-800" :
                          "bg-purple-100 text-purple-800"
                        )}>
                          {row.type}
                        </span>
                        <div className="text-[10px] font-normal text-slate-400 mt-0.5">{row.ref_no}</div>
                      </TableCell>
                      <TableCell className="text-[11px] font-medium text-slate-800">{row.particulars}</TableCell>
                      <TableCell className="text-[10px] text-slate-500 max-w-[150px] truncate" title={row.description}>
                        {row.description}
                      </TableCell>
                      <TableCell className="text-[11px] font-medium text-slate-900">{row.item_name}</TableCell>
                      <TableCell className="text-center text-[11px] font-bold text-slate-600">
                        {row.measurement === 15 ? (row.debit || row.credit) : '-'}
                      </TableCell>
                      <TableCell className="text-center text-[11px] font-bold text-slate-600">
                        {row.measurement === 22 ? (row.debit || row.credit) : '-'}
                      </TableCell>
                      <TableCell className="text-center text-[12px] font-bold text-blue-600 bg-blue-50/20">
                        {row.debit > 0 ? row.debit : '-'}
                      </TableCell>
                      <TableCell className="text-center text-[12px] font-bold text-orange-600 bg-orange-50/20">
                        {row.credit > 0 ? row.credit : '-'}
                      </TableCell>
                      <TableCell className={cn(
                        "text-center text-[12px] font-bold bg-slate-50/50",
                        row.balance >= 0 ? "text-slate-900" : "text-red-600"
                      )}>
                        {row.balance.toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

    </div>
  );
}
