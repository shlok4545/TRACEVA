import type { User } from '../types/auth';

const API_BASE_URL = (import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (options.body !== undefined && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Request failed');
  }

  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export type NotificationPayload = {
  id: number;
  notification_type: string;
  severity: string;
  title: string;
  message: string;
  related_passport_id?: number | null;
  related_pickup_id?: number | null;
  related_incident_id?: number | null;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
  user_id?: number | null;
};

export type Incident = {
  id: number;
  incident_number: string;
  facility_id: number;
  facility_name: string | null;
  passport_id: number | null;
  passport_number: string | null;
  pickup_request_id: number | null;
  reported_by_user_id: number;
  reported_by_name: string | null;
  assigned_to_user_id: number | null;
  assigned_to_name: string | null;
  incident_type: string;
  severity: string;
  title: string;
  description: string | null;
  status: string;
  detected_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
};

export type IncidentListResponse = {
  items: Incident[];
  page: number;
  limit: number;
  total: number;
};

export type WasteCategory = {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  segregation_group?: string | null;
  risk_level?: string | null;
  default_disposal_method?: string | null;
  handling_guidance?: string | null;
  warning_message?: string | null;
};

export type WastePassportItem = {
  id?: number;
  item_name: string;
  item_description?: string | null;
  source_department?: string | null;
  contamination_level?: string | null;
  condition?: string | null;
  quantity: number;
  weight_kg?: number | null;
  category?: string | null;
  classification_guidance?: string | null;
  classification_warning?: string | null;
  risk_score?: number | null;
  risk_priority?: string | null;
};

export type WastePassport = {
  id: number;
  facility_id: number;
  facility_name?: string | null;
  ward_id?: number | null;
  ward_name?: string | null;
  passport_number: string;
  generated_by_user_id?: number | null;
  status: string;
  risk_priority?: string | null;
  total_quantity?: number | null;
  total_weight_kg?: number | null;
  qr_token?: string | null;
  qr_generated_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  items: WastePassportItem[];
};

export type DashboardSummaryResponse = {
  passport_summary: {
    total: number;
    active: number;
    completed: number;
    total_weight_kg: number;
  };
  risk_summary: {
    low: number;
    medium: number;
    high: number;
    critical: number;
    distribution: Record<string, number>;
  };
  pickup_summary: {
    total_requests: number;
    completed: number;
    pending: number;
    overdue: number;
    average_waiting_time_minutes: number;
    average_response_time_minutes: number;
    priority_distribution: Record<string, number>;
  };
  treatment_summary: {
    received_count: number;
    treatment_pending: number;
    treatment_completed: number;
    verification_pending: number;
    verified: number;
    rejected: number;
    average_treatment_completion_hours: number;
  };
  incident_summary: {
    total: number;
    open: number;
    resolved: number;
  };
  alerts: Array<{ key: string; severity: string; title: string; message: string; entity: string; entity_id: number | null }>;
  recent_activity: Array<{ event_type: string; timestamp: string; entity: string; actor: string; message: string; severity: string }>;
};

export type TraceabilityReport = {
  stages: Record<string, number>;
  completion_rate: number;
  total_passports: number;
};

export type FacilityReportItem = {
  facility_id: number;
  facility_name: string;
  passport_volume: number;
  waste_weight_kg: number;
  incident_count: number;
  traceability_completion_rate: number;
};

export type RiskReport = {
  low: number;
  medium: number;
  high: number;
  critical: number;
  distribution: Record<string, number>;
  trend: Array<{ date: string; value: number }>;
};

export type PickupReport = {
  total_requests: number;
  completed: number;
  pending: number;
  overdue: number;
  average_waiting_time_minutes: number;
  average_response_time_minutes: number;
  priority_distribution: Record<string, number>;
};

export type TreatmentReport = {
  received_count: number;
  treatment_pending: number;
  treatment_completed: number;
  verification_pending: number;
  verified: number;
  rejected: number;
  average_treatment_completion_hours: number;
};

export type FacilityReport = FacilityReportItem[];

export type ReceivingQueueItem = {
  passport_id: number;
  passport_number: string;
  status: string;
  risk_priority: string | null;
  facility_id: number;
  facility_name: string | null;
  ward_id: number | null;
  ward_name: string | null;
  transport_status: string | null;
  treatment_status: string | null;
  received_at: string | null;
  seal_condition: string | null;
  waste_category: string | null;
  total_weight_kg: number | null;
};

export type ReceivingDetail = ReceivingQueueItem & {
  items: Array<{
    id: number;
    item_name: string;
    item_description: string | null;
    source_department: string | null;
    contamination_level: string | null;
    condition: string | null;
    quantity: number;
    weight_kg: number | null;
    category: string | null;
    segregation_group: string | null;
    classification_confidence: number | null;
    requires_human_confirmation: boolean;
    classification_guidance: string | null;
    classification_warning: string | null;
    risk_score: number | null;
    risk_priority: string | null;
  }>;
  events: Array<{
    id: number;
    event_type: string;
    details: string | null;
    actor_name: string | null;
    created_at: string;
  }>;
};

export type TreatmentRecord = {
  id: number;
  passport_id: number;
  treatment_facility_id: number;
  received_by_user_id: number;
  received_at: string;
  received_weight_kg: number;
  seal_condition: string;
  intake_status: string;
  treatment_method: string;
  treatment_started_at: string | null;
  treatment_completed_at: string | null;
  verification_status: string;
  certificate_number: string | null;
  verification_notes: string | null;
  created_at: string;
  updated_at: string;
  evidence: Array<{
    id: number;
    file_name: string;
    file_type: string;
    uploaded_at: string;
    description: string;
  }>;
};

export const api = {
  getHealth: () => request<{ status: string; service: string }>('/api/health'),
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  getCurrentUser: (token: string) =>
    request<User>('/api/auth/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  logout: (token: string) =>
    request<{ message: string }>('/api/auth/logout', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getUsers: (token: string) =>
    request<User[]>('/api/users', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getFacilities: (token: string) =>
    request<Array<{ id: number; name: string; type: string; address?: string | null; status: string; ward_count?: number }>>('/api/facilities', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getWards: (token: string) =>
    request<{ count: number; wards: Array<{ id: number; name: string; facility_id: number; facility_name?: string | null; department_type?: string | null }> }>('/api/wards', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getWasteCategories: (token: string) =>
    request<WasteCategory[]>('/api/waste/waste-categories', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getDashboardSummary: (token: string) =>
    request<DashboardSummaryResponse>('/api/dashboard/summary', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getPassport: (token: string, passportId: number) =>
    request<WastePassport>(`/api/passports/${passportId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getPassports: (token: string) =>
    request<WastePassport[]>('/api/passports', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  createPassport: (token: string, payload: { facility_id?: number; ward_id?: number | null; items: WastePassportItem[] }) =>
    request<WastePassport>('/api/passports', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  classifyPassport: (token: string, passportId: number) =>
    request<{ id: number; passport_number: string; status: string; risk_priority: string; classified_items: Array<{ id: number; item_name: string; category: string; risk_priority: string; guidance?: string | null }> }> (`/api/passports/` + passportId + `/classify`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  generateQr: (token: string, passportId: number) =>
    request<{ id: number; passport_number: string; qr_data_url: string; qr_token: string; status: string }>('/api/passports/' + passportId + '/generate-qr', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  createPickupRequest: (token: string, passportId: number, payload?: { notes?: string }) =>
    request<{ id: number; passport_id: number; passport_number: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; priority: string; risk_score_snapshot: number; status: string; requested_at: string; due_at: string; requested_by_user_id: number; assigned_collector_id: number | null; created_at: string }>(`/api/pickups/requests`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ passport_id: passportId, ...payload }),
    }),
  getPickupRequests: (token: string, params?: { status?: string; priority?: string; facility?: number; collector?: number; date?: string; search?: string }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
return request<Array<{ id: number; passport_id: number; passport_number: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; requested_by_user_id: number; assigned_collector_id: number | null; assigned_collector_name: string | null; priority: string; risk_score_snapshot: number | null; status: string; requested_at: string; assigned_at: string | null; accepted_at: string | null; pickup_started_at: string | null; completed_at: string | null; due_at: string | null; notes: string | null; waiting_minutes: number; waiting_hours: number; is_overdue: boolean; created_at: string; updated_at: string }>> (`/api/pickups/requests?${searchParams.toString()}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
  getPickupQueue: (token: string) =>
    request<Array<{ id: number; passport_number: string; ward: string | null; category: string; risk_score: number | null; priority: string; waiting_minutes: number; waiting_hours: number; due_time: string | null; status: string; assigned_collector: string | null; urgency_explanation: string; is_overdue: boolean }>> (`/api/pickups/queue`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  assignCollector: (token: string, pickupId: number, collectorId: number) =>
    request<{ id: number; passport_id: number; passport_number: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; requested_by_user_id: number; assigned_collector_id: number | null; assigned_collector_name: string | null; priority: string; risk_score_snapshot: number | null; status: string; requested_at: string; assigned_at: string | null; accepted_at: string | null; pickup_started_at: string | null; completed_at: string | null; due_at: string | null; notes: string | null; waiting_minutes: number; waiting_hours: number; is_overdue: boolean; created_at: string; updated_at: string }>(`/api/pickups/${pickupId}/assign`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ collector_id: collectorId }),
    }),
  getCollectors: (token: string) =>
    request<Array<{ id: number; user_id: number; facility_id: number; employee_code: string; vehicle_number: string | null; phone: string | null; availability_status: string; active: boolean; user: { id: number; name: string; email: string } }>> (`/api/pickups/collectors`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getCollectorAssignments: (token: string) =>
    request<Array<{ id: number; passport_id: number; passport_number: string; facility_name?: string | null; ward_name?: string | null; priority: string; risk_score_snapshot?: number | null; status: string; requested_at?: string | null; created_at?: string | null; waiting_minutes?: number; due_at?: string | null; notes?: string | null }>>('/api/pickups/assignments', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getCollectorAssignment: (token: string, pickupId: number) =>
    request<{ id: number; passport_id: number; passport_number: string; facility_name?: string | null; ward_name?: string | null; priority: string; risk_score_snapshot?: number | null; status: string; requested_at?: string | null; assigned_at?: string | null; accepted_at?: string | null; pickup_started_at?: string | null; completed_at?: string | null; due_at?: string | null; notes?: string | null; assigned_collector_name?: string | null }>(`/api/pickups/assignments/${pickupId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  acceptAssignment: (token: string, pickupId: number) =>
    request<{ id: number; passport_id: number; passport_number: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; requested_by_user_id: number; assigned_collector_id: number | null; assigned_collector_name: string | null; priority: string; risk_score_snapshot: number | null; status: string; requested_at: string; assigned_at: string | null; accepted_at: string | null; pickup_started_at: string | null; completed_at: string | null; due_at: string | null; notes: string | null; waiting_minutes: number; waiting_hours: number; is_overdue: boolean; created_at: string; updated_at: string }>(`/api/pickups/assignments/${pickupId}/accept`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  startAssignment: (token: string, pickupId: number) =>
    request<{ id: number; passport_id: number; passport_number: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; requested_by_user_id: number; assigned_collector_id: number | null; assigned_collector_name: string | null; priority: string; risk_score_snapshot: number | null; status: string; requested_at: string; assigned_at: string | null; accepted_at: string | null; pickup_started_at: string | null; completed_at: string | null; due_at: string | null; notes: string | null; waiting_minutes: number; waiting_hours: number; is_overdue: boolean; created_at: string; updated_at: string }>(`/api/pickups/assignments/${pickupId}/start`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  validateQrToken: (token: string) =>
    request<{ passport_number: string; status: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; risk_priority: string | null; waste_category: string | null; total_weight_kg: number | null; message: string }>('/api/qr/validate', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),
  scanPickupQr: (token: string, pickupId: number, qrToken: string) =>
    request<{ passport_number: string; status: string; verified: boolean }>(`/api/pickups/assignments/${pickupId}/scan`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ token: qrToken }),
    }),
  confirmHandover: (token: string, pickupId: number, payload: { seal_condition: string; notes?: string; checklist: Record<string, boolean>; weight_kg?: number }) =>
    request<{ id: number; passport_number: string; status: string }>(`/api/pickups/assignments/${pickupId}/handover`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  startTransport: (token: string, pickupId: number, payload: { vehicle_number?: string; to_facility_id?: number; seal_condition?: string; notes?: string }) =>
    request<{ id: number; pickup_id: number; passport_id: number; event_type: string; vehicle_number: string; from_facility_id: number; to_facility_id: number | null; departure_time: string; seal_status: string; notes: string | null; created_at: string }>(`/api/transport/start`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...payload, pickup_id: pickupId }),
    }),
  getTransportRecord: (token: string, transportId: number) =>
    request<{ id: number; pickup_id: number; passport_id: number; event_type: string; from_facility_id: number; to_facility_id: number | null; vehicle_number: string; arrival_time: string | null; departure_time: string; seal_status: string; notes: string | null; created_at: string }>(`/api/transport/${transportId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  markTransportArrival: (token: string, transportId: number, payload: { to_facility_id: number; latitude?: number; longitude?: number; notes?: string }) =>
    request<{ id: number; pickup_id: number; passport_id: number; event_type: string; to_facility_id: number; arrival_time: string; vehicle_number: string }>(`/api/transport/${transportId}/arrival`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  getReceivingQueue: (token: string) =>
    request<ReceivingQueueItem[]>('/api/facility/receiving', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getReceivingDetail: (token: string, passportId: number) =>
    request<ReceivingDetail>(`/api/facility/receiving/${passportId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  acceptReceiving: (token: string, passportId: number, payload: { received_weight_kg: number; seal_condition: string | null; notes?: string | null }) =>
    request<{ passport_id: number; treatment_facility_id: number; received_by_user_id: number; received_at: string; received_weight_kg: number; seal_condition: string; intake_status: string; verification_status: string }>(`/api/facility/receiving/${passportId}/accept`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  rejectReceiving: (token: string, passportId: number, payload: { reason: string | null }) =>
    request<{ passport_id: number; status: string; reason: string }>(`/api/facility/receiving/${passportId}/reject`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  getTreatmentRecords: (token: string) =>
    request<TreatmentRecord[]>('/api/treatment/records', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getTreatmentRecord: (token: string, recordId: number) =>
    request<TreatmentRecord>(`/api/treatment/records/${recordId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  createTreatmentRecord: (token: string, payload: { passport_id: number; received_weight_kg: number; seal_condition: string; treatment_method: string }) =>
    request<TreatmentRecord>('/api/treatment/records', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  updateTreatmentRecord: (token: string, recordId: number, payload: { treatment_method?: string | null; received_weight_kg?: number | null; seal_condition?: string | null; treatment_started_at?: string | null; treatment_completed_at?: string | null; verification_status?: string | null }) =>
    request<TreatmentRecord>(`/api/treatment/records/${recordId}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  verifyTreatmentRecord: (token: string, recordId: number, payload: { certificate_number?: string | null; verification_notes?: string | null }) =>
    request<TreatmentRecord>(`/api/treatment/records/${recordId}/verify`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  uploadTreatmentEvidence: (token: string, recordId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<{ id: number; file_name: string; file_type: string; uploaded_at: string }>(`/api/treatment/records/${recordId}/evidence`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });
  },
  getNotifications: (token: string) =>
    request<{ items: NotificationPayload[]; unread_count: number }>('/api/notifications', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  markNotificationRead: (token: string, notificationId: number) =>
    request<{ id: number; status: string }>(`/api/notifications/${notificationId}/read`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  markAllNotificationsRead: (token: string) =>
    request<{ updated: number }>('/api/notifications/mark-all-read', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getIncidents: (token: string, params?: { facility?: number; severity?: string; status?: string; incident_type?: string; start_date?: string; end_date?: string; passport_number?: string; page?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
    return request<IncidentListResponse>(`/api/incidents?${searchParams.toString()}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
  getIncident: (token: string, incidentId: number) =>
    request<Incident>(`/api/incidents/${incidentId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  updateIncident: (token: string, incidentId: number, payload: { severity?: string; status?: string; title?: string; description?: string }) =>
    request<Incident>(`/api/incidents/${incidentId}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  acknowledgeIncident: (token: string, incidentId: number) =>
    request<Incident>(`/api/incidents/${incidentId}/acknowledge`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  assignIncident: (token: string, incidentId: number, assignedToUserId: number) =>
    request<Incident>(`/api/incidents/${incidentId}/assign`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ assigned_to_user_id: assignedToUserId }),
    }),
  resolveIncident: (token: string, incidentId: number, payload: { resolution_notes?: string }) =>
    request<Incident>(`/api/incidents/${incidentId}/resolve`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  closeIncident: (token: string, incidentId: number, payload: { resolution_notes?: string }) =>
    request<Incident>(`/api/incidents/${incidentId}/close`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    }),
  getTraceabilityReport: (token: string) =>
    request<TraceabilityReport>('/api/reports/traceability', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getFacilityReport: (token: string) =>
    request<FacilityReport>('/api/reports/facilities', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
  getRiskReport: (token: string, params?: { range?: string; start_date?: string; end_date?: string }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
    return request<RiskReport>(`/api/reports/risk?${searchParams.toString()}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
  getPickupReport: (token: string, params?: { range?: string; start_date?: string; end_date?: string }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          searchParams.append(key, String(value));
        }
      });
    }
    return request<PickupReport>(`/api/reports/pickups?${searchParams.toString()}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },
  getTreatmentReport: (token: string) =>
    request<TreatmentReport>('/api/reports/treatment', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }),
};
