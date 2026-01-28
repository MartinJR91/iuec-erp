import React, { useState, useEffect } from "react";
import { Grid, Card, CardContent, Typography, Box, Alert, CircularProgress } from "@mui/material";
import { People, AttachMoney, Warning, School } from "@mui/icons-material";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

import KpiCard from "../KpiCard";

interface DashboardData {
  totalStudents: number;
  monthlyRevenue: number;
  sodAlerts: number;
  attendanceRate: number;
  enrollmentEvolution: Array<{ month: string; inscriptions: number }>;
}

const RecteurDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Simuler un fetch API
    const fetchData = async () => {
      try {
        // TODO: Remplacer par un vrai appel API : await api.get("/api/dashboard/recteur/")
        await new Promise((resolve) => setTimeout(resolve, 500)); // Simuler délai réseau
        
        setData({
          totalStudents: 1200,
          monthlyRevenue: 45000000,
          sodAlerts: 3,
          attendanceRate: 92,
          enrollmentEvolution: [
            { month: "Jan 2025", inscriptions: 1100 },
            { month: "Fév 2025", inscriptions: 1150 },
            { month: "Mar 2025", inscriptions: 1180 },
            { month: "Avr 2025", inscriptions: 1200 },
            { month: "Mai 2025", inscriptions: 1220 },
            { month: "Juin 2025", inscriptions: 1200 },
          ],
        });
        setLoading(false);
      } catch (err) {
        setError("Erreur lors du chargement des données");
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error || "Données non disponibles"}
      </Alert>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("fr-CM", {
      style: "currency",
      currency: "XAF",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Tableau de bord institutionnel
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Étudiants inscrits"
            value={data.totalStudents.toLocaleString()}
            subtitle="Total actif"
            trend="up"
            trendValue="+5% vs mois dernier"
            color="primary"
            icon={<People />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Revenus du mois"
            value={formatCurrency(data.monthlyRevenue)}
            subtitle="Janvier 2026"
            trend="up"
            trendValue="+8% vs décembre"
            color="success"
            icon={<AttachMoney />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Alertes SoD"
            value={data.sodAlerts}
            subtitle="À traiter"
            trend={data.sodAlerts > 0 ? "down" : "neutral"}
            trendValue={data.sodAlerts > 0 ? "Action requise" : "Aucune alerte"}
            color={data.sodAlerts > 0 ? "error" : "success"}
            icon={<Warning />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            title="Taux d'assiduité"
            value={`${data.attendanceRate}%`}
            subtitle="Moyenne globale"
            trend="up"
            trendValue="+2% vs trimestre dernier"
            color="info"
            icon={<School />}
          />
        </Grid>
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Évolution des inscriptions (2025-2026)
          </Typography>
          <Box sx={{ width: "100%", height: 300, mt: 2 }}>
            <ResponsiveContainer>
              <LineChart data={data.enrollmentEvolution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="inscriptions"
                  stroke="#1976d2"
                  strokeWidth={2}
                  name="Inscriptions"
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RecteurDashboard;
