export const generateAndPrintHTML = (type: 'inward' | 'outward' | 'transfer' | 'transfer_by_name', documents: any[]) => {
  const getLogoBase64 = () => {
    // In browser context, we can just use the public logo url assuming it exists
    // Fallback to text logo if none available
    return `<div style="width: 100%; height: 100%; background: transparent; border: 1px dashed #ccc; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999;">LOGO</div>`;
  };

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
      case 'inward': return doc.inward_no;
      case 'outward': return doc.outward_no;
      case 'transfer': return doc.transfer_no;
      case 'transfer_by_name': return doc.tbn_no;
      default: return '';
    }
  };

  let html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Print Documents</title>
    <style>
        @page {
            size: A4 portrait;
            margin: 0;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 12px;
            background: white;
            padding: 10mm;
            color: #1a1a1a;
        }
        .page {
            width: 210mm;
            min-height: 297mm;
            page-break-after: always;
            position: relative;
        }
        .page:last-child {
            page-break-after: auto;
        }
        .form {
            width: auto;
            border: 1px solid #000;
            padding: 8mm;
            margin-bottom: 5mm;
        }
        .form:last-child {
            margin-bottom: 0;
        }
        .cut-line {
            border-top: 2px dashed #666;
            margin: 5mm 0;
            width: 100%;
        }
        .header {
            text-align: center;
            margin-bottom: 8mm;
            position: relative;
        }
        .company-name {
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 3mm;
            color: #0066cc;
        }
        .logo {
            position: absolute;
            right: 0;
            top: 0;
            width: 45mm;
            height: 45mm;
            background: transparent;
        }
        .owner-info {
            text-align: center;
            font-size: 11px;
            margin-bottom: 2mm;
            color: #333333;
        }
        .subtitle {
            text-align: center;
            font-size: 16px;
            font-weight: bold;
            margin: 5mm 0;
            text-decoration: underline;
            color: #cc0000;
        }
        .meta-info {
            margin-bottom: 5mm;
        }
        .meta-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2mm;
            font-size: 11px;
            color: #1a1a1a;
        }
        .meta-item {
            flex: 1;
            margin-right: 5mm;
        }
        .meta-label {
            font-weight: bold;
            display: inline-block;
            min-width: 80px;
            color: #0066cc;
        }
        .meta-value {
            border-bottom: 1px solid #333;
            display: inline-block;
            min-width: 100px;
            padding: 0 2mm;
            color: #cc0000;
            font-weight: 500;
        }
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5mm;
        }
        .items-table th, .items-table td {
            border: 1px solid #333;
            padding: 2mm;
            text-align: left;
        }
        .items-table th {
            background-color: #e6f2ff;
            font-weight: bold;
            text-align: center;
            color: #0066cc;
        }
        .items-table td {
            text-align: center;
            color: #1a1a1a;
        }
        .items-table tbody tr:nth-child(even) td {
            background-color: #f9f9f9;
        }
        .footer {
            margin-top: 5mm;
            font-size: 10px;
        }
        .site-info {
            text-align: center;
            margin-top: 3mm;
            font-size: 10px;
            color: #006600;
            font-weight: 500;
        }
        .contacts {
            text-align: center;
            margin-top: 1mm;
            font-size: 10px;
            color: #cc6600;
            font-weight: 500;
        }
        @media print {
            body { padding: 0; }
            .page { margin: 0; padding: 10mm; }
            .cut-line { page-break-inside: avoid; }
            .form { page-break-inside: avoid; }
        }
    </style>
</head>
<body>`;

  const pages = [];
  for (let i = 0; i < documents.length; i += 2) {
    pages.push(documents.slice(i, i + 2));
  }

  pages.forEach((pageDocs) => {
    html += '<div class="page">\n';
    
    pageDocs.forEach((doc, idx) => {
      const items = (doc.items || []);
      const formattedDate = new Date(doc.date).toLocaleDateString('en-GB') || '';

      html += \`
        <div class="form">
            <div class="header">
                <div class="logo">\${getLogoBase64()}</div>
                <div class="company-name">MOMINA LACE DYEING</div>
                <div class="owner-info">
                    Owner : GHULAM MUSTAFA<br>
                    GM    : Shahid, Naveed
                </div>
            </div>
            
            <div class="subtitle">\${getTypeTitle()}</div>
            
            <div class="meta-info">
                <div class="meta-row">
                    <div class="meta-item">
                        <span class="meta-label">SR# :</span>
                        <span class="meta-value">\${doc.sr_no || ''}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">DATE :</span>
                        <span class="meta-value">\${formattedDate}</span>
                    </div>
                </div>
                <div class="meta-row">
                    <div class="meta-item">
                        <span class="meta-label">MS PARTY :</span>
                        <span class="meta-value">\${doc.ms_party_name || ''}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">FROM :</span>
                        <span class="meta-value">\${doc.from_party_name || ''}</span>
                    </div>
                </div>
                <div class="meta-row">
                    <div class="meta-item">
                        <span class="meta-label">\${getNumberLabel()}</span>
                        <span class="meta-value">\${getNumberValue(doc)}</span>
                    </div>
                    <div class="meta-item">
                        \${type === 'outward' ? \`<span class="meta-label">OUTWARD TO:</span>
                        <span class="meta-value">\${doc.outward_to_party_name || ''}</span>\` : ''}
                        \${type === 'transfer' ? \`<span class="meta-label">TRANSFER TO:</span>
                        <span class="meta-value">\${doc.transfer_to_party_name || ''}</span>\` : ''}
                        \${type === 'transfer_by_name' ? \`<span class="meta-label">TRANSFER TO:</span>
                        <span class="meta-value">\${doc.transfer_to_party_name || ''}</span>\` : ''}
                    </div>
                </div>
            </div>
            
            <table class="items-table">
                <thead>
                    <tr>
                        <th style="width: 20%;">QTY (Than)</th>
                        <th style="width: 50%;">DETAILS (Item Name)</th>
                        <th style="width: 30%;">YARDS</th>
                    </tr>
                </thead>
                <tbody>
      \`;

      items.forEach((item: any) => {
        html += \`
            <tr>
                <td>\${item.quantity || 0}</td>
                <td>\${item.item_name || ''}</td>
                <td>\${item.measurement || ''}</td>
            </tr>
        \`;
      });

      const emptyRows = Math.max(0, 3 - items.length);
      for (let j = 0; j < emptyRows; j++) {
        html += \`
            <tr>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
                <td>&nbsp;</td>
            </tr>
        \`;
      }

      html += \`
                </tbody>
            </table>
            
            <div class="footer">
                <div class="site-info">
                    SITE:<br>
                    Small Industrial State, Sargodha Road, Faisalabad
                </div>
                <div class="contacts">
                    CONTACTS:<br>
                    0321-7651815, 0300-8651815<br>
                    0304-6166663, 0300-8636129
                </div>
            </div>
        </div>
      \`;

      if (idx < pageDocs.length - 1) {
        html += '<div class="cut-line"></div>\n';
      }
    });

    html += '</div>\n';
  });

  html += \`
      <script>
          window.onload = function() {
              window.print();
          };
      </script>
  </body>
  </html>
  \`;

  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(html);
    printWindow.document.close();
  } else {
    alert("Please allow popups to print documents.");
  }
};
