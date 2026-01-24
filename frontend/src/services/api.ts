import axios from "axios";

const api = axios.create({
  baseURL: "https://iuec-erp.onrender.com",
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

export default api;
