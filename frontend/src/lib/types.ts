// Shared API types mirroring the FastAPI contract (base path /api).

export type TokenType = 'bearer';

export interface LoginResponse {
  mfa_required: boolean;
  mfa_token?: string;
  access_token?: string;
  token_type: TokenType;
}

export interface MfaVerifyResponse {
  access_token: string;
  token_type: TokenType;
}

export interface MfaEnrollResponse {
  secret: string;
  otpauth_uri: string;
  qr_svg: string | null;
}

export interface MfaEnrollVerifyResponse {
  totp_enabled: boolean;
  backup_codes: string[];
}

export interface MfaDisableResponse {
  totp_enabled: boolean;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  totp_enabled: boolean;
}

export type CourseStatus = 'planned' | 'in_progress' | 'completed' | 'paused';

export interface Course {
  id: string;
  title: string;
  platform?: string | null;
  url?: string | null;
  status: CourseStatus;
  target_date?: string | null; // YYYY-MM-DD
  created_at: string;
  updated_at: string;
}

export interface CourseCreate {
  title: string;
  platform?: string;
  url?: string;
  status: CourseStatus;
  target_date?: string;
}

export type CourseUpdate = Partial<CourseCreate>;

export interface StudySession {
  id: string;
  course_id: string;
  date: string; // YYYY-MM-DD
  minutes: number;
  note?: string | null;
  created_at: string;
}

export interface SessionCreate {
  date: string;
  minutes: number;
  note?: string;
}

export interface CalendarDay {
  date: string; // YYYY-MM-DD
  total_minutes: number;
  session_count: number;
  course_ids: string[];
}

export interface CalendarResponse {
  month: string; // YYYY-MM
  days: CalendarDay[];
}

export interface Stats {
  active_courses: number;
  completed_courses: number;
  total_courses: number;
  total_minutes: number;
  total_hours: number;
  current_streak: number;
  sessions_this_week: number;
}
