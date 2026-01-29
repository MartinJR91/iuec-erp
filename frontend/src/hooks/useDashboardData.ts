import { useState, useEffect } from "react";
import axios, { AxiosError } from "axios";
import { UserRole } from "../context/AuthContext";
import api from "../services/api";

export interface DashboardData {
  kpis?: {
    studentsCount?: number;
    monthlyRevenue?: string;
    sodAlerts?: number;
    attendanceRate?: number;
    studentsByFaculty?: Array<{
      facultyCode: string;
      students: number;
    }>;
  };
  graph?: Array<{
    month: string;
    value: number;
  }>;
  courses?: Array<{
    code: string;
    name: string;
    studentCount: number;
    nextClass: string;
  }>;
  grades?: Array<{
    ueCode: string;
    average: number;
    status: "Validée" | "Ajourné";
  }>;
  balance?: number;
  unpaidInvoices?: Array<{
    student: string;
    amount: number;
    dueDate: string;
  }>;
  totalPending?: number;
  stats?: {
    gradedStudents?: number;
    totalStudents?: number;
  };
  message?: string;
}

export const useDashboardData = (role: UserRole | null): { data: DashboardData | null; loading: boolean; error: string | null } => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!role) {
      setLoading(false);
      return;
    }

    // Fetch API réelle
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Le header X-Role-Active est déjà géré par l'interceptor axios
        const response = await api.get<DashboardData>("/api/dashboard/", {
          params: { role },
        });

        setData(response.data);
      } catch (err: unknown) {
        let errorMessage = "Erreur lors du chargement des données";
        if (axios.isAxiosError(err)) {
          const axiosError = err as AxiosError<{ detail?: string }>;
          if (axiosError.response?.status === 401) {
            errorMessage = "Non authentifié. Veuillez vous reconnecter.";
          } else if (axiosError.response?.status === 403) {
            errorMessage = "Accès refusé. Rôle non autorisé.";
          } else if (axiosError.response?.status === 500) {
            errorMessage = "Erreur serveur. Veuillez réessayer plus tard.";
          } else {
            errorMessage = axiosError.response?.data?.detail || "Erreur lors du chargement des données";
          }
        } else {
          errorMessage = err instanceof Error ? err.message : "Erreur lors du chargement des données";
        }
        setError(errorMessage);
        // Toast d'erreur
        toast.error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [role]);

  return { data, loading, error };
};
