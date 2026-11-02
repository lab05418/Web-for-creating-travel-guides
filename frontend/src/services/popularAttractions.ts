import { getRuntimeApiBaseUrl } from './api'

export interface PopularAttraction {
  id: string
  name: string
  city: string
  address: string
  location: { longitude: number; latitude: number }
  type: string
  category: string
  rating?: number | null
  ticket_price?: number | null
  photos: string[]
  image_url: string
  description: string
  visit_duration: number
  source: 'amap'
}

interface PopularResponse {
  city: string
  items: PopularAttraction[]
}

export async function fetchPopularAttractions(
  city: string,
  excludeNames: string[],
  limit = 12,
): Promise<PopularAttraction[]> {
  const params = new URLSearchParams({
    city,
    exclude: excludeNames.filter(Boolean).join(','),
    limit: String(limit),
  })
  let response: Response
  try {
    response = await fetch(`${getRuntimeApiBaseUrl()}/api/attractions/popular?${params.toString()}`)
  } catch {
    throw new Error('热门景点服务连接失败，请确认后端服务已启动')
  }
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
  const data = (body?.data ?? body) as PopularResponse
  return Array.isArray(data?.items) ? data.items : []
}
