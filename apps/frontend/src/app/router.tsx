import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { LoginPage } from "@/features/auth/LoginPage";
import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/ResetPasswordPage";
import { StudentDashboard } from "@/features/dashboard/StudentDashboard";
import { FacultyDashboard } from "@/features/dashboard/FacultyDashboard";
import { AdminDashboard } from "@/features/dashboard/AdminDashboard";
import { SessionsPage } from "@/features/sessions/SessionsPage";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { StudentsPage } from "@/features/students/StudentsPage";
import { AnalyticsPage } from "@/features/analytics/AnalyticsPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { ProfilePage } from "@/features/profile/ProfilePage";
import { DailyPlanPage } from "@/features/daily-plan/DailyPlanPage";
import { QrScannerPage } from "@/features/qr-scanner/QrScannerPage";
import { FacultyPage } from "@/features/faculty/FacultyPage";
import { PlaceholderPage } from "@/features/dashboard/PlaceholderPage";
import { useAuth } from "@/store/auth";

function RequireAuth() {
  const isAuthed = useAuth((s) => s.isAuthenticated);
  if (!isAuthed) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function DashboardRouter() {
  const role = useAuth((s) => s.user?.role);
  if (role === "admin") return <AdminDashboard />;
  if (role === "faculty") return <FacultyDashboard />;
  return <StudentDashboard />;
}

function RoleHome() {
  return <Navigate to="/dashboard" replace />;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/forgot-password", element: <ForgotPasswordPage /> },
  { path: "/reset-password", element: <ResetPasswordPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <RoleHome /> },
          { path: "/dashboard", element: <DashboardRouter /> },
          { path: "/sessions", element: <SessionsPage /> },
          { path: "/attendance", element: <AttendancePage /> },
          { path: "/students", element: <StudentsPage /> },
          { path: "/analytics", element: <AnalyticsPage /> },
          { path: "/reports", element: <ReportsPage /> },
          { path: "/settings", element: <SettingsPage /> },
          { path: "/profile", element: <ProfilePage /> },
          { path: "/daily-plan", element: <DailyPlanPage /> },
          { path: "/qr-scanner", element: <QrScannerPage /> },
          { path: "/faculty", element: <FacultyPage /> },
          { path: "/live-session/:id", element: <PlaceholderPage title="Live Session" emoji="🎥" /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
