import { getRuntimeApiBaseUrl } from './api'

export type AttractionGuideSource = 'curated' | 'ai' | 'fallback'

export interface AttractionGuide {
  name: string
  city: string
  overview: string
  history: string
  fun_facts: string[]
  tips: string[]
  source: AttractionGuideSource
}

export interface AttractionGuideInput {
  name: string
  city?: string
  address?: string
  description?: string
  category?: string
}

export const fetchAttractionGuide = async (
  input: AttractionGuideInput,
  signal?: AbortSignal
): Promise<AttractionGuide> => {
  const response = await fetch(`${getRuntimeApiBaseUrl()}/api/attractions/guide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
    signal,
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      detail = body?.detail || body?.message || detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }

  const body = await response.json()
  return (body?.data ?? body) as AttractionGuide
}
