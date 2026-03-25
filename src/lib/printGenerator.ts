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
    body { font-family: Arial, sans-serif; font-size: 12px; background: white; padding: 10mm; color: #1a1a1a; }
    .page { width: 190mm; page-break-after: always; }
    .page:last-child { page-break-after: auto; }
    .form { width: 100%; border: 1px solid #000; padding: 8mm; margin-bottom: 5mm; }
    .form:last-child { margin-bottom: 0; }
    .cut-line { border-top: 2px dashed #666; margin: 5mm 0; width: 100%; }
    .header { text-align: center; margin-bottom: 6mm; position: relative; min-height: 30mm; }
    .company-name { font-size: 18px; font-weight: bold; text-align: center; margin-bottom: 3mm; color: #0066cc; }
    .owner-info { text-align: center; font-size: 11px; margin-bottom: 2mm; color: #333333; }
    .subtitle { text-align: center; font-size: 16px; font-weight: bold; margin: 5mm 0; text-decoration: underline; color: #cc0000; }
    .meta-info { margin-bottom: 5mm; }
    .meta-row { display: flex; justify-content: space-between; margin-bottom: 2mm; font-size: 11px; }
    .meta-item { flex: 1; margin-right: 5mm; }
    .meta-item:last-child { margin-right: 0; }
    .meta-label { font-weight: bold; display: inline-block; min-width: 80px; color: #0066cc; }
    .meta-value { border-bottom: 1px solid #333; display: inline-block; min-width: 100px; padding: 0 2mm; color: #cc0000; font-weight: 500; }
    .items-table { width: 100%; border-collapse: collapse; margin-bottom: 5mm; }
    .items-table th, .items-table td { border: 1px solid #333; padding: 2mm; text-align: center; }
    .items-table th { background-color: #e6f2ff; font-weight: bold; color: #0066cc; }
    .items-table td { color: #1a1a1a; }
    .items-table tbody tr:nth-child(even) td { background-color: #f9f9f9; }
    .footer { margin-top: 5mm; font-size: 10px; }
    .site-info { text-align: center; margin-top: 3mm; font-size: 10px; color: #006600; font-weight: 500; }
    .contacts { text-align: center; margin-top: 1mm; font-size: 10px; color: #cc6600; font-weight: 500; }
    @media print {
      body { padding: 0; }
      .page { margin: 0; padding: 10mm; }
      .cut-line { page-break-inside: avoid; }
      .form { page-break-inside: avoid; }
    }
  `;

  const buildFormHtml = (doc: any) => {
    const items: any[] = doc.items || [];
    const formattedDate = doc.date ? new Date(doc.date).toLocaleDateString('en-GB') : '';

    let itemRows = '';
    items.forEach((item: any) => {
      itemRows += '<tr>' +
        '<td>' + (item.quantity || 0) + '</td>' +
        '<td>' + (item.item_name || '') + '</td>' +
        '<td>' + (item.measurement || '') + '</td>' +
        '</tr>';
    });

    const emptyCount = Math.max(0, 3 - items.length);
    for (let j = 0; j < emptyCount; j++) {
      itemRows += '<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>';
    }

    return (
      '<div class="form">' +
        '<div class="header">' +
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
        '</div>' +
        '<table class="items-table">' +
          '<thead><tr>' +
            '<th style="width:20%">QTY (Than)</th>' +
            '<th style="width:50%">DETAILS (Item Name)</th>' +
            '<th style="width:30%">YARDS</th>' +
          '</tr></thead>' +
          '<tbody>' + itemRows + '</tbody>' +
        '</table>' +
        '<div class="footer">' +
          '<div class="site-info">SITE:<br>Small Industrial State, Sargodha Road, Faisalabad</div>' +
          '<div class="contacts">CONTACTS:<br>0321-7651815, 0300-8651815<br>0304-6166663, 0300-8636129</div>' +
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
