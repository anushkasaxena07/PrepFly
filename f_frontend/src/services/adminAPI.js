import { handleSessionInvalidation } from '../utils/sessionUtils';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export const adminFetch = async (endpoint, options = {}) => {
  const token = localStorage.getItem("admin_access_token");
  const orgId = localStorage.getItem("admin_org_id") || "org_stanford_01";

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (orgId) {
    headers["X-Organization-Id"] = orgId;
  }

  let urlPath = endpoint.startsWith("/api") ? endpoint : `/api${endpoint}`;
  
  const res = await fetch(`${BACKEND_URL}${urlPath}`, {
    ...options,
    headers
  });

  if (res.status === 401) {
    const data = await res.clone().json().catch(() => ({}));
    if (data.code === "SESSION_SUPERSEEDED" || data.error?.includes("logged in from another device")) {
      handleSessionInvalidation(data.error);
    }
  }

  if (res.status === 403) {
    throw new Error("403 Forbidden: You do not have permission to access another organization's data");
  }

  return res;
};

export const adminLogin = async (email, password) => {
  const res = await adminFetch("/admin/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  if (res.ok) return await res.json();
  const data = await res.json();
  throw new Error(data.error || "Login failed");
};

export const getAdminDashboardStats = async () => {
  const res = await adminFetch("/admin/dashboard");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch dashboard stats");
};

export const getAdminStudents = async (params = {}) => {
  const query = new URLSearchParams(params).toString();
  const res = await adminFetch(`/admin/students?${query}`);
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch students");
};

export const createAdminStudent = async (studentData) => {
  const res = await adminFetch("/admin/student", {
    method: "POST",
    body: JSON.stringify(studentData)
  });
  if (res.ok) return await res.json();
  const data = await res.json();
  throw new Error(data.error || "Failed to create student");
};

export const updateAdminStudent = async (studentId, studentData) => {
  const res = await adminFetch(`/admin/student/${studentId}`, {
    method: "PUT",
    body: JSON.stringify(studentData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update student");
};

export const deleteAdminStudent = async (studentId) => {
  const res = await adminFetch(`/admin/student/${studentId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete student");
};

export const importAdminStudents = async (fileData) => {
  const res = await adminFetch("/admin/students/import", {
    method: "POST",
    body: JSON.stringify(fileData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to import students");
};

export const getAdminInterviews = async () => {
  const res = await adminFetch("/admin/interviews");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch interviews");
};

export const createAdminInterview = async (interviewData) => {
  const res = await adminFetch("/admin/interviews", {
    method: "POST",
    body: JSON.stringify(interviewData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to create interview");
};

export const openAdminInterviewPDF = (interviewId) => {
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
  window.open(`${BACKEND_URL}/admin/interview-pdf/${interviewId}`, "_blank");
};


export const getAdminCodingTests = async () => {
  const res = await adminFetch("/admin/coding");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch coding tests");
};

export const createAdminCodingTest = async (testData) => {
  const res = await adminFetch("/admin/coding", {
    method: "POST",
    body: JSON.stringify(testData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to create coding test");
};

export const generateAdminCodingTestCases = async (payload) => {
  const res = await adminFetch("/admin/coding/generate-test-cases", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to generate AI test cases");
};

export const getAdminCodingLeaderboard = async (testId) => {

  const res = await adminFetch(`/admin/coding-test/${testId}/leaderboard`);
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch coding leaderboard");
};

export const downloadCodingLeaderboardCSV = async (testId) => {
  const token = localStorage.getItem("admin_access_token");
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
  const response = await fetch(`${BACKEND_URL}/admin/coding-test/${testId}/export-csv`, { headers });
  
  if (!response.ok) throw new Error("Failed to export CSV");
  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = downloadUrl;
  a.download = `coding_leaderboard_${testId}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(downloadUrl);
};


export const getAdminQuestionBank = async () => {
  const res = await adminFetch("/admin/question-bank");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch question bank");
};

export const createAdminQuestion = async (qData) => {
  const res = await adminFetch("/admin/question-bank", {
    method: "POST",
    body: JSON.stringify(qData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to add question");
};

export const updateAdminQuestion = async (qId, qData) => {
  const res = await adminFetch(`/admin/question-bank/${qId}`, {
    method: "PUT",
    body: JSON.stringify(qData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update question");
};

export const deleteAdminQuestion = async (qId) => {
  const res = await adminFetch(`/admin/question-bank/${qId}`, {
    method: "DELETE"
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to delete question");
};

export const giveAdminQuestion = async (qId) => {
  const res = await adminFetch(`/admin/question-bank/give/${qId}`, {
    method: "POST"
  });
  if (res.ok) return await res.json();
  const data = await res.json().catch(() => ({}));
  throw new Error(data.error || "Failed to give question to students");
};


export const getAdminReports = async () => {
  const res = await adminFetch("/admin/reports");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch reports");
};

export const generateCustomReport = async (selectedReports, format = "csv") => {
  let newTab = null;
  if (format === "pdf") {
    newTab = window.open("", "_blank");
    if (newTab) {
      newTab.document.write("<div style='font-family:sans-serif;padding:40px;text-align:center;'>⏳ Generating Executive PDF Audit Report...</div>");
    }
  }

  try {
    const res = await adminFetch("/admin/reports/generate", {
      method: "POST",
      body: JSON.stringify({ selected_reports: selectedReports, format })
    });

    if (!res.ok) {
      if (newTab) newTab.close();
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.error || `Failed to generate ${format} report`);
    }

    if (format === "email") {
      return await res.json();
    }

    if (format === "pdf") {
      const htmlText = await res.text();
      if (newTab) {
        newTab.document.open();
        newTab.document.write(htmlText);
        newTab.document.close();
      } else {
        const blob = new Blob([htmlText], { type: "text/html" });
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = `placement_analytics_report_${new Date().toISOString().slice(0, 10)}.html`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
      }
      return;
    }

    const blob = await res.blob();
    const mimeType = format === "excel" ? "application/vnd.ms-excel" : "text/csv";
    const finalBlob = new Blob([blob], { type: mimeType });
    const downloadUrl = window.URL.createObjectURL(finalBlob);
    const ext = format === "excel" ? "xlsx" : "csv";

    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = `placement_analytics_report_${new Date().toISOString().slice(0, 10)}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(downloadUrl), 1000);
  } catch (err) {
    if (newTab) newTab.close();
    throw err;
  }
};

export const openStudentDossierPDF = (studentId) => {
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
  window.open(`${BACKEND_URL}/admin/reports/student/${studentId}/pdf`, "_blank");
};


export const getAdminAnalytics = async () => {
  const res = await adminFetch("/admin/analytics");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch analytics");
};

export const getAdminAnnouncements = async () => {
  const res = await adminFetch("/admin/announcements");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch announcements");
};

export const createAdminAnnouncement = async (annData) => {
  const res = await adminFetch("/admin/announcements", {
    method: "POST",
    body: JSON.stringify(annData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to create announcement");
};

export const getAdminOrganization = async () => {
  const res = await adminFetch("/admin/organization");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch organization profile");
};

export const updateAdminOrganization = async (orgData) => {
  const res = await adminFetch("/admin/organization", {
    method: "PUT",
    body: JSON.stringify(orgData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to update organization profile");
};

export const getAdminSubscription = async () => {
  const res = await adminFetch("/admin/subscription");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch subscription");
};

export const getAdminSettings = async () => {
  const res = await adminFetch("/admin/settings");
  if (res.ok) return await res.json();
  throw new Error("Failed to fetch settings");
};

export const saveAdminSettings = async (settingsData) => {
  const res = await adminFetch("/admin/settings", {
    method: "POST",
    body: JSON.stringify(settingsData)
  });
  if (res.ok) return await res.json();
  throw new Error("Failed to save settings");
};
