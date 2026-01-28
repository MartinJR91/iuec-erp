import { useState, useEffect } from "react";
import { UserRole } from "../context/AuthContext";

export interface DashboardData {
  kpis?: {
    studentsCount?: number;
    monthlyRevenue?: string;
    sodAlerts?: number;
    attendanceRate?: number;
  };
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

    // Simuler un fetch API (mock data)
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Simuler un délai réseau
        await new Promise((resolve) => setTimeout(resolve, 500));

        let mockData: DashboardData = {};

        switch (role) {
          case "RECTEUR":
          case "DAF":
          case "SG":
          case "VIEWER_STRATEGIC":
            mockData = {
              kpis: {
                studentsCount: 1200,
                monthlyRevenue: "45 000 000 XAF",
                sodAlerts: 3,
                attendanceRate: 92,
              },
            };
            break;

          case "USER_TEACHER":
          case "ENSEIGNANT":
            mockData = {
              courses: [
                { code: "MATH101", name: "Mathématiques Fondamentales", studentCount: 45, nextClass: "2026-01-30 08:00" },
                { code: "PHYS201", name: "Physique Quantique", studentCount: 32, nextClass: "2026-01-29 14:00" },
                { code: "INFO301", name: "Algorithmes Avancés", studentCount: 28, nextClass: "2026-01-31 10:00" },
                { code: "STAT202", name: "Statistiques", studentCount: 38, nextClass: "2026-02-01 09:00" },
              ],
              stats: {
                gradedStudents: 85,
                totalStudents: 120,
              },
            };
            break;

          case "USER_STUDENT":
            mockData = {
              grades: [
                { ueCode: "UE_MATH", average: 14.5, status: "Validée" },
                { ueCode: "UE_PHYS", average: 11.2, status: "Validée" },
                { ueCode: "UE_INFO", average: 8.5, status: "Ajourné" },
                { ueCode: "UE_STAT", average: 12.8, status: "Validée" },
              ],
              balance: 150000,
            };
            break;

          case "OPERATOR_FINANCE":
            mockData = {
              unpaidInvoices: [
                { student: "KONE Salif", amount: 250000, dueDate: "2026-02-15" },
                { student: "DIAKITE Amadou", amount: 180000, dueDate: "2026-02-10" },
                { student: "TRAORE Fatou", amount: 320000, dueDate: "2026-02-20" },
                { student: "SANGARE Mariam", amount: 150000, dueDate: "2026-02-05" },
                { student: "COULIBALY Ibrahim", amount: 280000, dueDate: "2026-02-12" },
              ],
              totalPending: 1180000,
            };
            break;

          default:
            mockData = {};
        }

        setData(mockData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur lors du chargement des données");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [role]);

  return { data, loading, error };
};
