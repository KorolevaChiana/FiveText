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

  // ВСТАВЬ СЮДА СВОЙ URL СКРИПТА GOOGLE APPS SCRIPT
  const url = "https://script.google.com/macros/s/ТВОЙ_КОД_ЗДЕСЬ/exec";

  fetch(url, {
    method: "POST",
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(fingerprint)
  }).catch(e => console.warn("Ошибка отправки ловушки:", e));
})();
