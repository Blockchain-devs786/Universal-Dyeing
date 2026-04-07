import { useState, useMemo, useEffect, useRef } from "react";
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
  Table as TableIcon,
  ChevronDown,
  ChevronRight,
  Layers,
  BarChart3,
  Share2,
  Mail
} from "lucide-react";
import {
  reportsApi,
  msPartiesApi,
  itemsApi,
  settingsApi,
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
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { sharePDF, mailPDF } from "@/lib/shareUtils";

type GroupedLedger = {
  itemId: number;
  itemName: string;
  transactions: (StockLedgerRow & { balance: number })[];
  totalDebit: number;
  totalCredit: number;
  finalBalance: number;
};

export default function StockLedger() {
  // Filter States
  const [msPartyId, setMsPartyId] = useState<string>("all");
  const [itemId, setItemId] = useState<string>("all");
  const [fromDate, setFromDate] = useState<string>(format(subDays(new Date(), 365), 'yyyy-MM-dd'));
  const [toDate, setToDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'));
  const [measurement, setMeasurement] = useState<{ [key: string]: boolean }>({ "15": false, "22": false });
  
  // UI States
  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [itemOpen, setItemOpen] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  const [isPreparing, setIsPreparing] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
  });

  const { data: items = [] } = useQuery({
    queryKey: ["items"],
    queryFn: () => itemsApi.list(),
  });

  // The actual report query
  const {
    data: ledger = [],
    isLoading,
    refetch,
    isFetching
  } = useQuery({
    queryKey: ["stock_ledger_report_internal"],
    queryFn: () => {
      const activeMeasurement = Object.keys(measurement).find(k => measurement[k]);
      return reportsApi.getStockLedger({
        ms_party_id: msPartyId === "all" ? undefined : Number(msPartyId),
        item_id: itemId === "all" ? undefined : Number(itemId),
        from_date: fromDate,
        to_date: toDate,
        measurement: activeMeasurement ? Number(activeMeasurement) : undefined,
      });
    },
    enabled: false
  });

  const { data: settings = [] } = useQuery({ queryKey: ["settings"], queryFn: () => settingsApi.list() });
  const getSetting = (key: string) => settings.find(s => s.key === key)?.value || "";

  // Default Party "Dyeing"
  useEffect(() => {
    if (msParties.length > 0 && msPartyId === "all") {
       const defaultParty = msParties.find(p => p.name.toLowerCase() === 'dyeing');
       if (defaultParty) setMsPartyId(String(defaultParty.id));
    }
  }, [msParties]);

  const handleGenerate = () => {
    if (msPartyId === "all") {
      alert("Please select a ledger first.");
      return;
    }
    setIsGenerated(true);
    refetch();
  };

  const handleClear = () => {
    setMeasurement({ "15": false, "22": false });
    setItemId("all");
    setIsGenerated(false);
    setExpandedItems(new Set());
  };

  const generatePDFBlob = async (): Promise<Blob> => {
    if (!printRef.current) return new Blob();
    const el = printRef.current;
    
    // Temporarily make element visible for capture
    el.style.visibility = 'visible';
    el.style.opacity = '1';
    el.style.zIndex = '9999';

    const canvas = await html2canvas(el, { 
      scale: 2, 
      useCORS: true,
      logging: false,
      allowTaint: true
    });

    // Hide again after capture
    el.style.visibility = 'hidden';
    el.style.opacity = '0';
    el.style.zIndex = '-2';

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'pt', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 20;
    const contentWidth = pageWidth - 2 * margin;
    const imgWidth = contentWidth;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;
    let position = margin;
    pdf.addImage(imgData, 'PNG', margin, position, imgWidth, imgHeight);
    heightLeft -= pageHeight - 2 * margin;
    while (heightLeft > 0) {
      pdf.addPage();
      pdf.addImage(imgData, 'PNG', margin, position - (pageHeight - 2 * margin), imgWidth, imgHeight);
      heightLeft -= pageHeight - 2 * margin;
    }
    return pdf.output('blob');
  };

  const toggleItem = (itemId: number) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) newExpanded.delete(itemId);
    else newExpanded.add(itemId);
    setExpandedItems(newExpanded);
  };

  // Grouping Logic
  const groupedData = useMemo(() => {
    const groups: Record<number, GroupedLedger> = {};

    ledger.forEach(row => {
      if (!groups[row.item_id]) {
        groups[row.item_id] = {
          itemId: row.item_id,
          itemName: row.item_name,
          transactions: [],
          totalDebit: 0,
          totalCredit: 0,
          finalBalance: 0
        };
      }
      
      const group = groups[row.item_id];
      const balance = group.finalBalance + (row.debit || 0) - (row.credit || 0);
      
      group.transactions.push({ ...row, balance });
      group.totalDebit += (row.debit || 0);
      group.totalCredit += (row.credit || 0);
      group.finalBalance = balance;
    });

    return Object.values(groups).sort((a,b) => a.itemName.localeCompare(b.itemName));
  }, [ledger]);

  const selectedMsPartyObj = msParties.find(p => String(p.id) === msPartyId);
  const selectedItemObj = items.find(i => String(i.id) === itemId);

  const activeMeasurementLabel = Object.keys(measurement).find(k => measurement[k]) 
    ? (Object.keys(measurement).find(k => measurement[k]) + " Yards") 
    : "All Measurements";

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">
      
      {/* Header (Hidden in Print) */}
      <div className="bg-slate-900 text-white rounded-2xl shadow-elevated border border-slate-800 p-6 print:hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-600/20 rounded-xl">
              <Layers className="h-8 w-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Stock Ledger (Item Wise)</h1>
              <p className="text-slate-400 text-sm mt-1">Central inventory tracking & party movements.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto items-end">
            <div className="space-y-1.5 w-full sm:w-64">
              <Label className="text-slate-400 text-[10px] uppercase font-bold tracking-widest px-1 flex items-center gap-1.5 font-sans">
                <Search className="h-3 w-3" /> Select Unit/Ledger:
              </Label>
              <Popover open={msPartyOpen} onOpenChange={setMsPartyOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between bg-white text-slate-900 border-none h-11 shadow-inner ring-offset-slate-900 focus:ring-2 focus:ring-blue-500"
                  >
                    <span className="truncate">
                      {msPartyId === "all" ? "-- Select Ledger --" : 
                        (selectedMsPartyObj?.name.toLowerCase() === 'dyeing' ? "\u2B50 " : "") + 
                        selectedMsPartyObj?.name}
                    </span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
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
                            {party.name.toLowerCase() === 'dyeing' ? "\u2B50 " : ""}{party.name}
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

      {/* Print-Only Header (Hidden on Screen) */}
      <div className="hidden print:block space-y-4 border-b pb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-black text-slate-900">Stock Ledger Report</h1>
            <p className="text-sm text-slate-500">Inventory history tracking system</p>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-slate-900">{selectedMsPartyObj?.name || 'All Ledgers'}</p>
            <p className="text-xs text-slate-500">Printed on: {format(new Date(), 'dd/MM/yyyy HH:mm')}</p>
          </div>
        </div>
        
        <div className="grid grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg border text-center">
          <div className="space-y-1">
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">From Date</p>
            <p className="text-xs font-bold text-slate-800">{format(new Date(fromDate), 'dd MMM yyyy')}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">To Date</p>
            <p className="text-xs font-bold text-slate-800">{format(new Date(toDate), 'dd MMM yyyy')}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Item Filter</p>
            <p className="text-xs font-bold text-slate-800">{itemId === 'all' ? 'All Items' : selectedItemObj?.name}</p>
          </div>
          <div className="space-y-1">
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Measurement</p>
            <p className="text-xs font-bold text-slate-800">{activeMeasurementLabel}</p>
          </div>
        </div>
      </div>

      {/* Filters Box (Hidden in Print) */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 print:hidden">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-end">
          
          {/* Item Filter Select */}
          <div className="md:col-span-3 space-y-2">
            <Label className="text-xs font-bold text-slate-500 uppercase px-1">Filter Item:</Label>
            <Popover open={itemOpen} onOpenChange={setItemOpen}>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-between h-10 font-normal bg-slate-50 border-slate-200">
                   <span className="truncate">{itemId === "all" ? "All Items" : selectedItemObj?.name}</span>
                   <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0">
                <Command>
                   <CommandInput placeholder="Search items..." />
                   <CommandList>
                     <CommandEmpty>No items found.</CommandEmpty>
                     <CommandGroup>
                        <CommandItem onSelect={() => { setItemId("all"); setItemOpen(false); }}>All Items</CommandItem>
                        {items.filter(item => item.status === 'active').map(item => (
                          <CommandItem key={item.id} value={item.name} onSelect={() => { setItemId(String(item.id)); setItemOpen(false); }}>{item.name}</CommandItem>
                        ))}
                     </CommandGroup>
                   </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <div className="md:col-span-4 grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase px-1">From:</Label>
              <Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="bg-slate-50 h-10" />
            </div>
            <div className="space-y-2">
              <Label className="text-xs font-bold text-slate-500 uppercase px-1">To:</Label>
              <Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} className="bg-slate-50 h-10" />
            </div>
          </div>

          <div className="md:col-span-3 space-y-2">
            <Label className="text-xs font-bold text-slate-500 uppercase px-1">Measurement:</Label>
            <div className="flex gap-4 p-2 bg-slate-50 rounded-lg border border-slate-200 h-10 items-center px-4">
              <div className="flex items-center space-x-2">
                <Checkbox id="y15" checked={measurement["15"]} onCheckedChange={(v) => setMeasurement({ "15": !!v, "22": false })} />
                <label htmlFor="y15" className="text-xs font-medium cursor-pointer">15 Yards</label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="y22" checked={measurement["22"]} onCheckedChange={(v) => setMeasurement({ "22": !!v, "15": false })} />
                <label htmlFor="y22" className="text-xs font-medium cursor-pointer">22 Yards</label>
              </div>
            </div>
          </div>

          <div className="md:col-span-2 flex gap-2">
            <Button variant="outline" onClick={handleClear} className="w-full h-10 border-slate-200">
              <Eraser className="h-4 w-4" />
            </Button>
            <Button onClick={handleGenerate} disabled={isFetching} className="w-full h-10 bg-blue-600 hover:bg-blue-700 shadow-lg">
              {isFetching ? <RefreshCw className="h-4 w-4 animate-spin" /> : <BarChart3 className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Results Section */}
      {isGenerated && (
        <div className="space-y-6 animate-in slide-in-from-bottom-2 duration-300">
          <div className="flex justify-between items-center px-2 print:hidden">
             <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
               <TableIcon className="h-5 w-5 text-blue-600" /> Items List Summary
             </h2>
             <div className="flex gap-2">
               <Button
                  variant="outline"
                  size="sm"
                  disabled={isPreparing}
                  className="bg-green-500 hover:bg-green-600 text-white border-none shadow-sm"
                  onClick={async () => {
                    setIsPreparing(true);
                    try {
                        const blob = await generatePDFBlob();
                        const filename = `StockLedger_${selectedMsPartyObj?.name || 'All'}_${format(new Date(), 'yyyyMMdd')}.pdf`;
                        await sharePDF(blob, filename);
                    } finally {
                        setIsPreparing(false);
                    }
                }}
                >
                  {isPreparing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Share2 className="h-4 w-4 mr-2" />}
                  Share
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isPreparing}
                  className="bg-slate-700 hover:bg-slate-800 text-white border-none shadow-sm"
                  onClick={async () => {
                    setIsPreparing(true);
                    try {
                        const email = getSetting("email");
                        const body = `Stock Ledger Report\nParty: ${selectedMsPartyObj?.name || 'All'}\nPeriod: ${fromDate} to ${toDate}\nPDF attached.`;
                        const filename = `StockLedger_${selectedMsPartyObj?.name || 'All'}.pdf`;
                        const blob = await generatePDFBlob();
                        await mailPDF(blob, filename, body, email);
                    } finally {
                        setIsPreparing(false);
                    }
                  }}
                >
                  {isPreparing ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Mail className="h-4 w-4 mr-2" />}
                  Mail Report
                </Button>
               <Button variant="outline" size="sm" onClick={() => window.print()} className="shadow-sm">
                 <Printer className="h-4 w-4 mr-2" /> Print Report
               </Button>
             </div>
          </div>

          {groupedData.length === 0 ? (
            <div className="bg-white rounded-2xl border p-20 text-center text-slate-400 font-medium">
              No stock data found for the selected filters.
            </div>
          ) : (
            <>
              {groupedData.map((group) => (
                <div key={group.itemId} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden break-inside-avoid mb-6">
                  
                  {/* Print-Only Item Header */}
                  <div className="hidden print:flex justify-between items-center px-6 py-3 bg-slate-50 border-b border-slate-200">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{group.itemName}</h3>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                         <p className="text-[8px] text-slate-400 font-bold uppercase tracking-wider">Debit</p>
                         <p className="text-[10px] font-bold text-blue-600">+{group.totalDebit.toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                         <p className="text-[8px] text-slate-400 font-bold uppercase tracking-wider">Credit</p>
                         <p className="text-[10px] font-bold text-orange-600">-{group.totalCredit.toLocaleString()}</p>
                      </div>
                      <div className="text-right pl-4 border-l border-slate-200">
                         <p className="text-[8px] text-slate-400 font-bold uppercase tracking-wider">Bal</p>
                         <p className="text-xs font-black text-slate-900">{group.finalBalance.toLocaleString()}</p>
                      </div>
                    </div>
                  </div>

                  {/* Accordion Header (Hidden in Print) */}
                  <button 
                    onClick={() => toggleItem(group.itemId)}
                    className="w-full px-6 py-4 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors border-b border-transparent data-[open=true]:border-slate-200 print:hidden"
                    data-open={expandedItems.has(group.itemId)}
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-slate-100 rounded-lg">
                        {expandedItems.has(group.itemId) ? <ChevronDown className="h-5 w-5 text-slate-600" /> : <ChevronRight className="h-5 w-5 text-slate-600" />}
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-slate-900">{group.itemName}</h3>
                        <p className="text-[10px] text-slate-400 mt-0.5">{group.transactions.length} Transactions</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-10">
                      <div className="text-right">
                         <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Total Debit</p>
                         <p className="text-xs font-bold text-blue-600">+{group.totalDebit.toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                         <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Total Credit</p>
                         <p className="text-xs font-bold text-orange-600">-{group.totalCredit.toLocaleString()}</p>
                      </div>
                      <div className="text-right bg-slate-50 px-4 py-2 rounded-xl border border-slate-100">
                         <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">Balance</p>
                         <p className={cn("text-sm font-black", group.finalBalance >= 0 ? "text-slate-900" : "text-red-600")}>
                           {group.finalBalance.toLocaleString()}
                         </p>
                      </div>
                    </div>
                  </button>

                  {/* Details Table (Forced visible in print) */}
                  <div className={cn(
                    "overflow-x-auto",
                    !expandedItems.has(group.itemId) && "hidden print:block"
                  )}>
                    <Table>
                      <TableHeader className="bg-slate-50/50">
                        <TableRow>
                          <TableHead className="w-[110px] font-bold text-[9px] text-slate-500 uppercase tracking-widest pl-6">Date</TableHead>
                          <TableHead className="font-bold text-[9px] text-slate-500 uppercase tracking-widest">Type / Ref</TableHead>
                          <TableHead className="font-bold text-[9px] text-slate-500 uppercase tracking-widest">Particulars</TableHead>
                          <TableHead className="font-bold text-[9px] text-slate-500 uppercase tracking-widest text-center">MSR</TableHead>
                          <TableHead className="font-bold text-[9px] text-slate-500 uppercase tracking-widest">Description</TableHead>
                          <TableHead className="text-center font-bold text-[9px] text-blue-600 uppercase tracking-widest">Debit (+)</TableHead>
                          <TableHead className="text-center font-bold text-[9px] text-orange-600 uppercase tracking-widest">Credit (-)</TableHead>
                          <TableHead className="text-center font-bold text-[9px] text-slate-900 uppercase tracking-widest bg-slate-100/50 pr-6">Run Bal</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {group.transactions.map((tx, idx) => (
                          <TableRow key={idx} className="hover:bg-slate-50/80 transition-colors group/row text-[10px] font-medium border-slate-100">
                            <TableCell className="text-slate-500 pl-6 border-slate-100">
                              {format(new Date(tx.date), 'dd/MM/yyyy')}
                            </TableCell>
                            <TableCell className="border-slate-100">
                              <span className="font-bold">{tx.type}</span>
                              <span className="text-slate-400 block text-[8px]">{tx.ref_no}</span>
                            </TableCell>
                            <TableCell className="border-slate-100">{tx.particulars}</TableCell>
                            <TableCell className="text-center border-slate-100">{tx.measurement}"</TableCell>
                            <TableCell className="text-slate-400 border-slate-100 max-w-[120px] truncate" title={tx.description}>{tx.description}</TableCell>
                            <TableCell className="text-center font-bold text-blue-700 bg-blue-50/5 border-slate-100">
                              {tx.debit > 0 ? `+${tx.debit.toLocaleString()}` : "-"}
                            </TableCell>
                            <TableCell className="text-center font-bold text-orange-600 bg-orange-50/5 border-slate-100">
                              {tx.credit > 0 ? `-${tx.credit.toLocaleString()}` : "-"}
                            </TableCell>
                            <TableCell className={cn(
                              "text-center font-black pr-6 border-slate-100",
                              tx.balance >= 0 ? "text-slate-900" : "text-red-600"
                            )}>
                              {tx.balance.toLocaleString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* Hidden Print Container for HTML-to-PDF */}
      <div ref={printRef} style={{ position: 'fixed', top: 0, left: 0, zIndex: -2, width: '794px', background: 'white', visibility: 'hidden', opacity: 0, color: '#1e293b', fontSize: '12px' }}>
        <div style={{ padding: '40px 40px 20px 40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid #e2e8f0' }}>
            <div>
              <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Stock Ledger Report</h1>
              <p style={{ fontSize: '13px', color: '#64748b' }}>{selectedMsPartyObj?.name || 'All Ledgers'} | Item: {itemId === 'all' ? 'All' : selectedItemObj?.name} | {format(new Date(fromDate), 'dd MMM yyyy')} to {format(new Date(toDate), 'dd MMM yyyy')}</p>
            </div>
          </div>
          {groupedData.map((group) => (
            <div key={group.itemId} style={{ marginBottom: '24px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '8px', background: '#f1f5f9', padding: '8px 12px' }}>{group.itemName}</h2>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', marginBottom: '8px' }}>
                <thead>
                  <tr style={{ background: '#1e293b', color: 'white' }}>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'left' }}>Date</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'left' }}>Type / Ref</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'left' }}>Particulars</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center' }}>MSR</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'left' }}>Description</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center' }}>Debit (+)</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center' }}>Credit (-)</th>
                    <th style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center' }}>Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {group.transactions.map((tx, idx) => (
                    <tr key={idx} style={{ background: idx % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px' }}>{format(new Date(tx.date), 'dd/MM/yyyy')}</td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px' }}><span style={{ fontWeight: 'bold' }}>{tx.type}</span><br/><span style={{ color: '#94a3b8', fontSize: '10px' }}>{tx.ref_no}</span></td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px' }}>{tx.particulars}</td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center' }}>{tx.measurement}"</td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', color: '#94a3b8', fontSize: '10px' }}>{tx.description}</td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center', color: '#1d4ed8', fontWeight: 'bold' }}>
                        {tx.debit > 0 ? `+${tx.debit.toLocaleString()}` : "-"}
                      </td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center', color: '#ea580c', fontWeight: 'bold' }}>
                        {tx.credit > 0 ? `-${tx.credit.toLocaleString()}` : "-"}
                      </td>
                      <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center', fontWeight: 'bold', color: tx.balance >= 0 ? '#1e293b' : '#ef4444' }}>
                        {tx.balance.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                  <tr style={{ background: '#f1f5f9', fontWeight: 'bold' }}>
                    <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'right' }} colSpan={5}>Totals - {group.itemName}</td>
                    <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center', color: '#1d4ed8' }}>+{group.totalDebit.toLocaleString()}</td>
                    <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center', color: '#ea580c' }}>-{group.totalCredit.toLocaleString()}</td>
                    <td style={{ border: '1px solid #e2e8f0', padding: '8px 8px', textAlign: 'center' }}>{group.finalBalance.toLocaleString()}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
          {groupedData.length === 0 && (
            <p style={{ textAlign: 'center', color: '#94a3b8', padding: '40px', fontStyle: 'italic' }}>No data</p>
          )}
        </div>
      </div>
    </div>
  );
}
