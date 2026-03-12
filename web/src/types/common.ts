export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface ErrorResponse {
  detail: string
}

export interface MessageResponse {
  message: string
}

export interface CountResponse {
  count: number
}
