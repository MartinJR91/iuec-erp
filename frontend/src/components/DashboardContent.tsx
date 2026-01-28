import React from "react";
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Divider,
  Alert,
  CircularProgress,
  Chip,
} from "@mui/material";
import {
  People,
  AttachMoney,
  Warning,
  Payment,
  Receipt,
  TrendingUp,
} from "@mui/icons-material";

import { useAuth } from "../context/AuthContext";
import { useDashboardData } from "../hooks/useDashboardData";
import KpiCard from "./KpiCard";

const DashboardContent: React.FC = () => {
  const { activeRole, user } = useAuth();
  const { data, loading, error } = useDashboardData(activeRole);

  if (!user || !activeRole) {
    return (
      <Alert severity="warning">Veuillez vous connecter pour accéder au dashboard.</Alert>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Erreur : {error}</Alert>;
  }

  // RECTEUR / DAF / SG / VIEWER_STRATEGIC
  if (activeRole === "RECTEUR" || activeRole === "DAF" || activeRole === "SG" || activeRole === "VIEWER_STRATEGIC") {
    return (
      <Box>
        <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
          Tableau de bord institutionnel
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Étudiants inscrits"
              value={data?.kpis?.studentsCount?.toLocaleString() || "0"}
              subtitle="Total inscriptions"
              trend="up"
              trendValue="+5% vs mois dernier"
              color="primary"
              icon={<People />}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Revenus du mois"
              value={data?.kpis?.monthlyRevenue || "0 XAF"}
              subtitle="Janvier 2026"
              trend="up"
              trendValue="+12% vs décembre"
              color="success"
              icon={<AttachMoney />}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Alertes SoD"
              value={data?.kpis?.sodAlerts || 0}
              subtitle="Violations détectées"
              trend={data?.kpis?.sodAlerts && data.kpis.sodAlerts > 0 ? "down" : "neutral"}
              trendValue={data?.kpis?.sodAlerts && data.kpis.sodAlerts > 0 ? "Action requise" : "Aucune alerte"}
              color={data?.kpis?.sodAlerts && data.kpis.sodAlerts > 0 ? "error" : "success"}
              icon={<Warning />}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Taux d'assiduité"
              value={`${data?.kpis?.attendanceRate || 0}%`}
              subtitle="Moyenne globale"
              trend="up"
              trendValue="+2% vs trimestre dernier"
              color="info"
              icon={<TrendingUp />}
            />
          </Grid>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Évolution des inscriptions (2025-2026)
                </Typography>
                <Box
                  sx={{
                    height: 300,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: "grey.100",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Graphique d'évolution des inscriptions
                    <br />
                    (Intégration recharts à venir)
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }

  // USER_TEACHER / ENSEIGNANT
  if (activeRole === "USER_TEACHER" || activeRole === "ENSEIGNANT") {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Mes cours</Typography>
          <Button variant="contained" color="primary" href="/notes">
            Saisie notes
          </Button>
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Mes cours actuels
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Code</TableCell>
                        <TableCell>Nom du cours</TableCell>
                        <TableCell align="right">Nb étudiants</TableCell>
                        <TableCell>Prochain cours</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data?.courses?.map((course, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Chip label={course.code} size="small" color="primary" />
                          </TableCell>
                          <TableCell>{course.name}</TableCell>
                          <TableCell align="right">{course.studentCount}</TableCell>
                          <TableCell>{new Date(course.nextClass).toLocaleString("fr-FR")}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Mes statistiques
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    Étudiants notés
                  </Typography>
                  <Typography variant="h6">
                    {data?.stats?.gradedStudents || 0} / {data?.stats?.totalStudents || 0}
                  </Typography>
                </Box>
                <Box
                  sx={{
                    width: "100%",
                    height: 8,
                    bgcolor: "grey.200",
                    borderRadius: 1,
                    overflow: "hidden",
                  }}
                >
                  <Box
                    sx={{
                      width: `${((data?.stats?.gradedStudents || 0) / (data?.stats?.totalStudents || 1)) * 100}%`,
                      height: "100%",
                      bgcolor: "primary.main",
                    }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }

  // USER_STUDENT
  if (activeRole === "USER_STUDENT") {
    const isBalancePositive = (data?.balance || 0) <= 0;
    return (
      <Box>
        <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
          Mon tableau de bord étudiant
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Mes notes récentes
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>UE</TableCell>
                        <TableCell align="right">Moyenne</TableCell>
                        <TableCell align="center">Statut</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data?.grades?.map((grade, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Chip label={grade.ueCode} size="small" />
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="h6">{grade.average.toFixed(1)}/20</Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip
                              label={grade.status}
                              color={grade.status === "Validée" ? "success" : "error"}
                              size="small"
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card
              sx={{
                bgcolor: isBalancePositive ? "success.light" : "error.light",
                color: isBalancePositive ? "success.contrastText" : "error.contrastText",
              }}
            >
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                  <Payment sx={{ mr: 1 }} />
                  <Typography variant="h6">Solde à payer</Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: "bold", mb: 2 }}>
                  {Math.abs(data?.balance || 0).toLocaleString("fr-FR")} XAF
                </Typography>
                {!isBalancePositive && (
                  <Button
                    variant="contained"
                    fullWidth
                    sx={{
                      bgcolor: "error.main",
                      "&:hover": { bgcolor: "error.dark" },
                    }}
                    onClick={() => alert("Fonctionnalité de paiement à venir")}
                  >
                    Payer en ligne
                  </Button>
                )}
                {isBalancePositive && (
                  <Chip label="Aucun solde dû" color="success" sx={{ mt: 1 }} />
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }

  // OPERATOR_FINANCE
  if (activeRole === "OPERATOR_FINANCE") {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Gestion financière</Typography>
          <Button variant="contained" color="primary" onClick={() => alert("Fonctionnalité d'encaissement à venir")}>
            Encaisser
          </Button>
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Factures impayées
                </Typography>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Étudiant</TableCell>
                        <TableCell align="right">Montant</TableCell>
                        <TableCell>Échéance</TableCell>
                        <TableCell align="center">Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data?.unpaidInvoices?.map((invoice, index) => (
                        <TableRow key={index}>
                          <TableCell>{invoice.student}</TableCell>
                          <TableCell align="right">
                            <Typography variant="body1" sx={{ fontWeight: "bold" }}>
                              {invoice.amount.toLocaleString("fr-FR")} XAF
                            </Typography>
                          </TableCell>
                          <TableCell>{new Date(invoice.dueDate).toLocaleDateString("fr-FR")}</TableCell>
                          <TableCell align="center">
                            <Button size="small" variant="outlined" color="primary">
                              Détails
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                  <Receipt sx={{ mr: 1, color: "warning.main" }} />
                  <Typography variant="h6">Total en attente</Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: "bold", color: "warning.main", mb: 2 }}>
                  {(data?.totalPending || 0).toLocaleString("fr-FR")} XAF
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {data?.unpaidInvoices?.length || 0} facture(s) en attente de paiement
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }

  // Rôle non géré
  return (
    <Alert severity="info">
      Dashboard non disponible pour le rôle "{activeRole}". Contactez l'administrateur.
    </Alert>
  );
};

export default DashboardContent;
