import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Banknote,
  Search,
  Printer,
  RefreshCw,
  Calendar,
  FileSpreadsheet,
  Share2,
  Mail,
  ChevronsUpDown,
  Filter
} from "lucide-react";
import {
  reportsApi,
  msPartiesApi,
  vendorsApi,
  expensesApi,
  accountsApi,
  assetsApi,
  settingsApi,
  type MsParty
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import {
    Popover,
    PopoverContent,
    PopoverTrigger
} from "@/components/ui/popover";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList
} from "@/components/ui/command";
import { cn } from "@/lib/utils";
import { format, subDays } from "date-fns";
import { sharePDF } from "@/lib/shareUtils";

export default function CashLedger() {
  const [accountId, setAccountId] = useState<string>("all");
  const [accountType, setAccountType] = useState<string>("MS Party");
  const [fromDate, setFromDate] = useState<string>(format(subDays(new Date(), 30), 'yyyy-MM-dd'));
  const [toDate, setToDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'));
  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);

  const printRef = useRef<HTMLDivElement>(null);

  // Queries
  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
  });

  const {
    data: ledger = [],
    isLoading,
    refetch,
    isFetching
  } = useQuery({
    queryKey: ["financial_ledger_report", accountId, accountType],
    queryFn: () => reportsApi.getFinancialLedger(Number(accountId), fromDate, toDate, accountType),
    enabled: false
  });

  const { data: vendors = [] } = useQuery({ queryKey: ["vendors"], queryFn: () => vendorsApi.list() });
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: () => accountsApi.list() });
  const { data: assets = [] } = useQuery({ queryKey: ["assets"], queryFn: () => assetsApi.list() });
  const { data: expenses = [] } = useQuery({ queryKey: ["expenses"], queryFn: () => expensesApi.list() });
  const { data: settings = [] } = useQuery({ queryKey: ["settings"], queryFn: () => settingsApi.list() });

  const getSetting = (key: string) => settings.find(s => s.key === key)?.value || "";

  // Default to "Dyeing" party on load
  useEffect(() => {
    if (msParties && msParties.length > 0 && accountId === "all" && accountType === "MS Party") {
        const dyeing = msParties.find(p => p.name?.toLowerCase() === 'dyeing');
        if (dyeing) setAccountId(String(dyeing.id));
    }
  }, [msParties]);

  const generatePDFBlob = async (): Promise<Blob> => {
    if (!printRef.current) return new Blob();
    const canvas = await html2canvas(printRef.current, { scale: 2, useCORS: true });
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


  const allLedgers = [
    ...msParties.map(p => ({ id: String(p.id), name: p.name, type: "MS Party" })),
    ...vendors.map(v => ({ id: String(v.id), name: v.name, type: "Vendor" })),
    ...accounts.map(a => ({ id: String(a.id), name: a.name, type: "Account" })),
    ...assets.map(a => ({ id: String(a.id), name: a.name, type: "Asset" })),
    ...expenses.map(e => ({ id: String(e.id), name: e.name, type: "Expense" })),
  ];

  const handleGenerate = () => {
    if (accountId === "all") return;
    setIsGenerated(true);
    refetch();
  };

  const selectedLedger = allLedgers.find(l => l.id === accountId && l.type === accountType);
  const totalDebit = ledger.reduce((s, r) => s + (r.debit || 0), 0);
  const totalCredit = ledger.reduce((s, r) => s + (r.credit || 0), 0);
  const finalBalance = ledger.length > 0 ? ledger[ledger.length - 1].balance : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">

      {/* Header */}
      <div className="bg-slate-900 text-white rounded-2xl shadow-elevated border border-slate-800 p-6 print:hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-600/20 rounded-xl">
              <Banknote className="h-8 w-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Cash Ledgers</h1>
              <p className="text-slate-400 text-sm mt-1">Track financial histories for parties & internal accounts.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto items-end">
            <div className="space-y-1.5 w-full sm:w-64">
              <Label className="text-slate-400 text-[10px] uppercase font-bold tracking-widest px-1 flex items-center gap-1.5 font-sans">
                <Search className="h-3 w-3" /> Select Ledger:
              </Label>
              <Popover open={msPartyOpen} onOpenChange={setMsPartyOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full justify-between bg-white text-slate-900 border-none h-11 shadow-inner ring-offset-slate-900 focus:ring-2 focus:ring-blue-500"
                  >
                    <span className="truncate">
                      {accountId === "all" ? "-- Select Ledger --" :
                        ((selectedLedger?.name?.toLowerCase() === 'dyeing' ? "\u2B50 " : "") +
                        `[${selectedLedger?.type || ''}] ` + (selectedLedger?.name || ''))}
                    </span>
                    <ChevronsUpDown className="ml-2 h-4 w-4 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80 p-0" align="start">
                  <Command>
                    <CommandInput placeholder="Search ledger type or name..." />
                    <CommandList>
                      <CommandEmpty>No ledger found.</CommandEmpty>
                      <CommandGroup>
                        {allLedgers.map((l) => (
                          <CommandItem
                            key={`${l.type}-${l.id}`}
                            value={`${l.type} ${l.name}`}
                            onSelect={() => {
                              setAccountId(l.id);
                              setAccountType(l.type);
                              setMsPartyOpen(false);
                              setIsGenerated(false);
                            }}
                            className="flex items-center justify-between"
                          >
                            <div className="flex flex-col">
                                <span className="font-medium">{l.name}</span>
                                <span className="text-[10px] uppercase text-muted-foreground">{l.type}</span>
                            </div>
                            {l.id === accountId && l.type === accountType && <Search className="h-4 w-4 text-blue-500" />}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            <Button
                onClick={handleGenerate}
                disabled={isLoading || isFetching || accountId === "all"}
                className="h-11 px-8 bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg transition-all active:scale-95"
            >
              {isLoading || isFetching ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
              Generate Report
            </Button>

            {isGenerated && (
              <div className="flex gap-2 print:hidden">
                <Button
                  variant="outline"
                  className="h-11 px-4 bg-green-500 hover:bg-green-600 text-white border-none shadow-md"
                  onClick={async () => {
                    const blob = await generatePDFBlob();
                    const filename = `Ledger_${selectedLedger?.name}_${format(new Date(), 'yyyyMMdd')}.pdf`;
                    await sharePDF(blob, filename);
                  }}
                >
                  <Share2 className="h-4 w-4 mr-2" />
                  Share
                </Button>
                <Button
                  variant="outline"
                  className="h-11 px-4 bg-slate-700 hover:bg-slate-800 text-white border-none shadow-md"
                  onClick={async () => {
                    const email = getSetting("email");
                    const balance = finalBalance || 0;
                    const subject = `Ledger Summary: ${selectedLedger?.name}`;
                    const body = `Please find the ledger summary below:\n\nParty: ${selectedLedger?.name}\nType: ${selectedLedger?.type}\nPeriod: ${fromDate} to ${toDate}\nBalance: PKR ${balance.toLocaleString()}`;

                    const blob = await generatePDFBlob();
                    const filename = `Ledger_${selectedLedger?.name}.pdf`;

                    // On mobile, use native share to auto-attach the file
                    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) && navigator.share && window.isSecureContext) {
                      const file = new File([blob], filename, { type: "application/pdf" });
                      if (navigator.canShare?.({ files: [file] })) {
                        const shareData: ShareData = { files: [file], text: body };
                        await navigator.share(shareData);
                        return;
                      }
                    }

                    // Desktop fallback: download + open mailto
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    link.click();
                    URL.revokeObjectURL(url);

                    window.open(`mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`);
                  }}
                >
                  <Mail className="h-4 w-4 mr-2" />
                  Mail Report
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filters Overlay */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 bg-white p-6 rounded-2xl border shadow-sm print:hidden">
        <div className="md:col-span-1 flex items-center gap-3 border-r pr-6">
            <div className="p-2 bg-slate-100 rounded-lg text-slate-600">
                <Filter className="h-5 w-5" />
            </div>
            <h3 className="font-bold text-slate-800">Reports Filters</h3>
        </div>

        <div className="space-y-1.5 flex-1">
          <Label className="text-[10px] font-black uppercase text-slate-400 tracking-wider flex items-center gap-2">
              <Calendar className="h-3 w-3" /> From Date
          </Label>
          <Input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="h-10 border-slate-200" />
        </div>

        <div className="space-y-1.5 flex-1">
          <Label className="text-[10px] font-black uppercase text-slate-400 tracking-wider flex items-center gap-2">
              <Calendar className="h-3 w-3" /> To Date
          </Label>
          <Input type="date" value={toDate} onChange={e => setToDate(e.target.value)} className="h-10 border-slate-200" />
        </div>

        <div className="flex items-end">
            <Button variant="outline" className="h-10 w-full border-dashed" onClick={() => window.print()} disabled={!isGenerated}>
                <Printer className="mr-2 h-4 w-4" /> Print PDF
            </Button>
        </div>
      </div>

      {/* Report Content */}
      {isGenerated && (
        <div className="bg-white rounded-2xl shadow-elevated border overflow-hidden min-h-[600px] print:border-none print:shadow-none">
          <div className="p-6 border-b bg-slate-50/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 print:p-0 print:border-none">
            <div className="flex items-center gap-3">
                <FileSpreadsheet className="h-6 w-6 text-emerald-600" />
                <div>
                    <h2 className="text-xl font-bold text-slate-900">{selectedLedger?.name || 'Unknown Account'}</h2>
                    <p className="text-slate-500 text-xs font-medium">{selectedLedger?.type || 'Account'} - Financial Statement Ledger</p>
                </div>
            </div>
            <div className="px-4 py-2 bg-slate-100 rounded-xl text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                Period: {fromDate ? format(new Date(fromDate), 'dd MMM yyyy') : ''} - {toDate ? format(new Date(toDate), 'dd MMM yyyy') : ''}
            </div>
          </div>

          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-slate-900">
                <TableRow className="hover:bg-slate-900 border-none h-12">
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider w-[120px]">Date</TableHead>
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider">Particulars</TableHead>
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider">Invoice/Voucher</TableHead>
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider">Description</TableHead>
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider text-right">Debit (PKR)</TableHead>
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider text-right">Credit (PKR)</TableHead>
                  <TableHead className="text-white text-[10px] font-black uppercase tracking-wider text-right">Balance</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ledger.length === 0 ? (
                    <TableRow>
                        <TableCell colSpan={7} className="h-32 text-center text-slate-400 font-medium italic">
                            No financial transactions found for the selected period.
                        </TableCell>
                    </TableRow>
                ) : (
                    ledger.map((row, idx) => (
                      <TableRow key={idx} className="h-14 hover:bg-slate-50/80 transition-colors border-slate-100">
                        <TableCell className="font-medium text-slate-600">{row.date ? format(new Date(row.date), 'yyyy-MM-dd') : 'N/A'}</TableCell>
                        <TableCell className="font-bold text-slate-900 uppercase text-xs">{row.particulars}</TableCell>
                        <TableCell className="font-bold text-blue-600 text-xs">{row.ref_no}</TableCell>
                        <TableCell className="text-slate-500 text-xs max-w-xs truncate">{row.description}</TableCell>
                        <TableCell className="text-right font-bold text-blue-700">
                            {(row.debit || 0) > 0 ? (row.debit || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "-"}
                        </TableCell>
                        <TableCell className="text-right font-bold text-red-600">
                            {(row.credit || 0) > 0 ? (row.credit || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "-"}
                        </TableCell>
                        <TableCell className={cn(
                            "text-right font-black",
                            (row.balance || 0) < 0 ? "text-red-700" : "text-emerald-700"
                        )}>
                            {(row.balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </TableCell>
                      </TableRow>
                    ))
                )}
              </TableBody>
            </Table>
          </div>

          <div className="p-8 bg-slate-50 border-t print:hidden">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="bg-white p-4 rounded-xl border shadow-sm">
                    <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Total Debits</p>
                    <p className="text-xl font-black text-blue-700">
                        {totalDebit.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </p>
                </div>
                <div className="bg-white p-4 rounded-xl border shadow-sm">
                    <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Total Credits</p>
                    <p className="text-xl font-black text-red-600">
                        {totalCredit.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </p>
                </div>
                <div className="md:col-span-2 bg-slate-900 p-4 rounded-xl shadow-lg flex justify-between items-center text-white">
                    <div>
                        <p className="text-[10px] font-bold text-slate-400 uppercase mb-1">Final Outstanding Balance</p>
                        <p className="text-2xl font-black">
                            {finalBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </p>
                    </div>
                    <div className="p-2 bg-white/10 rounded-lg">
                        <Banknote className="h-8 w-8 text-blue-400" />
                    </div>
                </div>
            </div>
          </div>
        </div>
      )}

      {/* Hidden Print Container for HTML-to-PDF */}
      <div ref={printRef} style={{ position: 'fixed', top: 0, left: 0, zIndex: -2, width: '794px', background: 'white', visibility: 'hidden', opacity: 0, color: '#1e293b', fontSize: '13px' }}>
        <div style={{ padding: '40px 40px 20px 40px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid #e2e8f0' }}>
            <div>
              <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>{selectedLedger?.name || 'Unknown Account'}</h1>
              <p style={{ fontSize: '14px', color: '#64748b' }}>{selectedLedger?.type || 'Account'} - Financial Statement Ledger</p>
            </div>
            <p style={{ fontSize: '13px', color: '#64748b' }}>
              Period: {fromDate ? format(new Date(fromDate), 'dd MMM yyyy') : ''} - {toDate ? format(new Date(toDate), 'dd MMM yyyy') : ''}
            </p>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ background: '#1e293b', color: 'white' }}>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'left' }}>Date</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'left' }}>Particulars</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'left' }}>Invoice/Voucher</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'left' }}>Description</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'right' }}>Debit (PKR)</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'right' }}>Credit (PKR)</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 10px', textAlign: 'right' }}>Balance</th>
              </tr>
            </thead>
            <tbody>
              {ledger.map((row, idx) => (
                <tr key={idx} style={{ background: idx % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', color: '#475569' }}>{row.date ? format(new Date(row.date), 'yyyy-MM-dd') : 'N/A'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', fontWeight: '600', textTransform: 'uppercase' }}>{row.particulars}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', color: '#2563eb' }}>{row.ref_no}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', color: '#64748b' }}>{row.description}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', textAlign: 'right', color: '#1d4ed8', fontWeight: '600' }}>
                    {(row.debit || 0) > 0 ? (row.debit || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "-"}
                  </td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', textAlign: 'right', color: '#dc2626', fontWeight: '600' }}>
                    {(row.credit || 0) > 0 ? (row.credit || 0).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "-"}
                  </td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', textAlign: 'right', fontWeight: '700', color: (row.balance || 0) < 0 ? '#dc2626' : '#059669' }}>
                    {(row.balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))}
              <tr style={{ background: '#f1f5f9', fontWeight: '700' }}>
                <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px' }} colSpan={4}>TOTALS</td>
                <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', textAlign: 'right', color: '#1d4ed8' }}>{totalDebit.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', textAlign: 'right', color: '#dc2626' }}>{totalCredit.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                <td style={{ border: '1px solid #e2e8f0', padding: '8px 10px', textAlign: 'right' }}>{finalBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}