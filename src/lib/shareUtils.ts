/**
 * Share a PDF via WhatsApp using the simplest manual flow:
 * 1. Try navigator.share with the PDF file (works on mobile, shows WhatsApp as option)
 * 2. Fallback: auto-download the PDF + open WhatsApp Web/me so user can manually attach
 *
 * This does NOT use any API — it's entirely user-controlled.
 *
 * @param blob       The PDF blob to share
 * @param filename   Name for the downloaded/shared PDF
 * @param whatsapp   WhatsApp number for wa.me fallback (digits only, no + or spaces)
 * @param text       Summary text to pre-fill in the WhatsApp message
 */
export async function shareWhatsAppPDF(blob: Blob, filename: string, whatsapp: string, text: string): Promise<void> {
  // Try native share first (works on mobile, shows WhatsApp as a share target)
  if (navigator.share && navigator.canShare) {
    const file = new File([blob], filename, { type: 'application/pdf' });
    const shareData = { files: [file], title: filename, text };

    if (navigator.canShare(shareData)) {
      try {
        await navigator.share(shareData);
        return; // Shared successfully
      } catch (err: any) {
        if ((err as Error).name === 'AbortError') return; // User cancelled
        // Not abort → fall through to download + WhatsApp fallback
      }
    }
  }

  // Fallback: download PDF + open WhatsApp so user can manually attach
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  // Open WhatsApp (Web or app) with summary text
  window.open(`https://wa.me/${whatsapp}?text=${encodeURIComponent(text)}`, '_blank');
}
