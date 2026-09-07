/**
 * API client for the Passive Thermal Shelter Platform backend.
 * All API calls proxy through Vite dev server to FastAPI on port 8000.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

export default api

// ── Types ────────────────────────────────────────────────────────────────────

export interface Location {
  id: string
  name: string
  display_name?: string
  latitude: number
  longitude: number
  elevation?: number
  timezone?: string
  country?: string
  region?: string
  created_at?: string
}

export interface WeatherDataPoint {
  timestamp: string
  temperature_2m?: number
  relative_humidity_2m?: number
  wind_speed_10m?: number
  wind_direction_10m?: number
  cloud_cover?: number
  precipitation?: number
  shortwave_radiation?: number
  direct_radiation?: number
  diffuse_radiation?: number
  surface_pressure?: number
}

export interface WeatherDataset {
  id: string
  location_id: string
  provider: string
  start_datetime: string
  end_datetime: string
  resolution_hours: number
  data: WeatherDataPoint[]
  fetched_at: string
}

export interface Material {
  id: string
  name: string
  category: string
  description?: string
  thermal_conductivity: number
  density: number
  specific_heat: number
  emissivity: number
  solar_absorptivity: number
  solar_reflectivity: number
  default_thickness?: number
  notes?: string
  source?: string
  is_builtin: boolean
  created_at: string
  updated_at: string
}

export interface Design {
  id: string
  name: string
  description?: string
  design_type: string
  file_path?: string
  file_format?: string
  file_size_bytes?: number
  length: number
  width: number
  height: number
  wall_thickness: number
  roof_thickness: number
  floor_thickness: number
  floor_area?: number
  volume?: number
  window_area: number
  door_area: number
  window_orientation: string
  glazing_u_value: number
  orientation: string
  notes?: string
  is_builtin: boolean
  created_at: string
  updated_at: string
}

export interface SimulationJob {
  id: string
  sim_id: string
  config_id: string
  design_id: string
  material_id: string
  orientation: string
  status: string
  progress_message?: string
  error_message?: string
  ansys_job_dir?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface SimulationResult {
  id: string
  job_id: string
  timestamps?: string[]
  temp_internal?: number[]
  temp_ambient?: number[]
  solar_radiation?: number[]
  solar_heat_gain?: number[]
  total_heat_flow?: number[]
  min_internal_temp?: number
  max_internal_temp?: number
  avg_internal_temp?: number
  nighttime_min_temp?: number
  nighttime_avg_temp?: number
  daytime_max_temp?: number
  comfort_hours?: number
  comfort_percentage?: number
  total_solar_gain_kwh?: number
  total_heat_loss_kwh?: number
  peak_heat_loss_w?: number
  temp_fluctuation_std?: number
  nighttime_retention_score?: number
  node_count?: number
  element_count?: number
  solve_time_seconds?: number
  created_at: string
}

export interface AnsysStatus {
  ansys_detected: boolean
  ansys_version?: string
  ansys_install_path?: string
  mapdl_exe_path?: string
  mapdl_exe_exists: boolean
  pymapdl_version?: string
  pymapdl_available: boolean
  connection_tested: boolean
  connection_successful?: boolean
  connection_error?: string
  student_license: boolean
  node_limit?: number
}

export interface RecommendationResult {
  recommendation_id: string
  session_id: string
  config_id?: string
  config_name?: string
  location_name?: string
  latitude?: number
  longitude?: number
  elevation?: number
  region?: string
  country?: string
  simulation_start?: string
  simulation_end?: string
  recommended_job_id: string
  recommended_design?: string
  recommended_material?: string
  overall_score: number
  explanation: string[]
  weights_used: Record<string, number>
  scores_breakdown: Record<string, number>
  comparison_table: ComparisonRow[]
  total_completed: number
  total_failed: number
  comfort_min_temp?: number
  comfort_max_temp?: number
}

export interface ComparisonRow {
  job_id: string
  sim_id: string
  design_name: string
  material_name: string
  avg_internal_temp?: number
  min_internal_temp?: number
  max_internal_temp?: number
  comfort_percentage?: number
  total_solar_gain_kwh?: number
  total_heat_loss_kwh?: number
  nighttime_retention_score?: number
  score?: number
  is_recommended: boolean
}

// ── API calls ────────────────────────────────────────────────────────────────

export const API = {
  // Location
  searchLocation: (query: string) => api.post<Location>('/locations/search', { query }),
  listLocations: () => api.get<Location[]>('/locations'),

  // Weather
  fetchWeather: (data: {
    location_id: string
    start_date: string
    end_date: string
    force_refresh?: boolean
  }) => api.post<WeatherDataset>('/weather/fetch', data),
  getWeather: (id: string) => api.get<WeatherDataset>(`/weather/${id}`),

  // Materials
  listMaterials: (category?: string) =>
    api.get<Material[]>('/materials', { params: { category } }),
  getMaterial: (id: string) => api.get<Material>(`/materials/${id}`),
  createMaterial: (data: Partial<Material>) =>
    api.post<Material>('/materials', data),
  duplicateMaterial: (id: string) =>
    api.post<Material>(`/materials/${id}/duplicate`),
  deleteMaterial: (id: string) =>
    api.delete(`/materials/${id}`),

  // Designs
  listDesigns: () => api.get<Design[]>('/designs'),
  getDesign: (id: string) => api.get<Design>(`/designs/${id}`),
  createDesign: (data: Partial<Design>) => api.post<Design>('/designs', data),
  uploadDesign: (formData: FormData) =>
    api.post<Design>('/designs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  duplicateDesign: (id: string) => api.post<Design>(`/designs/${id}/duplicate`),
  deleteDesign: (id: string) =>
    api.delete(`/designs/${id}`),

  // Simulations
  configure: (data: object) => api.post<{
    config_id: string
    total_jobs: number
    job_ids: string[]
    combinations: object[]
  }>('/simulations/configure', data),
  launch: (configId: string) => api.post(`/simulations/launch/${configId}`),
  listConfigs: () => api.get<Array<{
    id: string
    name: string
    created_at: string
    location_name?: string
    latitude?: number
    longitude?: number
    elevation?: number
    simulation_start?: string
    simulation_end?: string
    total_jobs: number
    completed_jobs: number
    failed_jobs: number
    comfort_min_temp?: number
    comfort_max_temp?: number
  }>>('/simulations/configs'),
  deleteConfig: (configId: string) => api.delete(`/simulations/configs/${configId}`),
  getLatestConfig: () => api.get<{
    config_id: string
    name: string
    completed_jobs: number
  }>('/simulations/latest-config'),
  listJobs: (configId: string) => api.get<SimulationJob[]>(`/simulations/jobs/${configId}`),
  getJob: (jobId: string) => api.get<SimulationJob>(`/simulations/job/${jobId}`),
  getResult: (jobId: string) => api.get<SimulationResult>(`/simulations/result/${jobId}`),
  recommend: (configId: string) => api.post<RecommendationResult>(`/simulations/recommend/${configId}`),
  cancelJob: (jobId: string) => api.delete(`/simulations/job/${jobId}/cancel`),

  // ANSYS
  ansysStatus: () => api.get<AnsysStatus>('/ansys/status'),
  testConnection: () => api.post<AnsysStatus>('/ansys/test-connection'),
  autoDetectAnsys: () => api.post<AnsysStatus>('/ansys/auto-detect'),
  configureAnsys: (data: { exe_path: string; test_now?: boolean }) =>
    api.post<AnsysStatus>('/ansys/configure', data),

  // Reports
  generateReport: (recommendationId: string) =>
    api.post<{ report_id: string; title: string; file_path: string }>(`/reports/generate/${recommendationId}`),
  downloadReport: (reportId: string) =>
    `/api/v1/reports/download/${reportId}`,

  // System
  systemInfo: () => api.get('/system/info'),
  health: () => api.get('/health'),
}
