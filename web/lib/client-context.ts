// Auto-detected submission context (device/browser/platform) sent
// silently alongside a feedback submission - useful signal for admin
// triage, unlike the old dashboard's product/module/version/region
// randomization, which was fabricated and deliberately not ported.

function detectBrowser(userAgent: string): string {
  if (userAgent.includes("Edg/")) return "Edge";
  if (userAgent.includes("Chrome/") && !userAgent.includes("Chromium")) return "Chrome";
  if (userAgent.includes("Firefox/")) return "Firefox";
  if (userAgent.includes("Safari/") && !userAgent.includes("Chrome")) return "Safari";
  return "Other";
}

function detectPlatform(userAgent: string): string {
  if (/android/i.test(userAgent)) return "Android";
  if (/iphone|ipad|ipod/i.test(userAgent)) return "iOS";
  if (/mac/i.test(userAgent)) return "macOS";
  if (/win/i.test(userAgent)) return "Windows";
  if (/linux/i.test(userAgent)) return "Linux";
  return "Other";
}

function detectDevice(userAgent: string): string {
  if (/mobile/i.test(userAgent)) return "Mobile";
  if (/tablet|ipad/i.test(userAgent)) return "Tablet";
  return "Desktop";
}

export function detectClientContext(): { device: string; browser: string; platform: string } {
  if (typeof navigator === "undefined") {
    return { device: "Unknown", browser: "Unknown", platform: "Unknown" };
  }
  const userAgent = navigator.userAgent;
  return {
    device: detectDevice(userAgent),
    browser: detectBrowser(userAgent),
    platform: detectPlatform(userAgent),
  };
}
