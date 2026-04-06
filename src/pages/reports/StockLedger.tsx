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
import autoTable from "jspdf-autotable";
import { sharePDF } from "@/lib/shareUtils";

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

  const generatePDFBlob = (): Blob => {
    const doc = new jsPDF();
    const title = "Stock Ledger Report";
    const subtitle = `${selectedMsPartyObj?.name || 'All'} | Item: ${itemId === 'all' ? 'All' : selectedItemObj?.name} | ${format(new Date(fromDate), 'dd MMM yyyy')} - ${format(new Date(toDate), 'dd MMM yyyy')}`;
    doc.setFontSize(20);
    doc.text(title, 14, 20);
    doc.setFontSize(10);
    doc.text(subtitle, 14, 30);

    let yOffset = 38;
    groupedData.forEach((group) => {
      autoTable(doc, {
        startY: yOffset,
        head: [[`Item: ${group.itemName}`]],
        body: group.transactions.map(tx => [
          format(new Date(tx.date), 'dd/MM/yyyy'),
          `${tx.type} / ${tx.ref_no}`,
          tx.particulars,
          tx.debit > 0 ? `+${tx.debit.toLocaleString()}` : '-',
          tx.credit > 0 ? `-${tx.credit.toLocaleString()}` : '-',
          tx.balance.toLocaleString()
        ]),
        headStyles: { fillColor: [15, 23, 42], textColor: 255, fontSize: 9 },
        styles: { fontSize: 8 },
        margin: { left: 14, right: 14 },
        theme: 'grid',
      });
      yOffset = (doc as any).lastAutoTable?.finalY + 10;
    });

    return doc.output('blob');
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
                        {items.map(item => (
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
                 className="bg-green-500 hover:bg-green-600 text-white border-none shadow-sm"
                 onClick={async () => {
                   const blob = generatePDFBlob();
                   const filename = `StockLedger_${selectedMsPartyObj?.name || 'All'}_${format(new Date(), 'yyyyMMdd')}.pdf`;
                   await sharePDF(blob, filename);
               }}
               >
                 <Share2 className="h-4 w-4 mr-2" /> Share
               </Button>
               <Button
                 variant="outline"
                 size="sm"
                 className="bg-slate-700 hover:bg-slate-800 text-white border-none shadow-sm"
                 onClick={async () => {
                   const email = getSetting("email");
                   const subject = `Stock Ledger: ${selectedMsPartyObj?.name || 'All'}`;
                   const body = `Stock Ledger Report\nParty: ${selectedMsPartyObj?.name || 'All'}\nPeriod: ${fromDate} to ${toDate}`;
                   const filename = `StockLedger_${selectedMsPartyObj?.name || 'All'}.pdf`;
                   const blob = generatePDFBlob();

                   if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) && navigator.share && window.isSecureContext) {
                     const file = new File([blob], filename, { type: "application/pdf" });
                     if (navigator.canShare?.({ files: [file] })) {
                       const shareData: ShareData = { files: [file], text: body };
                       await navigator.share(shareData);
                       return;
                     }
                   }

                   const url = URL.createObjectURL(blob);
                   const link = document.createElement('a');
                   link.href = url;
                   link.download = filename;
                   link.click();
                   URL.revokeObjectURL(url);
                   window.open(`mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`);
                 }}
               >
                 <Mail className="h-4 w-4 mr-2" /> Mail Report
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
            groupedData.map((group) => (
              <div key={group.itemId} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden break-inside-avoid mb-6">
                
                {/* Accordion Header (Modified for Print) */}
                <button 
                  onClick={() => toggleItem(group.itemId)}
                  className="w-full px-6 py-4 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors border-b border-transparent data-[open=true]:border-slate-200 print:bg-slate-50 print:border-slate-200"
                  data-open={expandedItems.has(group.itemId)}
                >
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-slate-100 rounded-lg print:hidden">
                      {expandedItems.has(group.itemId) ? <ChevronDown className="h-5 w-5 text-slate-600" /> : <ChevronRight className="h-5 w-5 text-slate-600" />}
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900">{group.itemName}</h3>
                      <p className="text-[10px] text-slate-400 mt-0.5 print:hidden">{group.transactions.length} Transactions</p>
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
                    <div className="text-right bg-slate-50 px-4 py-2 rounded-xl border border-slate-100 print:bg-white print:border-slate-300">
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
            ))
          )}
        </div>
      )}

    </div>
  );
}
