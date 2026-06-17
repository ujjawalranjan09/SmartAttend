import { LayoutDashboard, BarChart3, Users, Calendar, CheckSquare, FileText, Settings, UserCircle, CalendarClock, ScanLine, TrendingUp, GraduationCap, type LucideIcon } from "lucide-react";

export interface NavItem {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: number;
}
export interface NavSection {
  section: string;
  items?: NavItem[];
}

export const NAV: Record<string, NavSection[]> = {
  admin: [
    { section: "Overview", items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "analytics", label: "Analytics", icon: BarChart3 },
    ]},
    { section: "Management", items: [
      { id: "students", label: "Students", icon: Users },
      { id: "faculty", label: "Faculty", icon: GraduationCap },
      { id: "sessions", label: "Sessions", icon: Calendar },
      { id: "attendance", label: "Attendance", icon: CheckSquare },
    ]},
    { section: "Reports", items: [
      { id: "reports", label: "Reports", icon: FileText },
    ]},
    { section: "System", items: [
      { id: "settings", label: "Settings", icon: Settings },
    ]},
  ],
  faculty: [
    { section: "Overview", items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    ]},
    { section: "Teaching", items: [
      { id: "sessions", label: "My Sessions", icon: Calendar },
      { id: "attendance", label: "Attendance", icon: CheckSquare },
      { id: "students", label: "My Students", icon: Users },
    ]},
    { section: "Insights", items: [
      { id: "analytics", label: "Analytics", icon: BarChart3 },
      { id: "reports", label: "Reports", icon: FileText },
      { id: "settings", label: "Settings", icon: Settings },
    ]},
  ],
  student: [
    { section: "My space", items: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "profile", label: "My Profile", icon: UserCircle },
      { id: "daily-plan", label: "My Day", icon: CalendarClock },
      { id: "qr-scanner", label: "Scan QR", icon: ScanLine },
      { id: "attendance", label: "My Attendance", icon: CheckSquare },
      { id: "sessions", label: "Schedule", icon: Calendar },
      { id: "analytics", label: "My Progress", icon: TrendingUp },
      { id: "settings", label: "Settings", icon: Settings },
    ]},
  ],
};
