/**
 * Simple i18n system with English and Hindi translations.
 * Translations stored in a nested object. Key format: "section.key"
 * Example: t('settings.profile') => "Profile"
 */

const translations = {
  en: {
    // Navigation
    nav: {
      dashboard: "Dashboard",
      attendance: "Attendance",
      sessions: "Sessions",
      analytics: "Analytics",
      students: "Students",
      courses: "Courses",
      timetable: "Timetable",
      settings: "Settings",
      notifications: "Notifications",
      alerts: "Alerts",
      institutions: "Institutions",
      departments: "Departments",
      reports: "Reports",
      logout: "Logout",
    },
    // Common
    common: {
      loading: "Loading...",
      error: "Something went wrong",
      retry: "Retry",
      save: "Save",
      cancel: "Cancel",
      delete: "Delete",
      edit: "Edit",
      create: "Create",
      search: "Search",
      noData: "No data available",
      confirm: "Confirm",
      success: "Success",
      back: "Back",
    },
    // Dashboard
    dashboard: {
      title: "My Dashboard",
      welcome: "Welcome back",
      overallAttendance: "Overall Attendance",
      classesAttended: "Classes Attended",
      classesMissed: "Classes Missed",
      atRisk: "At-Risk Students",
      activeSessions: "Active Sessions Now",
      unresolvedAlerts: "Unresolved Alerts",
      onTrack: "On track",
      belowThreshold: "Below 75% threshold",
    },
    // Attendance
    attendance: {
      title: "My Attendance",
      mark: "Mark Attendance",
      overview: "Overview",
      history: "History",
      present: "Present",
      absent: "Absent",
      late: "Late",
      proxySuspected: "Proxy Suspected",
      faceConfidence: "Face Conf.",
      riskScore: "Risk Score",
      showFlaggedOnly: "Show flagged only",
      safe: "Safe",
      shortage: "Shortage",
    },
    // Settings
    settings: {
      title: "Settings",
      profile: "Profile",
      security: "Security",
      notifications: "Notifications",
      appearance: "Appearance",
      faceRecognition: "Face Recognition",
      changePassword: "Change Password",
      enable2FA: "Enable 2FA",
      darkMode: "Dark mode",
      faceEnrolled: "Face enrolled successfully",
      notEnrolled: "Not Enrolled",
      enrollFace: "Enroll Face",
      removeEnrollment: "Remove Enrollment",
      capturePhoto: "Capture Photo",
    },
    // Alerts
    alerts: {
      title: "Alerts",
      resolve: "Resolve",
      unresolved: "Unresolved",
      lowAttendance: "Low Attendance",
      proxySuspected: "Proxy Suspected",
      trendAnomaly: "Trend Anomaly",
      severity: "Severity",
    },
    // Analytics
    analytics: {
      title: "Analytics",
      myProgress: "My Progress",
      weeklyTrend: "Weekly Trend",
      forecast: "Forecast",
      improving: "improving",
      declining: "declining",
      stable: "stable",
    },
    // Auth
    auth: {
      login: "Login",
      logout: "Logout",
      register: "Register",
      email: "Email",
      password: "Password",
      forgotPassword: "Forgot Password?",
      resetPassword: "Reset Password",
      changePassword: "Change Password",
    },
  },

  hi: {
    nav: {
      dashboard: "डैशबोर्ड",
      attendance: "उपस्थिति",
      sessions: "सत्र",
      analytics: "विश्लेषण",
      students: "छात्र",
      courses: "पाठ्यक्रम",
      timetable: "समय-सारणी",
      settings: "सेटिंग्स",
      notifications: "सूचनाएं",
      alerts: "अलर्ट",
      institutions: "संस्थान",
      departments: "विभाग",
      reports: "रिपोर्ट",
      logout: "लॉग आउट",
    },
    common: {
      loading: "लोड हो रहा है...",
      error: "कुछ गलत हो गया",
      retry: "पुनः प्रयास करें",
      save: "सहेजें",
      cancel: "रद्द करें",
      delete: "हटाएं",
      edit: "संपादित करें",
      create: "बनाएं",
      search: "खोजें",
      noData: "कोई डेटा उपलब्ध नहीं",
      confirm: "पुष्टि करें",
      success: "सफल",
      back: "वापस",
    },
    dashboard: {
      title: "मेरा डैशबोर्ड",
      welcome: "आपका स्वागत है",
      overallAttendance: "कुल उपस्थिति",
      classesAttended: "उपस्थित कक्षाएं",
      classesMissed: "अनुपस्थित कक्षाएं",
      atRisk: "जोखिम वाले छात्र",
      activeSessions: "सक्रिय सत्र",
      unresolvedAlerts: "अनसुलझे अलर्ट",
      onTrack: "सही रास्ते पर",
      belowThreshold: "75% सीमा से नीचे",
    },
    attendance: {
      title: "मेरी उपस्थिति",
      mark: "उपस्थिति दर्ज करें",
      overview: "अवलोकन",
      history: "इतिहास",
      present: "उपस्थित",
      absent: "अनुपस्थित",
      late: "विलंब",
      proxySuspected: "प्रॉक्सी संदिग्ध",
      faceConfidence: "चेहरा विश्वास",
      riskScore: "जोखिम स्कोर",
      showFlaggedOnly: "केवल चिह्नित दिखाएं",
      safe: "सुरक्षित",
      shortage: "कमी",
    },
    settings: {
      title: "सेटिंग्स",
      profile: "प्रोफाइल",
      security: "सुरक्षा",
      notifications: "सूचनाएं",
      appearance: "रूप",
      faceRecognition: "चेहरा पहचान",
      changePassword: "पासवर्ड बदलें",
      enable2FA: "2FA सक्षम करें",
      darkMode: "डार्क मोड",
      faceEnrolled: "चेहरा सफलतापूर्वक पंजीकृत",
      notEnrolled: "पंजीकृत नहीं",
      enrollFace: "चेहरा पंजीकृत करें",
      removeEnrollment: "पंजीकरण हटाएं",
      capturePhoto: "फोटो लें",
    },
    alerts: {
      title: "अलर्ट",
      resolve: "हल करें",
      unresolved: "अनसुलझे",
      lowAttendance: "कम उपस्थिति",
      proxySuspected: "प्रॉक्सी संदिग्ध",
      trendAnomaly: "प्रवृत्ति विसंगति",
      severity: "गंभीरता",
    },
    analytics: {
      title: "विश्लेषण",
      myProgress: "मेरी प्रगति",
      weeklyTrend: "साप्ताहिक रुझान",
      forecast: "पूर्वानुमान",
      improving: "सुधार",
      declining: "गिरावट",
      stable: "स्थिर",
    },
    auth: {
      login: "लॉगिन",
      logout: "लॉग आउट",
      register: "पंजीकरण",
      email: "ईमेल",
      password: "पासवर्ड",
      forgotPassword: "पासवर्ड भूल गए?",
      resetPassword: "पासवर्ड रीसेट करें",
      changePassword: "पासवर्ड बदलें",
    },
  },
};

// Get current language from localStorage, default to 'en'
function getLanguage() {
  try {
    return localStorage.getItem("smartattend_lang") || "en";
  } catch {
    return "en";
  }
}

// Set the current language
export function setLanguage(lang) {
  if (!translations[lang]) lang = "en";
  try {
    localStorage.setItem("smartattend_lang", lang);
  } catch {}
  // Dispatch event so the app can re-render
  window.dispatchEvent(new CustomEvent("language-changed", { detail: { lang } }));
}

// Get supported languages
export function getLanguages() {
  return [
    { code: "en", label: "English" },
    { code: "hi", label: "हिन्दी (Hindi)" },
  ];
}

/**
 * Translate a key to the current language.
 * @param {string} key - Dot-separated key (e.g., "nav.dashboard")
 * @param {object} params - Optional interpolation values: t('common.welcome', {name: 'John'})
 * @returns {string} Translated string
 */
export function t(key, params = {}) {
  const lang = getLanguage();
  const keys = key.split(".");
  let value = translations[lang];

  for (const k of keys) {
    if (value && typeof value === "object" && k in value) {
      value = value[k];
    } else {
      // Fall back to English
      value = translations["en"];
      for (const fk of keys) {
        if (value && typeof value === "object" && fk in value) {
          value = value[fk];
        } else {
          return key; // Key not found
        }
      }
      break;
    }
  }

  if (typeof value !== "string") return key;

  // Replace {param} placeholders
  return value.replace(/\{(\w+)\}/g, (_, name) => params[name] ?? `{${name}}`);
}

// Export the current language for use in templates
export function getCurrentLang() {
  return getLanguage();
}