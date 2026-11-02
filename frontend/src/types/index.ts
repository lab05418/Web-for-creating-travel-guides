// 类型定义

export interface CityStay {
  city: string
  days: number
}

export interface Location {
  longitude: number
  latitude: number
}

export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  image_url?: string
  photos?: string[]
  ticket_price?: number
  reservation_required?: boolean
  reservation_tips?: string
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  address?: string
  location?: Location
  description?: string
  estimated_cost?: number
}

export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string
  rating: string
  distance: string
  type: string
  estimated_cost?: number
}

export type IntercitySeatType =
  | '二等座'
  | '一等座'
  | '特等座'
  | '商务座'
  | '无座'
  | '硬座'
  | '软座'
  | '硬卧'
  | '软卧'
  | '高级软卧'
  | '经济舱'
  | '超级经济舱'
  | '公务舱'
  | '头等舱'

export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total_inter_city_transport?: number
  total: number
  /** null/undefined 表示旧计划，按旧版“含城际”兼容 */
  include_inter_city_transport_in_budget?: boolean | null
  budget_limit?: number | null
  intercity_transport_mode?: string | null
  intercity_seat_type?: string | null
  intercity_distance_km?: number | null
  intercity_ticket_total?: number | null
  intercity_pricing_basis?: '12306_distance_rule' | 'llm_estimate' | 'none' | string | null
}

export interface DayPlan {
  date: string
  day_index: number
  city?: string
  is_transfer_day?: boolean
  transfer_info?: string
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

export interface WeatherInfo {
  date: string
  city?: string
  day_weather: string
  night_weather: string
  day_temp: number
  night_temp: number
  wind_direction: string
  wind_power: string
}

export interface TripPlan {
  city: string
  cities?: string[]
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}

export interface TripFormData {
  origin?: string
  intercity_transportation?: string
  intercity_seat_type?: IntercitySeatType
  city: string
  cities?: CityStay[]
  start_date: string
  end_date: string
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
  budget_amount?: number | null
  include_inter_city_transport_in_budget?: boolean
  language?: string
  user_id?: string
}

export interface TripPlanResponse {
  success: boolean
  message: string
  plan_id?: string
  data?: TripPlan
}

export interface TripHistoryItem {
  plan_id: string
  task_id: string
  city: string
  start_date: string
  end_date: string
  travel_days: number
  updated_at: string
  overall_suggestions?: string
}

export type TripTaskStatus = 'processing' | 'completed' | 'failed'

export type TripTaskStage =
  | 'submitted'
  | 'initializing'
  | 'attraction_search'
  | 'weather_search'
  | 'hotel_search'
  | 'planning'
  | 'completed'
  | 'failed'

export interface TripTaskEvent {
  task_id: string
  plan_id: string
  status: TripTaskStatus
  stage: TripTaskStage
  progress: number
  message: string
  error?: string
  result?: TripPlanResponse
}

export interface XhsSessionStatus {
  configured?: boolean
  status?: 'active' | 'degraded' | 'expired' | 'needs_login' | 'disabled' | string
  account_label?: string
  last_ok_at?: string | null
  fail_count?: number
  note?: string
}

export interface BackendRuntimeSettings {
  vite_amap_web_key: string
  vite_amap_web_js_key: string
  vite_amap_security_js_code: string
  xhs_cookie: string
  xhs_session?: XhsSessionStatus
  openai_api_key: string
  openai_base_url: string
  openai_model: string
}

export interface RuntimeSettings {
  api_base_url: string
  vite_amap_web_key: string
  vite_amap_web_js_key: string
  vite_amap_security_js_code: string
  xhs_cookie: string
  xhs_session?: XhsSessionStatus
  openai_api_key: string
  openai_base_url: string
  openai_model: string
}

