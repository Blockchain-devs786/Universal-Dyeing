/**
 * Share utility for sharing PDF reports via Web Share API or falling back to download.
 */

function isMobile(): boolean {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent,
  );
}

/**
 * Share a PDF file via the native share sheet.
 * Falls back to download if sharing is not supported.
 */
export async function sharePDF(blob: Blob, filename: string): Promise<void> {
  const file = new File([blob], filename, { type: "application/pdf" });

  // Check if Web Share API is available and can share files
  if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({
        files: [file],
        title: filename,
        text: "Sharing report from Universal Dyeing.",
      });
      return;
    } catch (err) {
      // User cancelled or share failed
      if ((err as Error).name !== 'AbortError') {
        console.error("Share failed:", err);
      }
    }
  }

  // Fallback: Download
  triggerDownload(blob, filename);
}

/**
 * Specifically aimed at Mailing. On mobile, uses share sheet (user picks mail).
 * On desktop, downloads and opens mailto link.
 */
export async function mailPDF(blob: Blob, filename: string, bodyText: string, recipientEmail?: string): Promise<void> {
  const file = new File([blob], filename, { type: "application/pdf" });

  // On mobile/modern browsers that support file sharing, the share sheet is the only way to attach
  if (navigator.share && navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({
        files: [file],
        title: filename,
        text: bodyText,
      });
      return;
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        console.error("Mail Share failed:", err);
      }
    }
  }

  // Desktop or No-Share Fallback:
  // 1. Download the file
  triggerDownload(blob, filename);
  
  // 2. Open mailto link (cannot auto-attach file here)
  const subject = filename.replace('.pdf', '');
  const mailtoUrl = `mailto:${recipientEmail || ''}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(bodyText)}`;
  window.open(mailtoUrl, '_blank');
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.body.appendChild(document.createElement("a"));
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => {
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, 100);
}
