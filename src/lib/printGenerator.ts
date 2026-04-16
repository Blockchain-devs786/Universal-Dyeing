export const generateAndPrintHTML = (
  type: 'inward' | 'outward' | 'transfer' | 'transfer_by_name',
  documents: any[]
) => {
  const getTypeTitle = () => {
    switch (type) {
      case 'inward': return 'GOODS RECEIPT';
      case 'outward': return 'GOODS DISPATCH';
      case 'transfer': return 'GOODS TRANSFER';
      case 'transfer_by_name': return 'TRANSFER BY NAME';
      default: return 'DOCUMENT';
    }
  };

  const getNumberLabel = () => {
    switch (type) {
      case 'inward': return 'INW# :';
      case 'outward': return 'OUT# :';
      case 'transfer': return 'TRF# :';
      case 'transfer_by_name': return 'TBN# :';
      default: return 'NO# :';
    }
  };

  const getNumberValue = (doc: any) => {
    switch (type) {
      case 'inward': return doc.inward_no || '';
      case 'outward': return doc.outward_no || '';
      case 'transfer': return doc.transfer_no || '';
      case 'transfer_by_name': return doc.tbn_no || '';
      default: return '';
    }
  };

  const getToPartyHtml = (doc: any) => {
    if (type === 'outward') {
      return '<span class="meta-label">OUTWARD TO:</span>' +
        '<span class="meta-value">' + (doc.outward_to_party_name || '') + '</span>';
    }
    if (type === 'transfer' || type === 'transfer_by_name') {
      return '<span class="meta-label">TRANSFER TO:</span>' +
        '<span class="meta-value">' + (doc.transfer_to_party_name || '') + '</span>';
    }
    return '';
  };

  const CSS = `
    @page { size: A4 portrait; margin: 0; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: Arial, sans-serif; font-size: 11px; background: white; padding: 2mm; color: #1a1a1a; margin: 0; }
    .page { width: 210mm; height: 297mm; page-break-after: always; overflow: hidden; position: relative; display: flex; flex-direction: column; padding: 5mm; }
    .page:last-child { page-break-after: auto; }
    .form { width: 100%; border: 1px solid #000; padding: 6mm; margin-bottom: 2mm; page-break-inside: avoid; flex: 1; display: flex; flex-direction: column; max-height: 140mm; }
    .form:last-child { margin-bottom: 0; }
    .cut-line { border-top: 1px dashed #666; margin: 2mm 0; width: 100%; page-break-inside: avoid; height: 0; min-height: 0; }
    .header { text-align: center; margin-bottom: 2mm; position: relative; min-height: 30mm; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .logo { position: absolute; right: 0; top: 0; width: 130px; height: 130px; }
    .logo img { width: 100%; height: 100%; object-fit: contain; }
    .company-name { font-size: 16px; font-weight: bold; text-align: center; margin-bottom: 1mm; color: #0066cc; }
    .owner-info { text-align: center; font-size: 10px; margin-bottom: 1mm; color: #333333; }
    .subtitle { text-align: center; font-size: 15px; font-weight: bold; margin: 2mm 0; text-decoration: underline; color: #cc0000; }
    .meta-info { margin-bottom: 4mm; }
    .meta-row { display: flex; justify-content: space-between; margin-bottom: 2mm; font-size: 11px; }
    .meta-item { flex: 1; margin-right: 5mm; }
    .meta-item:last-child { margin-right: 0; }
    .meta-label { font-weight: bold; display: inline-block; min-width: 80px; color: #0066cc; }
    .meta-value { border-bottom: 1px solid #333; display: inline-block; min-width: 100px; padding: 0 2mm; color: #cc0000; font-weight: 500; }
    .items-table { width: 100%; border-collapse: collapse; margin-bottom: 5mm; }
    .items-table th, .items-table td { border: 1px solid #333; padding: 1.5mm; text-align: center; font-size: 11px; }
    .items-table th { background-color: #e6f2ff; font-weight: bold; color: #0066cc; }
    .items-table td { color: #1a1a1a; }
    .items-table tbody tr:nth-child(even) td { background-color: #f9f9f9; }
    .footer { margin-top: 2mm; font-size: 9px; line-height: 1.2; }
    .site-info { text-align: center; margin-top: 3mm; font-size: 10px; color: #006600; font-weight: 500; }
    .contacts { text-align: center; margin-top: 1mm; font-size: 10px; color: #cc6600; font-weight: 500; }
    @media print {
      body { padding: 0; }
      .page { margin: 0; padding: 10mm; }
      .cut-line { page-break-inside: avoid; }
      .form { page-break-inside: avoid; }
    }
  `;

  const getReferenceHtml = (doc: any) => {
    let html = '';
    
    // Check for Inward linkage first
    if (doc.inward_no || doc.inward_sr_no || doc.inward_gp_no) {
      html += '<div class="meta-row">';
      if (doc.inward_no) {
        html += '<div class="meta-item"><span class="meta-label">INW NO:</span><span class="meta-value">' + doc.inward_no + '</span></div>';
      }
      if (doc.inward_sr_no) {
        html += '<div class="meta-item"><span class="meta-label">INW SR:</span><span class="meta-value">' + doc.inward_sr_no + '</span></div>';
      }
      html += '</div>';
      
      if (doc.inward_gp_no) {
        html += '<div class="meta-row">';
        html += '<div class="meta-item"><span class="meta-label">INW GP:</span><span class="meta-value">' + doc.inward_gp_no + '</span></div>';
        html += '<div class="meta-item"></div>';
        html += '</div>';
      }
    }

    // Generic reference note
    if (doc.reference && type !== 'outward') {
      html += '<div class="meta-row">' +
        '<div class="meta-item">' +
          '<span class="meta-label">REF:</span>' +
          '<span class="meta-value">' + doc.reference + '</span>' +
        '</div>' +
        '<div class="meta-item"></div>' +
      '</div>';
    }
    
    // For Outwards print, just use the automated deductions in the table instead of manual header lines
    if (type === 'outward') {
       return ''; // Hide all manual outward reference blocks from header to save space
    }
    
    // MS Party GP No (for Inward)
    if (doc.ms_party_gp_no) {
      html += '<div class="meta-row">' +
        '<div class="meta-item">' +
          '<span class="meta-label">MS PARTY GP:</span>' +
          '<span class="meta-value">' + doc.ms_party_gp_no + '</span>' +
        '</div>' +
        '<div class="meta-item"></div>' +
      '</div>';
    }
    
    return html;
  };

  const buildFormHtml = (doc: any) => {
    const items: any[] = doc.items || [];
    const formattedDate = doc.date ? new Date(doc.date).toLocaleDateString('en-GB') : '';

    let itemRows = '';
    items.forEach((item: any) => {
      let refText = '';
      if (type === 'outward' && doc.deductions && doc.deductions.length > 0) {
        const itemDeducts = doc.deductions.filter((d: any) => d.outward_item_id === item.id);
        if (itemDeducts.length > 0) {
          const deductStrings = itemDeducts.map((d: any) => {
             let text = `INW: ${d.inward_no}`;
             if (d.inward_gp_no) text += `, GP: ${d.inward_gp_no}`;
             if (d.inward_ms_party_gp_no) text += `, MS GP: ${d.inward_ms_party_gp_no}`;
             if (d.from_party_name) text += ` (${d.from_party_name})`;
             text += ` = Qty: ${Number(d.deducted_qty)}`;
             return `[${text}]`;
          });
          refText = `<div style="font-size: 8px; color: #555; font-weight: normal; margin-top: 1px;">Refs: ${deductStrings.join(' | ')}</div>`;
        }
      }

      itemRows += '<tr>' +
        '<td>' + (item.quantity || 0) + '</td>' +
        '<td style="text-align: left; padding-left: 2mm;"><strong>' + (item.item_name || '') + '</strong>' + refText + '</td>' +
        '<td>' + (item.measurement || '') + '</td>' +
        '</tr>';
    });
 
    return (
      '<div class="form">' +
        '<div class="header">' +
          '<div class="logo"><img src="/logo.png" alt="logo"></div>' +
          '<div class="company-name">MOMINA LACE DYEING</div>' +
          '<div class="owner-info">Owner : GHULAM MUSTAFA<br>GM &nbsp;&nbsp;: Shahid, Naveed</div>' +
        '</div>' +
        '<div class="subtitle">' + getTypeTitle() + '</div>' +
        '<div class="meta-info">' +
          '<div class="meta-row">' +
            '<div class="meta-item">' +
              '<span class="meta-label">SR# :</span>' +
              '<span class="meta-value">' + (doc.sr_no || '') + '</span>' +
            '</div>' +
            '<div class="meta-item">' +
              '<span class="meta-label">DATE :</span>' +
              '<span class="meta-value">' + formattedDate + '</span>' +
            '</div>' +
          '</div>' +
          '<div class="meta-row">' +
            '<div class="meta-item">' +
              '<span class="meta-label">MS PARTY :</span>' +
              '<span class="meta-value">' + (doc.ms_party_name || '') + '</span>' +
            '</div>' +
            '<div class="meta-item">' +
              '<span class="meta-label">FROM :</span>' +
              '<span class="meta-value">' + (doc.from_party_name || '') + '</span>' +
            '</div>' +
          '</div>' +
          '<div class="meta-row">' +
            '<div class="meta-item">' +
              '<span class="meta-label">' + getNumberLabel() + '</span>' +
              '<span class="meta-value">' + getNumberValue(doc) + '</span>' +
            '</div>' +
            '<div class="meta-item">' + getToPartyHtml(doc) + '</div>' +
          '</div>' +
          getReferenceHtml(doc) +
        '</div>' +
        '<table class="items-table" style="flex-grow: 1;">' +
          '<thead><tr>' +
            '<th style="width:20%">QTY (Than)</th>' +
            '<th style="width:50%">DETAILS (Item Name)</th>' +
            '<th style="width:30%">YARDS</th>' +
          '</tr></thead>' +
          '<tbody>' + itemRows + '</tbody>' +
        '</table>' +
        '<div class="footer" style="margin-top: auto;">' +
          '<div class="site-info">SITE:<br>Small Industrial State, Sargodha Road, Faisalabad</div>' +
          '<div class="contacts">CONTACTS:<br>0321-7651815, 0300-8651815<br>0304-6166663, 0300-8636129</div>' +
          '<div style="text-align: right; margin-top: 2mm; font-size: 10px; font-weight: bold; color: #333;">CREATED BY: ' + (doc.created_by || 'Mehmood') + '</div>' +
        '</div>' +
      '</div>'
    );
  };

  let bodyHtml = '';
  const pages: any[][] = [];
  for (let i = 0; i < documents.length; i += 2) {
    pages.push(documents.slice(i, i + 2));
  }

  pages.forEach((pageDocs) => {
    bodyHtml += '<div class="page">';
    pageDocs.forEach((doc, idx) => {
      bodyHtml += buildFormHtml(doc);
      if (idx < pageDocs.length - 1) {
        bodyHtml += '<div class="cut-line"></div>';
      }
    });
    bodyHtml += '</div>';
  });

  const fullHtml =
    '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Print</title>' +
    '<base href="' + window.location.origin + '/">' +
    '<style>' + CSS + '</style>' +
    '</head><body>' +
    bodyHtml +
    '<script>window.onload=function(){window.print();}<\/script>' +
    '</body></html>';

  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(fullHtml);
    printWindow.document.close();
  } else {
    alert('Please allow popups to print documents.');
  }
};
