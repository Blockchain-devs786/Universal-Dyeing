/**
 * Share a PDF via platform-appropriate method.
 *
 * Desktop:
 *   - Downloads the PDF to the Downloads folder (no WhatsApp / no browser link)
 *
 * Mobile:
 *   - Uses the native Web Share API (navigator.share) to open the share sheet
 *   - The PDF is auto-attached as a File so it can be shared directly to WhatsApp,
 *     email, or any other app on the device
 */

/**
 * Returns true if running on a mobile device.
 */
function isMobile(): boolean {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent,
  );
}

export async function sharePDF(
  blob: Blob,
  filename: string,
): Promise<void> {
  // On mobile, try the native share sheet
  if (isMobile() && navigator.share && window.isSecureContext) {
    const file = new File([blob], filename, { type: "application/pdf" });
    const shareData: ShareData = {
      files: [file],
    };
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share(shareData);
      return;
    }
  }

  // Desktop (or fallback): download file only, do NOT open WhatsApp
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
