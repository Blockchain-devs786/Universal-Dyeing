import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  RefreshCw,
  Printer,
  Search,
  Check,
  ChevronsUpDown,
  Filter,
  MessageSquare,
  Share2,
  Mail
} from "lucide-react";
import {
  reportsApi,
  msPartiesApi,
  itemsApi,
  settingsApi,
  type StockReportRow,
} from "@/lib/api-client";
import { format } from "date-fns";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { sharePDF } from "@/lib/shareUtils";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { cn } from "@/lib/utils";

export default function StockReport() {
  const [filterMsPartyId, setFilterMsPartyId] = useState<string>("all");
  const [filterItemId, setFilterItemId] = useState<string>("all");

  const [msPartyOpen, setMsPartyOpen] = useState(false);
  const [itemOpen, setItemOpen] = useState(false);

  const printRef = useRef<HTMLDivElement>(null);

  // Data Queries
  const { data: stocks = [], isLoading, refetch, isFetching } = useQuery({
    queryKey: ["reports_stock", filterMsPartyId, filterItemId],
    queryFn: () => reportsApi.getStock(filterMsPartyId, filterItemId),
  });

  const { data: msParties = [] } = useQuery({
    queryKey: ["ms_parties"],
    queryFn: () => msPartiesApi.list(),
  });

  const { data: items = [] } = useQuery({
    queryKey: ["items"],
    queryFn: () => itemsApi.list(),
  });

  const { data: settings = [] } = useQuery({ queryKey: ["settings"], queryFn: () => settingsApi.list() });
  const getSetting = (key: string) => settings.find(s => s.key === key)?.value || "";

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
      windowWidth: 894,
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


  // Calculate Aggregates for KPI cards
  const aggregates = stocks.reduce(
    (acc, row) => {
      acc.total_inward += row.total_inward;
      acc.total_outward += row.total_outward;
      acc.total_transfer += row.total_transfer;
      acc.transfer_in += row.transfer_in;
      acc.transfer_out += row.transfer_out;
      acc.net_remaining += row.remaining;
      return acc;
    },
    {
      total_inward: 0,
      total_outward: 0,
      total_transfer: 0,
      transfer_in: 0,
      transfer_out: 0,
      net_remaining: 0,
    }
  );

  const selectedMsPartyObj = msParties.find(p => String(p.id) === filterMsPartyId);
  const selectedItemObj = items.find(i => String(i.id) === filterItemId);

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-500">

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 page-header-gradient p-6 rounded-2xl text-white shadow-elevated">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Stock Report</h1>
          <p className="text-white/80 mt-1">Monitor inventory levels across all MS Parties and items.</p>
        </div>

        <div className="flex gap-3 print:hidden">
          <Button
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            className="shadow-sm bg-white text-slate-800"
          >
            <RefreshCw className={cn("mr-2 h-4 w-4 text-slate-800", isFetching && "animate-spin")} />
            Refresh
          </Button>
          <Button
            onClick={handlePrint}
            className="bg-white hover:bg-white/90 text-primary shadow-sm"
          >
            <Printer className="mr-2 h-4 w-4" />
            Print
          </Button>

          <Button
            variant="outline"
            className="bg-green-500 hover:bg-green-600 text-white border-none shadow-sm"
            onClick={async () => {
              const blob = await generatePDFBlob();
              const filename = `StockReport_${format(new Date(), 'yyyyMMdd')}.pdf`;
              await sharePDF(blob, filename);
            }}
          >
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>

          <Button
            variant="outline"
            className="bg-slate-700 hover:bg-slate-800 text-white border-none shadow-sm"
            onClick={async () => {
              const email = getSetting("email");
              const subject = `Stock Report: ${filterMsPartyId === "all" ? "Combined" : selectedMsPartyObj?.name}`;
              const body = `Stock Report Summary:\nParty: ${filterMsPartyId === "all" ? "All Parties" : selectedMsPartyObj?.name}\nNet Remaining: ${aggregates.net_remaining.toLocaleString()}`;
              const filename = `StockReport_${format(new Date(), 'yyyyMMdd')}.pdf`;
              const blob = await generatePDFBlob();

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
      </div>

      {/* Filters Section */}
      <div className="bg-white p-5 rounded-xl shadow-sm border border-border/50 print:hidden">
        <div className="flex items-center gap-2 mb-4 text-blue-600">
          <Filter className="h-4 w-4" />
          <h2 className="font-semibold text-sm">Filters</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">MS Party</Label>
            <Popover open={msPartyOpen} onOpenChange={setMsPartyOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={msPartyOpen}
                  className="w-full justify-between font-normal bg-slate-50/50 h-10"
                >
                  <span className="truncate">{filterMsPartyId === "all" ? "All Parties" : selectedMsPartyObj?.name || "All Parties"}</span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search ms party..." />
                  <CommandList>
                    <CommandEmpty>No records found.</CommandEmpty>
                    <CommandGroup>
                      <CommandItem
                        value="all"
                        onSelect={() => {
                          setFilterMsPartyId("all");
                          setMsPartyOpen(false);
                        }}
                      >
                        <Check className={cn("mr-2 h-4 w-4", filterMsPartyId === "all" ? "opacity-100" : "opacity-0")} />
                        All Parties
                      </CommandItem>
                      {msParties.map((party) => (
                        <CommandItem
                          key={party.id}
                          value={party.name}
                          onSelect={() => {
                            setFilterMsPartyId(String(party.id));
                            setMsPartyOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              filterMsPartyId === String(party.id) ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {party.name}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Search Item</Label>
            <Popover open={itemOpen} onOpenChange={setItemOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={itemOpen}
                  className="w-full justify-between font-normal bg-slate-50/50 h-10"
                >
                  <span className="truncate">{filterItemId === "all" ? "All Items" : selectedItemObj?.name || "All Items"}</span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[300px] p-0" align="start">
                <Command>
                  <CommandInput placeholder="Search items..." />
                  <CommandList>
                    <CommandEmpty>No records found.</CommandEmpty>
                    <CommandGroup>
                      <CommandItem
                        value="all"
                        onSelect={() => {
                          setFilterItemId("all");
                          setItemOpen(false);
                        }}
                      >
                        <Check className={cn("mr-2 h-4 w-4", filterItemId === "all" ? "opacity-100" : "opacity-0")} />
                        All Items
                      </CommandItem>
                      {items.map((item) => (
                        <CommandItem
                          key={item.id}
                          value={item.name}
                          onSelect={() => {
                            setFilterItemId(String(item.id));
                            setItemOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              filterItemId === String(item.id) ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {item.name}
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

      {/* KPI Cards Grid (Hidden in Print) */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 print:hidden">
        <KPICard title="TOTAL INWARD" value={aggregates.total_inward} numeralColor="text-blue-600" />
        <KPICard title="TOTAL OUTWARD" value={aggregates.total_outward} numeralColor="text-orange-500" />
        <KPICard title="TOTAL TRANSFER" value={aggregates.total_transfer} numeralColor="text-purple-500" />
        <KPICard title="TRANSFER IN" value={aggregates.transfer_in} numeralColor="text-emerald-500" />
        <KPICard title="TRANSFER OUT" value={aggregates.transfer_out} numeralColor="text-red-500" />
        <div className="bg-white p-5 rounded-xl shadow-sm border-2 border-blue-500/80 flex flex-col items-center justify-center text-center">
          <span className="text-xs font-semibold text-muted-foreground tracking-widest mb-3 uppercase">Net Remaining</span>
          <span className="text-3xl font-bold tracking-tight text-blue-600">{aggregates.net_remaining.toLocaleString()}</span>
        </div>
      </div>

      {/* Print-Only Summary Box (Hidden on Screen) */}
      <div className="hidden print:block mb-6 space-y-4">
        <div className="flex justify-between items-end border-b border-border/60 pb-2">
           <div className="flex gap-8">
             <p className="text-sm font-semibold text-slate-600">
               MS Party: <span className="font-bold text-black">{filterMsPartyId === "all" ? "All Parties" : selectedMsPartyObj?.name}</span>
             </p>
             <p className="text-sm font-semibold text-slate-600">
               Search Item: <span className="font-bold text-black">{filterItemId === "all" ? "All Items" : selectedItemObj?.name}</span>
             </p>
           </div>
           <p className="text-xs text-slate-500">Printed on: {new Date().toLocaleString()}</p>
        </div>

        <div className="flex justify-between items-center p-3 border rounded-lg bg-slate-50 font-semibold shadow-sm text-center">
           <div><span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Total Inward</span><span className="text-blue-600 text-base">{aggregates.total_inward.toLocaleString()}</span></div>
           <div><span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Total Outward</span><span className="text-orange-500 text-base">{aggregates.total_outward.toLocaleString()}</span></div>
           <div><span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Total Transfer</span><span className="text-purple-500 text-base">{aggregates.total_transfer.toLocaleString()}</span></div>
           <div><span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Transfer IN</span><span className="text-emerald-500 text-base">{aggregates.transfer_in.toLocaleString()}</span></div>
           <div><span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Transfer OUT</span><span className="text-red-500 text-base">{aggregates.transfer_out.toLocaleString()}</span></div>
           <div className="border-l border-slate-300 pl-4 py-1">
             <span className="text-[10px] text-muted-foreground uppercase tracking-wider block mb-1">Net Remaining</span>
             <span className="text-blue-700 font-bold text-lg">{aggregates.net_remaining.toLocaleString()}</span>
           </div>
        </div>
      </div>

      {/* Hidden Print Container for HTML-to-PDF */}
      <div ref={printRef} style={{ position: 'fixed', top: 0, left: 0, zIndex: -2, width: '794px', background: 'white', visibility: 'hidden', opacity: 0, color: '#1e293b', fontSize: '14px' }}>
        <div style={{ padding: '40px 40px 20px 40px' }}>
          <h1 style={{ fontSize: '26px', fontWeight: 'bold', marginBottom: '4px' }}>Stock Report</h1>
          <p style={{ fontSize: '14px', color: '#64748b', marginBottom: '16px' }}>
            MS Party: {filterMsPartyId === "all" ? "All Parties" : selectedMsPartyObj?.name} |
            Item: {filterItemId === "all" ? "All Items" : selectedItemObj?.name}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', border: '1px solid #e2e8f0', borderRadius: '8px', background: '#f8fafc', marginBottom: '20px', fontSize: '13px', fontWeight: '600' }}>
            <div style={{ textAlign: 'center' }}><span style={{ display: 'block', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Total Inward</span><span style={{ color: '#2563eb' }}>{aggregates.total_inward.toLocaleString() || '-'}</span></div>
            <div style={{ textAlign: 'center' }}><span style={{ display: 'block', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Total Outward</span><span style={{ color: '#f97316' }}>{aggregates.total_outward.toLocaleString() || '-'}</span></div>
            <div style={{ textAlign: 'center' }}><span style={{ display: 'block', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Total Transfer</span><span style={{ color: '#a855f7' }}>{aggregates.total_transfer.toLocaleString() || '-'}</span></div>
            <div style={{ textAlign: 'center' }}><span style={{ display: 'block', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Transfer IN</span><span style={{ color: '#10b981' }}>{aggregates.transfer_in.toLocaleString() || '-'}</span></div>
            <div style={{ textAlign: 'center' }}><span style={{ display: 'block', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Transfer OUT</span><span style={{ color: '#ef4444' }}>{aggregates.transfer_out.toLocaleString() || '-'}</span></div>
            <div style={{ borderLeft: '1px solid #cbd5e1', paddingLeft: '16px', marginLeft: '8px' }}>
              <span style={{ display: 'block', fontSize: '11px', color: '#64748b', marginBottom: '4px' }}>Net Remaining</span>
              <span style={{ color: '#1d4ed8', fontWeight: 'bold' }}>{aggregates.net_remaining.toLocaleString()}</span>
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ background: '#f1f5f9' }}>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'left', color: '#475569', fontWeight: '600' }}>Item Name</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', color: '#475569', fontWeight: '600' }}>MSR</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'left', color: '#475569', fontWeight: '600' }}>MS Party</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', color: '#2563eb', fontWeight: '600' }}>Total Inward</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', color: '#f97316', fontWeight: '600' }}>Total Outward</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', color: '#a855f7', fontWeight: '600' }}>Total Transfer</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', color: '#10b981', fontWeight: '600' }}>Transfer IN</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', color: '#ef4444', fontWeight: '600' }}>Transfer OUT</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', borderRadius: '0 8px 8px 0', color: '#1d4ed8', fontWeight: '700' }}>Remaining</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((row, idx) => (
                <tr key={idx} style={{ background: idx % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', fontWeight: '500' }}>{row.item_name}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '500' }}>{row.msr}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px' }}>{row.ms_party_name}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '600', color: '#2563eb' }}>{row.total_inward || '-'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '600', color: '#f97316' }}>{row.total_outward || '-'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '600', color: '#a855f7' }}>{row.total_transfer || '-'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '600', color: '#10b981' }}>{row.transfer_in || '-'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '600', color: '#ef4444' }}>{row.transfer_out || '-'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '10px 12px', textAlign: 'center', fontWeight: '700', color: '#1d4ed8' }}>{row.remaining}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white shadow-sm rounded-xl overflow-hidden border">
        <Table>
          <TableHeader className="bg-slate-50 border-b">
            <TableRow>
              <TableHead className="py-4 font-semibold text-slate-600">Item Name</TableHead>
              <TableHead className="font-semibold text-slate-600 text-center">MSR</TableHead>
              <TableHead className="font-semibold text-slate-600">MS Party</TableHead>
              <TableHead className="font-semibold text-slate-600 text-center">Total Inward</TableHead>
              <TableHead className="font-semibold text-slate-600 text-center">Total Outward</TableHead>
              <TableHead className="font-semibold text-slate-600 text-center">Total Transfer</TableHead>
              <TableHead className="font-semibold text-slate-600 text-center">Transfer IN</TableHead>
              <TableHead className="font-semibold text-slate-600 text-center">Transfer OUT</TableHead>
              <TableHead className="font-semibold text-blue-600 bg-blue-50/50 text-center">Remaining</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-10 text-muted-foreground">Loading stock report...</TableCell>
              </TableRow>
            ) : stocks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                  No stock records found matching your filters.
                </TableCell>
              </TableRow>
            ) : (
              stocks.map((row, idx) => (
                <TableRow key={idx} className="transition-colors hover:bg-slate-50/80 group">
                  <TableCell className="font-medium text-slate-800 py-3">{row.item_name}</TableCell>
                  <TableCell className="text-center font-medium">{row.msr}</TableCell>
                  <TableCell className="font-medium text-slate-600">{row.ms_party_name}</TableCell>
                  <TableCell className="text-center font-semibold text-blue-600/80">{row.total_inward || '-'}</TableCell>
                  <TableCell className="text-center font-semibold text-orange-500/80">{row.total_outward || '-'}</TableCell>
                  <TableCell className="text-center font-semibold text-purple-500/80">{row.total_transfer || '-'}</TableCell>
                  <TableCell className="text-center font-semibold text-emerald-500/80">{row.transfer_in || '-'}</TableCell>
                  <TableCell className="text-center font-semibold text-red-500/80">{row.transfer_out || '-'}</TableCell>
                  <TableCell className="text-center font-bold text-blue-700 bg-blue-50/30">
                    {row.remaining}
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

function KPICard({ title, value, numeralColor }: { title: string, value: number, numeralColor: string }) {
  return (
    <div className="bg-white p-5 rounded-xl shadow-sm border border-border/60 flex flex-col items-center justify-center text-center transition-all hover:shadow-md">
      <span className="text-xs font-semibold text-muted-foreground tracking-widest mb-3 uppercase">{title}</span>
      <span className={`text-3xl font-bold tracking-tight ${numeralColor}`}>
        {value.toLocaleString()}
      </span>
    </div>
  );
}
