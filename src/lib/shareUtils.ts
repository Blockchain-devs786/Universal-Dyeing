/**
 * Share a PDF via WhatsApp.
 *
 * Flow:
 * 1. Auto-download the PDF
 * 2. Open WhatsApp (app or web) with summary text
 * 3. User manually attaches the downloaded PDF
 *
 * No API usage, no automation — entirely user-controlled.
 *
 * @param blob       The PDF blob to share
 * @param filename   Name for the downloaded PDF
 * @param whatsapp   WhatsApp number for wa.me (digits only)
 * @param text       Summary text to pre-fill in the WhatsApp message
 */
export async function shareWhatsAppPDF(blob: Blob, filename: string, whatsapp: string, text: string): Promise<void> {
  // Download PDF to device
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  // Wait briefly for download to start, then open WhatsApp
  await new Promise((r) => setTimeout(r, 500));

  // Open WhatsApp — user manually attaches the PDF
  window.open(`https://wa.me/${whatsapp}?text=${encodeURIComponent(text)}`, '_blank');
}
