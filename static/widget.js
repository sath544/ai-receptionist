// widget.js - embeddable chat widget
// Usage on client sites:
// <script src="https://your-domain.com/static/widget.js?client=acme&color=%232563eb&logo=https%3A%2F%2Facme.com%2Flogo.png" async></script>

(function () {
  if (window.AI_WIDGET_LOADED) return;
  window.AI_WIDGET_LOADED = true;

  // Read query params from the script src
  function readScriptParams() {
    try {
      var scripts = document.getElementsByTagName("script");
      for (var i = scripts.length - 1; i >= 0; i--) {
        var s = scripts[i];
        if (s.src && s.src.indexOf("widget.js") !== -1) {
          var q = s.src.split("?")[1] || "";
          var params = {};
          q.split("&").forEach(function (pair) {
            if (!pair) return;
            var kv = pair.split("=");
            params[decodeURIComponent(kv[0])] = decodeURIComponent(kv[1] || "");
          });
          return params;
        }
      }
    } catch (e) { /* ignore */ }
    return {};
  }

  var params = readScriptParams();
  var client = params.client || "";
  var color = params.color || "#2563eb";
  var logo = params.logo || "";

  // Create container
  var container = document.createElement("div");
  container.id = "ai-widget-container";
  document.body.appendChild(container);

  // Styles
  var css = '\
  #ai-widget-container { position: fixed; right: 18px; bottom: 18px; z-index: 999999; font-family: Arial, sans-serif; } \
  #ai-widget-btn { background:' + color + '; color: #fff; border: none; padding: 12px 16px; border-radius: 999px; cursor: pointer; box-shadow: 0 6px 20px rgba(0,0,0,.15); } \
  #ai-widget-box { width: 360px; height: 520px; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,.2); margin-top: 10px; display: none; } \
  #ai-widget-iframe { width: 100%; height: 100%; border: 0; } \
  #ai-widget-header { display:flex; align-items:center; gap:10px; padding:10px 12px; background:' + color + '; color:#fff; } \
  #ai-widget-logo { height:32px; width:32px; object-fit:contain; border-radius:6px; background:rgba(255,255,255,0.06); padding:4px } \
  ';
  var style = document.createElement("style");
  style.innerHTML = css;
  document.head.appendChild(style);

  // Button
  var btn = document.createElement("button");
  btn.id = "ai-widget-btn";
  btn.innerText = "Chat";
  container.appendChild(btn);

  // Box
  var box = document.createElement("div");
  box.id = "ai-widget-box";

  // build iframe content source (pass client slug so app can load client-specific data)
  var host = location.protocol + "//" + location.host;
  var iframeSrc = host + "/?widget=1" + (client ? ("&client=" + encodeURIComponent(client)) : "");
  // allow additional branding params
  if (color) iframeSrc += "&color=" + encodeURIComponent(color);
  if (logo) iframeSrc += "&logo=" + encodeURIComponent(logo);

  var iframe = document.createElement("iframe");
  iframe.id = "ai-widget-iframe";
  iframe.src = iframeSrc;
  iframe.referrerPolicy = "no-referrer";

  box.appendChild(iframe);
  container.appendChild(box);

  var open = false;
  btn.addEventListener("click", function () {
    open = !open;
    box.style.display = open ? "block" : "none";
    if (open) {
      // bring iframe to front (in case of z-index issues)
      iframe.contentWindow.focus && iframe.contentWindow.focus();
    }
  });

  // simple keyboard accessibility: open with 'm' key when focused on page
  document.addEventListener("keydown", function (e) {
    if (e.key === "m" || e.key === "M") {
      btn.click();
    }
  });
})();
