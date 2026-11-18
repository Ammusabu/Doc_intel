import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Plus, Send, Loader2, MessageSquare, FileText, Sparkles, Copy, Check,
  RefreshCw, Trash2, Pencil, ChevronDown, ChevronRight, X,
} from "lucide-react"
import { api, TOKEN_KEY } from "../lib/api"
import type { Citation, Conversation } from "../lib/types"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  citations: Citation[]
  created_at: string
  streaming?: boolean
}

const SUGGESTED_QUESTIONS = [
  "What does the Deep Learning syllabus cover?",
  "What are the citation rules in the Harvard style guide?",
  "How does the Chicago paper describe digital surveillance?",
  "Summarize the main argument of the Chicago paper.",
  "What topics are in Unit III of the syllabus?",
  "What are the key formatting rules for Chicago citations?",
]

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

export default function Chat() {
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState("")
  const [expandedCitation, setExpandedCitation] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [renaming, setRenaming] = useState<string | null>(null)
  const [renameText, setRenameText] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get<Conversation[]>("/chat/conversations")
      .then((r) => setConversations(r.data))
      .catch(console.error)
      .finally(() => setInitialLoading(false))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function loadConversation(id: string) {
    setActiveId(id); setError("")
    try {
      const res = await api.get<{ messages: Message[] }>(`/chat/conversations/${id}`)
      setMessages(res.data.messages.map((m) => ({ ...m, streaming: false })))
    } catch (e) { console.error(e) }
  }

  function startNew() {
    setActiveId(null); setMessages([]); setError("")
  }

  async function sendQuery(q: string) {
    if (!q.trim() || streaming) return
    setInput("")

    const userMsg: Message = {
      id: `u-${Date.now()}`, role: "user", content: q, citations: [], created_at: new Date().toISOString(),
    }
    const assistantId = `a-${Date.now()}`
    const assistantMsg: Message = {
      id: assistantId, role: "assistant", content: "", citations: [], created_at: new Date().toISOString(), streaming: true,
    }
    setMessages((p) => [...p, userMsg, assistantMsg])
    setStreaming(true); setError("")

    try {
      const token = localStorage.getItem(TOKEN_KEY)
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: q, conversation_id: activeId }),
      })

      if (!res.ok || !res.body) {
        const text = await res.text()
        setError(`Failed: ${res.status} ${text.slice(0, 200)}`)
        setStreaming(false)
        setMessages((p) => p.filter((m) => m.id !== assistantId))
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const events = buffer.split("\n\n")
        buffer = events.pop() ?? ""

        for (const ev of events) {
          const lines = ev.split("\n")
          const eventType = lines.find((l) => l.startsWith("event: "))?.slice(7)
          const dataLine = lines.find((l) => l.startsWith("data: "))?.slice(6)
          if (!eventType || !dataLine) continue

          if (eventType === "meta") {
            const meta = JSON.parse(dataLine)
            if (meta.conversation_id) setActiveId(meta.conversation_id)
            setMessages((p) => p.map((m) => m.id === assistantId
              ? { ...m, citations: meta.citations }
              : m))
          } else if (eventType === "token") {
            const { t } = JSON.parse(dataLine)
            setMessages((p) => p.map((m) => m.id === assistantId
              ? { ...m, content: m.content + t }
              : m))
          } else if (eventType === "error") {
            const { error: e } = JSON.parse(dataLine)
            setError(e)
          } else if (eventType === "done") {
            setMessages((p) => p.map((m) => m.id === assistantId ? { ...m, streaming: false } : m))
          }
        }
      }

      const list = await api.get<Conversation[]>("/chat/conversations")
      setConversations(list.data)
    } catch (e: any) {
      setError(e?.message ?? "Request failed")
    } finally {
      setStreaming(false)
    }
  }

  function send(e: React.FormEvent) {
    e.preventDefault()
    sendQuery(input)
  }

  async function regenerate(msgId: string) {
    const idx = messages.findIndex((m) => m.id === msgId)
    if (idx <= 0) return
    const userMsg = messages[idx - 1]
    if (userMsg.role !== "user") return
    setMessages(messages.slice(0, idx))
    await sendQuery(userMsg.content)
  }

  async function copyAnswer(msg: Message) {
    await navigator.clipboard.writeText(msg.content)
    setCopiedId(msg.id)
    setTimeout(() => setCopiedId(null), 1500)
  }

  async function doRename(id: string, title: string) {
    try {
      await api.patch(`/chat/conversations/${id}`, { title })
      setRenaming(null)
      const list = await api.get<Conversation[]>("/chat/conversations")
      setConversations(list.data)
    } catch (e) { console.error(e) }
  }

  async function doDelete(id: string) {
    try {
      await api.delete(`/chat/conversations/${id}`)
      if (activeId === id) startNew()
      const list = await api.get<Conversation[]>("/chat/conversations")
      setConversations(list.data)
    } catch (e) { console.error(e) }
  }

  if (initialLoading) return <div className="p-8 text-slate-400">Loading conversations...</div>

  return (
    <div className="flex h-screen">
      <div className="w-72 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="p-3 border-b border-slate-800">
          <button
            onClick={startNew}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition"
          >
            <Plus className="w-4 h-4" /> New chat
          </button>
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="text-center text-slate-500 text-sm py-8">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              No conversations yet
            </div>
          ) : (
            conversations.map((c) => (
              <div key={c.id} className="group relative">
                {renaming === c.id ? (
                  <div className="px-2 py-1">
                    <input
                      autoFocus
                      value={renameText}
                      onChange={(e) => setRenameText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") doRename(c.id, renameText)
                        if (e.key === "Escape") setRenaming(null)
                      }}
                      onBlur={() => doRename(c.id, renameText)}
                      className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200 focus:outline-none focus:border-brand-500"
                    />
                  </div>
                ) : (
                  <button
                    onClick={() => loadConversation(c.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm transition truncate pr-16 ${
                      activeId === c.id
                        ? "bg-slate-800 text-slate-100"
                        : "text-slate-400 hover:bg-slate-800/50"
                    }`}
                  >
                    {c.title}
                  </button>
                )}
                <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 flex gap-0.5">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setRenaming(c.id)
                      setRenameText(c.title)
                    }}
                    className="p-1 rounded hover:bg-slate-700 text-slate-500 hover:text-slate-200"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm(`Delete "${c.title}"?`)) doDelete(c.id)
                    }}
                    className="p-1 rounded hover:bg-red-500/20 text-slate-500 hover:text-red-400"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-slate-950">
        <div className="flex-1 overflow-auto p-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-2xl mx-auto px-4">
              <div className="p-4 rounded-2xl bg-brand-500/10 mb-4">
                <Sparkles className="w-10 h-10 text-brand-500" />
              </div>
              <h2 className="text-2xl font-bold text-slate-100 mb-2">AI Knowledge Assistant</h2>
              <p className="text-slate-400 mb-6">
                Ask questions about your documents. Every answer is grounded in retrieved
                chunks with page-level citations you can click to verify.
              </p>
              <div className="w-full">
                <div className="text-xs text-slate-500 mb-2 text-left">Try asking:</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendQuery(q)}
                      className="text-left text-sm px-3 py-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    m.role === "user"
                      ? "bg-brand-600 text-white"
                      : "bg-slate-900 border border-slate-800 text-slate-200"
                  }`}>
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">
                      {m.content}
                      {m.streaming && (
                        <span className="inline-block w-1.5 h-4 ml-0.5 align-middle bg-brand-500 animate-pulse" />
                      )}
                    </div>

                    {m.role === "assistant" && m.content && !m.streaming && (
                      <div className="flex items-center gap-1 mt-2 pt-2 border-t border-slate-800">
                        <button
                          onClick={() => copyAnswer(m)}
                          className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-200 transition"
                          title="Copy"
                        >
                          {copiedId === m.id ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                        <button
                          onClick={() => regenerate(m.id)}
                          className="p-1 rounded hover:bg-slate-800 text-slate-500 hover:text-slate-200 transition"
                          title="Regenerate"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}

                    {m.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <div className="text-xs text-slate-500 mb-2">Sources:</div>
                        <div className="space-y-1.5">
                          {m.citations.map((c, i) => {
                            const key = `${m.id}-${c.chunk_id}`
                            const open = expandedCitation === key
                            return (
                              <div key={key} className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/50">
                                <button
                                  onClick={() => setExpandedCitation(open ? null : key)}
                                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-800/50 text-left transition"
                                >
                                  {open ? <ChevronDown className="w-3 h-3 text-slate-500" /> : <ChevronRight className="w-3 h-3 text-slate-500" />}
                                  <FileText className="w-3 h-3 text-brand-500 flex-shrink-0" />
                                  <span className="text-xs text-slate-300 truncate flex-1">{c.document_title}</span>
                                  <span className="text-xs text-slate-500 flex-shrink-0">p.{c.page_number}</span>
                                </button>
                                {open && (
                                  <div className="px-3 pb-3 pt-1 bg-slate-900/50">
                                    <p className="text-xs text-slate-400 leading-relaxed mb-2 italic">
                                      &quot;{c.excerpt}&quot;
                                    </p>
                                    <button
                                      onClick={() => navigate(`/documents/${c.document_id}`)}
                                      className="text-xs text-brand-400 hover:text-brand-300 transition"
                                    >
                                      Open source document →
                                    </button>
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {error && (
                <div className="flex justify-start">
                  <div className="bg-red-950/50 border border-red-900 rounded-2xl px-4 py-3 text-sm text-red-300">
                    {error}
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t border-slate-800 p-4">
          <form onSubmit={send} className="max-w-3xl mx-auto">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={streaming ? "Waiting for response..." : "Ask a question about your documents..."}
                disabled={streaming}
                className="flex-1 px-4 py-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={streaming || !input.trim()}
                className="px-4 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white transition"
              >
                {streaming ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
