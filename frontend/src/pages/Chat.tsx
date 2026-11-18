import { useEffect, useRef, useState } from "react"
import { Plus, Send, Loader2, MessageSquare, FileText, Sparkles } from "lucide-react"
import { api } from "../lib/api"
import type { ChatResponse, Citation, Conversation } from "../lib/types"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  citations: Citation[]
  created_at: string
}

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState("")
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get<Conversation[]>("/chat/conversations")
      .then((r) => setConversations(r.data))
      .catch(console.error)
      .finally(() => setInitialLoading(false))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function loadConversation(id: string) {
    setActiveId(id); setError("")
    try {
      const res = await api.get<{ messages: Message[] }>(`/chat/conversations/${id}`)
      setMessages(res.data.messages)
    } catch (e) { console.error(e) }
  }

  function startNew() {
    setActiveId(null); setMessages([]); setError("")
  }

  async function send(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || loading) return
    const q = input.trim()
    setInput("")
    setMessages((prev) => [...prev, {
      id: `temp-${Date.now()}`, role: "user", content: q, citations: [], created_at: new Date().toISOString(),
    }])
    setLoading(true); setError("")

    try {
      const res = await api.post<ChatResponse>("/chat", {
        message: q,
        conversation_id: activeId,
      })
      setActiveId(res.data.conversation_id)
      setMessages((prev) => [...prev, {
        id: `assist-${Date.now()}`, role: "assistant", content: res.data.answer,
        citations: res.data.citations, created_at: new Date().toISOString(),
      }])
      const list = await api.get<Conversation[]>("/chat/conversations")
      setConversations(list.data)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(typeof detail === "string" ? detail : "Failed to get an answer")
    } finally {
      setLoading(false)
    }
  }

  if (initialLoading) {
    return <div className="p-8 text-slate-400">Loading conversations...</div>
  }

  return (
    <div className="flex h-screen">
      <div className="w-72 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="p-3 border-b border-slate-800">
          <button
            onClick={startNew}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition"
          >
            <Plus className="w-4 h-4" />
            New chat
          </button>
        </div>
        <div className="flex-1 overflow-auto p-2">
          {conversations.length === 0 ? (
            <div className="text-center text-slate-500 text-sm py-8">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              No conversations yet
            </div>
          ) : (
            conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => loadConversation(c.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition truncate ${
                  activeId === c.id
                    ? "bg-slate-800 text-slate-100"
                    : "text-slate-400 hover:bg-slate-800/50"
                }`}
              >
                {c.title}
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col bg-slate-950">
        <div className="flex-1 overflow-auto p-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="p-4 rounded-2xl bg-brand-500/10 mb-4">
                <Sparkles className="w-10 h-10 text-brand-500" />
              </div>
              <h2 className="text-2xl font-bold text-slate-100 mb-2">AI Knowledge Assistant</h2>
              <p className="text-slate-400 max-w-md">
                Ask questions about your documents. Answers are grounded in retrieved chunks with page-level citations.
              </p>
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
                    <div className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</div>
                    {m.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <div className="text-xs text-slate-500 mb-2">Sources:</div>
                        <div className="flex flex-wrap gap-2">
                          {m.citations.map((c, i) => (
                            <button
                              key={c.chunk_id}
                              onClick={() => setSelectedCitation(c)}
                              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition"
                            >
                              <span className="font-mono text-slate-500">[{i + 1}]</span>
                              <FileText className="w-3 h-3" />
                              <span className="truncate max-w-[180px]">{c.document_title}</span>
                              <span className="text-slate-500">p.{c.page_number}</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl px-4 py-3 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-brand-500 animate-spin" />
                    <span className="text-sm text-slate-400">Thinking...</span>
                  </div>
                </div>
              )}
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
                placeholder="Ask a question about your documents..."
                disabled={loading}
                className="flex-1 px-4 py-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="px-4 py-3 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white transition"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
          </form>
        </div>
      </div>

      {selectedCitation && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setSelectedCitation(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-100">{selectedCitation.document_title}</h3>
                <p className="text-sm text-slate-500 mt-1">Page {selectedCitation.page_number}</p>
              </div>
              <button onClick={() => setSelectedCitation(null)} className="text-slate-500 hover:text-slate-300">✕</button>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4">
              <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{selectedCitation.excerpt}</p>
            </div>
            <div className="mt-3 text-xs text-slate-500 font-mono break-all">
              chunk: {selectedCitation.chunk_id}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
