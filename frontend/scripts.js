;(() => {
  const API_BASE_URL = "http://localhost:8001" // Keep as-is; update if needed.
  const state = {
    sessionId: generateSessionId(),
    isOpen: false,
    typingId: null,
    restoreLimit: 20,
  }

  // Elements
  const root = document.getElementById("chatbotRoot")
  const openBtn = document.getElementById("openChatbotBtn")
  const closeBtn = document.getElementById("closeChatbotBtn")
  const suggestions = document.getElementById("chatSuggestions")
  const messagesEl = document.getElementById("chatMessages")
  const input = document.getElementById("messageInput")
  const sendBtn = document.getElementById("sendButton")
  const openChatCta = document.getElementById("openChatCta")
  const exploreBtn = document.getElementById("exploreBtn")

  // Init
  document.addEventListener("DOMContentLoaded", onReady)

  function onReady() {
    attachEvents()
    closeChat()
    restoreHistory()
    autoGrow(input)
  }

  function attachEvents() {
    openBtn?.addEventListener("click", toggleChat)
    closeBtn?.addEventListener("click", closeChat)
    openChatCta?.addEventListener("click", openChat)

    // Keyboard: Enter to send, Shift+Enter for newline, Esc to close
    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        sendMessage()
      } else if (e.key === "Escape") {
        closeChat()
      }
    })

    sendBtn?.addEventListener("click", sendMessage)

    // Suggestions
    suggestions?.addEventListener("click", (e) => {
      const btn = e.target.closest(".chip")
      if (!btn) return
      input.value = btn.dataset.prompt || ""
      input.focus()
    })

    // Example CTA scroll
    exploreBtn?.addEventListener("click", () => {
      const section = document.getElementById("homeSection")
      if (section) section.scrollIntoView({ behavior: "smooth", block: "start" })
    })

    // Persist on unload
    window.addEventListener("beforeunload", persistHistory)
  }

  function toggleChat() {
    state.isOpen ? closeChat() : openChat()
  }
  function openChat() {
    state.isOpen = true
    root?.setAttribute("data-state", "open")
    setTimeout(() => input?.focus(), 120)
  }
  function closeChat() {
    state.isOpen = false
    root?.setAttribute("data-state", "closed")
    openBtn?.focus()
  }

  function generateSessionId() {
    return "session_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9)
  }

  function nowTime() {
    const d = new Date()
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }

  function addMessage({ text, sender }) {
    const wrapper = document.createElement("div")
    wrapper.className = `message ${sender === "user" ? "message--user" : "message--bot"}`

    const meta = document.createElement("div")
    meta.className = "message__meta"
    meta.innerHTML = `<strong>${sender === "user" ? "You" : "INGRES Assistant"}</strong> <time class="message__time">${nowTime()}</time>`

    const content = document.createElement("div")
    content.className = "message__content"
    content.textContent = text

    wrapper.appendChild(meta)
    wrapper.appendChild(content)
    messagesEl.appendChild(wrapper)
    scrollToBottom()

    return wrapper
  }

  function addTyping() {
    const wrapper = document.createElement("div")
    wrapper.className = "message message--bot"
    wrapper.dataset.typing = "true"

    const meta = document.createElement("div")
    meta.className = "message__meta"
    meta.innerHTML = `<strong>INGRES Assistant</strong> <time class="message__time">${nowTime()}</time>`

    const content = document.createElement("div")
    content.className = "message__content typing"
    content.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>'

    wrapper.appendChild(meta)
    wrapper.appendChild(content)
    messagesEl.appendChild(wrapper)
    scrollToBottom()

    state.typingId = wrapper
  }

  function removeTyping() {
    if (state.typingId && state.typingId.parentNode) {
      state.typingId.parentNode.removeChild(state.typingId)
    }
    state.typingId = null
  }

  async function sendMessage() {
    const text = (input?.value || "").trim()
    if (!text) return

    // optimistic UI
    addMessage({ text, sender: "user" })
    input.value = ""
    autoGrow(input)

    sendBtn.disabled = true
    addTyping()

    try {
      const res = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: text,
          session_id: state.sessionId,
          user_id: "web_user",
        }),
      })

      const data = await res.json().catch(() => ({}))
      removeTyping()

      const answer = data?.answer || "Sorry, I could not retrieve an answer right now."
      const msgEl = addMessage({ text: answer, sender: "bot" })

      // Optional sources preview
      if (Array.isArray(data?.sources) && data.sources.length > 0) {
        const sources = document.createElement("div")
        sources.style.marginTop = "8px"
        sources.style.fontSize = ".9rem"
        sources.style.color = "#374151"

        const toggle = document.createElement("button")
        toggle.textContent = "Show sources"
        toggle.className = "btn"
        toggle.style.padding = "6px 10px"
        toggle.style.marginRight = "8px"
        toggle.addEventListener("click", () => {
          list.hidden = !list.hidden
          toggle.textContent = list.hidden ? "Show sources" : "Hide sources"
        })

        const list = document.createElement("div")
        list.hidden = true
        list.style.marginTop = "8px"
        list.innerHTML = data.sources
          .slice(0, 3)
          .map((s) => {
            const label = s?.type || s?.source_type || "Source"
            const rel = s?.relevance_score ? ` (${Math.round(s.relevance_score * 100)}% relevant)` : ""
            return `<div>• ${label}${rel}</div>`
          })
          .join("")

        const copyBtn = document.createElement("button")
        copyBtn.textContent = "Copy answer"
        copyBtn.className = "btn"
        copyBtn.style.padding = "6px 10px"
        copyBtn.addEventListener("click", async () => {
          try {
            await navigator.clipboard.writeText(answer)
            copyBtn.textContent = "Copied!"
            setTimeout(() => (copyBtn.textContent = "Copy answer"), 1200)
          } catch {}
        })

        sources.appendChild(toggle)
        sources.appendChild(copyBtn)
        sources.appendChild(list)
        msgEl.appendChild(sources)
      }
    } catch (err) {
      removeTyping()
      addMessage({ text: "Sorry, I encountered an error. Please try again.", sender: "bot" })
      console.error("[INGRES] Error:", err)
    } finally {
      sendBtn.disabled = false
      persistHistory()
    }
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight
  }

  // Auto-grow textarea height
  function autoGrow(el) {
    if (!el) return
    const resize = () => {
      el.style.height = "auto"
      el.style.height = Math.min(el.scrollHeight, 180) + "px"
    }
    el.addEventListener("input", resize)
    resize()
  }

  // History persistence (simple, local)
  function persistHistory() {
    try {
      const items = Array.from(messagesEl.querySelectorAll(".message"))
        .slice(-state.restoreLimit)
        .map((node) => {
          const sender = node.classList.contains("message--user") ? "user" : "bot"
          const text = node.querySelector(".message__content")?.textContent || ""
          const time = node.querySelector(".message__time")?.textContent || ""
          return { sender, text, time }
        })
      localStorage.setItem("aquamind_history", JSON.stringify(items))
    } catch {}
  }

  function restoreHistory() {
    try {
      const raw = localStorage.getItem("aquamind_history")
      if (!raw) return
      const items = JSON.parse(raw)
      messagesEl.innerHTML = ""

      items.forEach(({ sender, text, time }) => {
        const wrapper = document.createElement("div")
        wrapper.className = `message ${sender === "user" ? "message--user" : "message--bot"}`

        const meta = document.createElement("div")
        meta.className = "message__meta"
        const who = sender === "user" ? "You" : "INGRES Assistant"
        meta.innerHTML = `<strong>${who}</strong> <time class="message__time">${time || nowTime()}</time>`

        const content = document.createElement("div")
        content.className = "message__content"
        content.textContent = text

        wrapper.appendChild(meta)
        wrapper.appendChild(content)
        messagesEl.appendChild(wrapper)
      })
      scrollToBottom()
    } catch {}
  }
})()
