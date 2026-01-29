import React from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Grid,
  Typography,
} from "@mui/material";
import {
  Line,
  LineChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import DashboardContent from "../components/DashboardContent";
import { useDashboardData } from "../hooks/useDashboardData";

const Dashboard: React.FC = () => {
  const { activeRole, user } = useAuth();
  const navigate = useNavigate();
  const { data } = useDashboardData(activeRole);
  const prevSodAlerts = React.useRef<number | null>(null);

  const isRecteur = activeRole === "RECTEUR";
  const studentsByFaculty = data?.kpis?.studentsByFaculty ?? [];
  const totalStudentsByFaculty = studentsByFaculty.reduce((sum, item) => sum + item.students, 0);
  const monthlyRevenueRaw = data?.kpis?.monthlyRevenue || "0";
  const monthlyRevenueValue = Number(String(monthlyRevenueRaw).replace(/[^0-9]/g, "")) || 0;
  const chartData = studentsByFaculty.map((item) => {
    const ratio = totalStudentsByFaculty ? item.students / totalStudentsByFaculty : 0;
    const payments = Math.round(monthlyRevenueValue * ratio);
    return {
      faculty: item.facultyCode,
      inscriptions: item.students,
      paiements: payments,
    };
  });

  // Rediriger vers login si non connecté
  React.useEffect(() => {
    if (!user || !activeRole) {
      navigate("/login");
    }
  }, [user, activeRole, navigate]);

  React.useEffect(() => {
    if (!isRecteur) {
      return;
    }
    const sodAlerts = data?.kpis?.sodAlerts ?? 0;
    if (prevSodAlerts.current !== null && sodAlerts > prevSodAlerts.current) {
      toast.success("Nouvelle alerte SoD détectée.", { icon: "⚠️" });
    }
    prevSodAlerts.current = sodAlerts;
  }, [data?.kpis?.sodAlerts, isRecteur]);

  if (!user || !activeRole) {
    return null;
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <DashboardContent />
      {isRecteur && (
        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
            <Typography variant="h5">Reporting stratégique</Typography>
            <Button variant="outlined" onClick={() => alert("Export PDF/CSV à venir")}>
              Reporting global
            </Button>
          </Box>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    Étudiants par faculté
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  {studentsByFaculty.length === 0 ? (
                    <Typography variant="body2">Aucune donnée disponible.</Typography>
                  ) : (
                    studentsByFaculty.map((item) => (
                      <Box key={item.facultyCode} sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}>
                        <Typography variant="body2">{item.facultyCode}</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {item.students}
                        </Typography>
                      </Box>
                    ))
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    Budget OHADA du mois
                  </Typography>
                  <Typography variant="h4" sx={{ mt: 2 }}>
                    {monthlyRevenueRaw}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Agrégé des factures payées
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">
                    Alertes conflits SoD
                  </Typography>
                  <Typography variant="h4" sx={{ mt: 2 }}>
                    {data?.kpis?.sodAlerts ?? 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    30 derniers jours
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle1" sx={{ mb: 2 }}>
                    Alertes actives
                  </Typography>
                  {data?.kpis?.sodAlerts ? (
                    <Alert severity="warning">
                      {data.kpis.sodAlerts} alerte(s) SoD en attente de traitement.
                    </Alert>
                  ) : (
                    <Alert severity="success">Aucune alerte SoD active.</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="subtitle1" sx={{ mb: 2 }}>
                    Inscriptions vs Paiements par faculté
                  </Typography>
                  <Box sx={{ width: "100%", height: 320 }}>
                    <ResponsiveContainer>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="faculty" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="inscriptions" stroke="#1976d2" strokeWidth={2} />
                        <Line type="monotone" dataKey="paiements" stroke="#2e7d32" strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}
    </Container>
  );
};

export default Dashboard;
