import { getRuntimeApiBaseUrl } from './api'

export type PlaceType = 'hotel' | 'attraction' | 'restaurant' | 'station' | 'custom'

export interface PlaceLocation {
  longitude: number
  latitude: number
}

export interface Place {
  id: string
  plan_id: string
  day_index: number | null
  type: PlaceType
  name: string
  address: string
  location: PlaceLocation
  coord_system: 'GCJ-02'
  source: 'user' | 'amap' | 'ai'
  amap_poi_id: string | null
  price?: number | null
  price_source?: string
  inferred_type?: string
  requested_type?: string
  price_available?: boolean
  price_kind?: string
  itinerary_adjusted?: boolean
  adjustment_message?: string
  note: string
  visit_duration_min: number | null
  order_index: number
  created_at: string
  updated_at: string
  version: number
}

export interface PlaceInput {
  day_index?: number | null
  type: PlaceType
  name: string
  address?: string
  location: PlaceLocation
  source?: 'user' | 'amap' | 'ai'
  amap_poi_id?: string | null
  note?: string
  visit_duration_min?: number | null
  version?: number
}

const apiBase = () => getRuntimeApiBaseUrl()
const url = (path: string) => `${apiBase()}${path}`

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
  let response: Response
  try {
    response = await fetch(url(path), {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
    })
  } catch {
    throw new Error('地点服务连接失败，请确认后端服务已启动')
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
  if (response.status === 204) return undefined as T
  const body = await response.json()
  return (body?.data ?? body) as T
}

export const listPlaces = (planId: string) =>
  request<Place[]>(`/api/plans/${encodeURIComponent(planId)}/places`)

export const createPlace = (planId: string, input: PlaceInput) =>
  request<Place>(`/api/plans/${encodeURIComponent(planId)}/places`, {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const updatePlace = (planId: string, placeId: string, input: Partial<PlaceInput>) =>
  request<Place>(`/api/plans/${encodeURIComponent(planId)}/places/${encodeURIComponent(placeId)}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })

export const deletePlace = (planId: string, placeId: string) =>
  request<void>(`/api/plans/${encodeURIComponent(planId)}/places/${encodeURIComponent(placeId)}`, {
    method: 'DELETE',
  })

export const reorderPlaces = (planId: string, dayIndex: number, ids: string[]) =>
  request<Place[]>(`/api/plans/${encodeURIComponent(planId)}/places/order`, {
    method: 'PUT',
    body: JSON.stringify({ day_index: dayIndex, ids }),
  })

export const setHotel = (planId: string, dayIndex: number, placeId: string) =>
  request<Place>(`/api/plans/${encodeURIComponent(planId)}/days/${dayIndex}/hotel`, {
    method: 'PUT',
    body: JSON.stringify({ place_id: placeId }),
  })
