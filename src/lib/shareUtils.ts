/**
 * Share a PDF via WhatsApp.
 *
 * Flow:
 * 1. Save the PDF to disk first
 * 2. Open native share screen with PDF attached
 *    - On mobile: WhatsApp appears as a share option
 *    - On desktop: system share dialog (may not support all targets)
 *
 * File is downloaded before the share dialog opens — so even if share
 * closes immediately, the PDF is already available for manual attach.
 *
 * No API, no automation — entirely user-controlled.
 *
 * @param blob       The PDF blob to share
 * @param filename   Name for the downloaded/shared PDF
 * @param whatsapp   WhatsApp number for wa.me fallback (digits only)
 * @param text       Summary text to pre-fill in the WhatsApp message
 */
export async function shareWhatsAppPDF(
  blob: Blob,
  filename: string,
  whatsapp: string,
  text: string,
): Promise<void> {
  // Step 1: Download PDF to device first (always succeeds)
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  // Step 2: Brief delay, then try native share with File
  await new Promise((r) => setTimeout(r, 600));
  if (navigator.share) {
    const file = new File([blob], filename, { type: 'application/pdf' });
    try {
      await navigator.share({ files: [file], title: filename, text });
      return;
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return;
      // Share failed — ignore and skip to fallback
    }
  }

  // Step 3: Fallback — open WhatsApp Web for manual attach
  window.open(
    `https://wa.me/${whatsapp}?text=${encodeURIComponent(text)}`,
    '_blank',
  );
}
