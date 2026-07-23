/**
 * Asis Asistan — entegre edilebilir chatbot widget'ı.
 *
 * Herhangi bir sayfaya eklemek için tek satır yeterlidir:
 *   <script src="/js/chatbot-widget.js"></script>
 *
 * Sağ altta bir sohbet balonu oluşturur; mesajları POST /api/chat
 * endpoint'ine gönderir ve dönen linkleri tıklanabilir buton olarak çizer.
 */
(function () {
  "use strict";

  const API_URL = "/api/chat";

  // ---------- Stil ----------
  const style = document.createElement("style");
  style.textContent = `
    #asis-chat-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 60px; height: 60px; border-radius: 50%;
      background: #1d9bf0; color: #fff; border: none; cursor: pointer;
      font-size: 26px; box-shadow: 0 4px 14px rgba(0,0,0,.25);
      display: flex; align-items: center; justify-content: center;
      transition: transform .15s;
    }
    #asis-chat-btn:hover { transform: scale(1.08); }
    #asis-chat-panel {
      position: fixed; bottom: 96px; right: 24px; z-index: 9999;
      width: 360px; max-width: calc(100vw - 32px); height: 480px;
      max-height: calc(100vh - 130px);
      background: #fff; border-radius: 14px; overflow: hidden;
      box-shadow: 0 8px 30px rgba(0,0,0,.25);
      display: none; flex-direction: column;
      font-family: "Segoe UI", system-ui, sans-serif;
    }
    #asis-chat-panel.open { display: flex; }
    .asis-chat-header {
      background: #0d3b66; color: #fff; padding: 14px 16px;
      font-weight: 600; display: flex; align-items: center; gap: 10px;
    }
    .asis-chat-header .dot {
      width: 9px; height: 9px; border-radius: 50%; background: #4ade80;
    }
    .asis-chat-messages {
      flex: 1; overflow-y: auto; padding: 14px;
      display: flex; flex-direction: column; gap: 10px; background: #f4f6fa;
    }
    .asis-msg {
      max-width: 85%; padding: 9px 13px; border-radius: 12px;
      font-size: .9rem; line-height: 1.45; white-space: pre-wrap;
    }
    .asis-msg.user {
      align-self: flex-end; background: #1d9bf0; color: #fff;
      border-bottom-right-radius: 3px;
    }
    .asis-msg.bot {
      align-self: flex-start; background: #fff; color: #1f2a37;
      border: 1px solid #e2e8f0; border-bottom-left-radius: 3px;
    }
    .asis-links { display: flex; flex-direction: column; gap: 6px; align-self: flex-start; max-width: 85%; }
    .asis-link-btn {
      display: block; background: #e8f4fd; color: #0d3b66;
      border: 1px solid #bcdcf5; border-radius: 9px;
      padding: 8px 13px; font-size: .87rem; font-weight: 600;
      text-decoration: none; transition: background .15s;
    }
    .asis-link-btn:hover { background: #d3eafc; }
    .asis-chat-input {
      display: flex; border-top: 1px solid #e2e8f0; background: #fff;
    }
    .asis-chat-input input {
      flex: 1; border: none; padding: 13px 14px; font: inherit;
      font-size: .9rem; outline: none;
    }
    .asis-chat-input button {
      border: none; background: none; color: #1d9bf0; font-size: 1.25rem;
      padding: 0 16px; cursor: pointer;
    }
    .asis-typing { font-size: .82rem; color: #64748b; padding-left: 4px; }
  `;
  document.head.appendChild(style);

  // ---------- HTML ----------
  const btn = document.createElement("button");
  btn.id = "asis-chat-btn";
  btn.setAttribute("aria-label", "Sohbeti aç");
  btn.textContent = "💬";

  const panel = document.createElement("div");
  panel.id = "asis-chat-panel";
  panel.innerHTML = `
    <div class="asis-chat-header"><span class="dot"></span> Asis Asistan</div>
    <div class="asis-chat-messages" id="asis-messages"></div>
    <form class="asis-chat-input" id="asis-form">
      <input id="asis-input" type="text" placeholder="Yapmak istediğiniz işlemi yazın..."
             autocomplete="off" maxlength="300" />
      <button type="submit" aria-label="Gönder">➤</button>
    </form>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#asis-messages");
  const form = panel.querySelector("#asis-form");
  const input = panel.querySelector("#asis-input");

  // ---------- Yardımcılar ----------
  function addMessage(text, who) {
    const el = document.createElement("div");
    el.className = "asis-msg " + who;
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  function addLinks(links) {
    if (!links.length) return;
    const wrap = document.createElement("div");
    wrap.className = "asis-links";
    links.forEach(({ link, link_text }) => {
      const a = document.createElement("a");
      a.className = "asis-link-btn";
      a.href = link;
      a.textContent = "🔗 " + link_text;
      wrap.appendChild(a);
    });
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function sendMessage(text) {
    addMessage(text, "user");
    const typing = document.createElement("div");
    typing.className = "asis-typing";
    typing.textContent = "Asis Asistan yazıyor...";
    messagesEl.appendChild(typing);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      typing.remove();
      addMessage(data.reply, "bot");

      const links = [];
      if (data.link) links.push({ link: data.link, link_text: data.link_text });
      (data.suggestions || []).forEach((s) => links.push(s));
      addLinks(links);
    } catch (err) {
      typing.remove();
      addMessage(
        "Şu anda sunucuya ulaşılamıyor. Lütfen daha sonra tekrar deneyin.",
        "bot"
      );
    }
  }

  // ---------- Olaylar ----------
  let greeted = false;
  btn.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) {
      input.focus();
      if (!greeted) {
        greeted = true;
        addMessage(
          "Merhaba! 👋 Ben Asis Asistan. Yapmak istediğiniz işlemi yazın, " +
            "sizi doğru sayfaya yönlendireyim.\n\n" +
            'Örnek: "Bayilerin dolum hakedişini görmek istiyorum"',
          "bot"
        );
      }
    }
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendMessage(text);
  });
})();
