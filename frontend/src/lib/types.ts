export interface DocumentOut {
  id: string
  owner_id: string
  title: string
  original_filename: string
  mime_type: string
  file_size_bytes: number
  page_count: number
  predicted_category: string | null
  classification_confidence: number | null
  status: "pending" | "processing" | "completed" | "failed"
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface DocumentListOut {
  items: DocumentOut[]
  total: number
  page: number
  page_size: number
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface SearchResult {
  chunk_id: string
  document_id: string
  document_title: string
  page_number: number
  chunk_index: number
  content: string
  dense_score: number | null
  keyword_score: number | null
  rrf_score: number
  rerank_score: number | null
  final_rank: number
}

export interface Citation {
  chunk_id: string
  document_id: string
  document_title: string
  page_number: number
  excerpt: string
}

export interface ChatResponse {
  conversation_id: string
  answer: string
  citations: Citation[]
  no_relevant_docs: boolean
}

export interface Chunk {
  id: string
  chunk_index: number
  page_number: number
  token_count: number
  content: string
  embedding_model: string
  embedding_version: string
  has_embedding: boolean
}

export interface ChunksResponse {
  document_id: string
  total: number
  embedding_model: string | null
  embedding_version: string | null
  chunks: Chunk[]
}

export interface TextResponse {
  document_id: string
  page_count: number
  text_by_page: { page_number: number; text: string }[]
}

export type SortKey = "created_at" | "file_size_bytes" | "classification_confidence"
export type SortDir = "asc" | "desc"
