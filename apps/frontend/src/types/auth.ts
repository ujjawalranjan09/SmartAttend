export type UserRole = 'student' | 'faculty' | 'hod' | 'admin' | 'parent';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  institution_id: string;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
