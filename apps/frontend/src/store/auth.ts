import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Role = "admin" | "faculty" | "student";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  phone?: string;
  institution_id?: string;
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  setUser: (u: AuthUser | null) => void;
  logout: () => void;
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    { name: "smartattend_auth" }
  )
);
