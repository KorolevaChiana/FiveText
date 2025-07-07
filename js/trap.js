(function() {
  const fingerprint = {
    userAgent: navigator.userAgent,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen: window.screen.width + "x" + window.screen.height,
    platform: navigator.platform,
    plugins: Array.from(navigator.plugins).map(p => p.name).join(", "),
    timestamp: new Date().toISOString()
  };

  fetch("https://script.google.com/macros/s/AKfycbynlJMdPq34qSawrGVRz4_DWeAEFlby0NZRg4Fc8SMOd3_AUBIPMeZa68fs9fQL7AQ8_w/exec", {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fingerprint)
  }).catch(e => console.warn("Ошибка отправки ловушки:", e));
})();
