import React, { useState, useEffect } from "react";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Chip,
} from "@mui/material";
import { School, Payment, CheckCircle, Cancel } from "@mui/icons-material";

import KpiCard from "../KpiCard";

interface Grade {
  ueCode: string;
  ueName: string;
  average: number;
  status: "validated" | "failed";
}

interface DashboardData {
  recentGrades: Grade[];
  balanceDue: number;
}

const StudentDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // TODO: Remplacer par un vrai appel API : await api.get("/api/dashboard/student/")
        await new Promise((resolve) => setTimeout(resolve, 500));
        
        setData({
          recentGrades: [
            { ueCode: "UE101", ueName: "Mathématiques", average: 14.5, status: "validated" },
            { ueCode: "UE102", ueName: "Physique", average: 16.2, status: "validated" },
            { ueCode: "UE103", ueName: "Informatique", average: 8.5, status: "failed" },
            { ueCode: "UE104", ueName: "Anglais", average: 12.0, status: "validated" },
          ],
          balanceDue: 150000,
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

  const validatedCount = data.recentGrades.filter((g) => g.status === "validated").length;
  const failedCount = data.recentGrades.filter((g) => g.status === "failed").length;

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Mon tableau de bord étudiant
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="UE validées"
            value={validatedCount}
            subtitle={`sur ${data.recentGrades.length} UE`}
            trend="up"
            trendValue={`${Math.round((validatedCount / data.recentGrades.length) * 100)}%`}
            color="success"
            icon={<CheckCircle />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="UE à repasser"
            value={failedCount}
            subtitle="Session de rattrapage"
            trend={failedCount > 0 ? "down" : "neutral"}
            trendValue={failedCount > 0 ? "Action requise" : "Aucune"}
            color={failedCount > 0 ? "error" : "success"}
            icon={<Cancel />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card
            sx={{
              height: "100%",
              bgcolor: data.balanceDue > 0 ? "error.light" : "success.light",
              color: data.balanceDue > 0 ? "error.contrastText" : "success.contrastText",
            }}
          >
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                <Typography variant="body2" gutterBottom>
                  Solde à payer
                </Typography>
                <Payment />
              </Box>
              <Typography variant="h4" component="div" sx={{ fontWeight: "bold", mb: 2 }}>
                {formatCurrency(data.balanceDue)}
              </Typography>
              {data.balanceDue > 0 && (
                <Button
                  variant="contained"
                  color="error"
                  fullWidth
                  onClick={() => alert("Redirection vers paiement en ligne (à implémenter)")}
                >
                  Payer en ligne
                </Button>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Mes notes récentes
          </Typography>
          <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Code UE</strong></TableCell>
                  <TableCell><strong>Nom UE</strong></TableCell>
                  <TableCell align="right"><strong>Moyenne</strong></TableCell>
                  <TableCell align="center"><strong>Statut</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.recentGrades.map((grade) => (
                  <TableRow key={grade.ueCode} hover>
                    <TableCell>
                      <Chip label={grade.ueCode} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell>{grade.ueName}</TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body1"
                        sx={{
                          fontWeight: "bold",
                          color: grade.average >= 10 ? "success.main" : "error.main",
                        }}
                      >
                        {grade.average.toFixed(1)}/20
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={grade.status === "validated" ? "Validée" : "Ajourné"}
                        color={grade.status === "validated" ? "success" : "error"}
                        size="small"
                        icon={grade.status === "validated" ? <CheckCircle /> : <Cancel />}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default StudentDashboard;
