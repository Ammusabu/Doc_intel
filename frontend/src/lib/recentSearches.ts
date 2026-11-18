const KEY = "docintel_recent_searches"
const MAX = 8

export function getRecentSearches(): string[] {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function addRecentSearch(q: string) {
  const trimmed = q.trim()
  if (!trimmed) return
  const list = getRecentSearches().filter((x) => x !== trimmed)
  list.unshift(trimmed)
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, MAX)))
}

export function clearRecentSearches() {
  localStorage.removeItem(KEY)
}
