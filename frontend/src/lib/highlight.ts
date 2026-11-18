/**
 * Split `text` into fragments with match markers for the given query terms.
 * Returns an array of { text, match } so React can render <mark> safely.
 */
export interface Fragment {
  text: string
  match: boolean
}

export function highlight(text: string, query: string): Fragment[] {
  const terms = query
    .toLowerCase()
    .split(/\s+/)
    .map((t) => t.replace(/[^\w]/g, ""))
    .filter((t) => t.length >= 3)
  if (terms.length === 0) return [{ text, match: false }]

  const pattern = new RegExp(`(${terms.map(escapeRe).join("|")})`, "gi")
  const parts = text.split(pattern)
  return parts.map((p) =>
    p ? { text: p, match: terms.some((t) => t.toLowerCase() === p.toLowerCase()) } : { text: "", match: false }
  ).filter((f) => f.text)
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}
