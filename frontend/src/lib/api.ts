/**
 * Axios client with JWT injection.
 * Automatically attaches `Authorization: Bearer <token>` from localStorage
 * and clears it on 401.
 */
import axios from "axios"

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

export const TOKEN_KEY = "docintel_token"

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

export interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}
