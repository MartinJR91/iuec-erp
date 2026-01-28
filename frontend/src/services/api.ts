import axios, { AxiosError } from "axios";

// Utiliser l'URL locale en développement, Render en production
const getBaseURL = (): string => {
  if (process.env.NODE_ENV === "development" || window.location.hostname === "localhost") {
    return "http://localhost:8000";
  }
  return "https://iuec-erp.onrender.com";
};

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const roleActive = localStorage.getItem("role_active");
  if (roleActive) {
    config.headers["X-Role-Active"] = roleActive;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expiré ou invalide
      localStorage.removeItem("token");
      localStorage.removeItem("role_active");
      // Rediriger vers login si on n'y est pas déjà
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
