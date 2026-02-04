import React, { useState, useEffect } from "react";
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
  School,
  CheckCircle,
} from "@mui/icons-material";
import { Link } from "react-router-dom";
import { DataGrid, GridColDef, GridActionsCellItem } from "@mui/x-data-grid";
import toast from "react-hot-toast";

import { useAuth } from "../context/AuthContext";
import { useDashboardData } from "../hooks/useDashboardData";
import KpiCard from "./KpiCard";
import KpiGraph from "./KpiGraph";
import api from "../services/api";

const DashboardContent: React.FC = () => {
  const { activeRole, user } = useAuth();
  const { data, loading, error } = useDashboardData(activeRole);
  
  // Hooks pour OPERATOR_FINANCE - doivent être déclarés avant tout return conditionnel
  const [invoices, setInvoices] = useState<any[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  
  // Hooks pour USER_STUDENT - doivent être déclarés avant tout return conditionnel
  const [echeances, setEcheances] = useState<any>(null);
  const [loadingEcheances, setLoadingEcheances] = useState(false);
  const [moratoires, setMoratoires] = useState<any[]>([]);
  const [loadingMoratoires, setLoadingMoratoires] = useState(false);

  useEffect(() => {
    if (activeRole === "OPERATOR_FINANCE") {
      const fetchInvoices = async () => {
        setInvoicesLoading(true);
        try {
          const response = await api.get("/api/invoices/", {
            params: { status: "impayée" },
          });
          const results = Array.isArray(response.data) ? response.data : response.data.results || [];
          setInvoices(results);
        } catch (err) {
          toast.error("Erreur lors du chargement des factures impayées");
          console.error(err);
        } finally {
          setInvoicesLoading(false);
        }
      };
      fetchInvoices();
    }
  }, [activeRole]);

  // useEffect pour USER_STUDENT - doit être déclaré avant tout return conditionnel
  useEffect(() => {
    if (activeRole !== "USER_STUDENT" || !user?.email) return;
    const fetchEcheances = async () => {
      setLoadingEcheances(true);
      try {
        // Récupérer l'ID de l'étudiant depuis les données du dashboard ou faire un appel API
        const studentsRes = await api.get("/api/students/");
        const students = Array.isArray(studentsRes.data) ? studentsRes.data : studentsRes.data.results || [];
        const currentStudent = students.find((s: any) => s.email === user.email || s.identity_nested?.email === user.email);
        
        if (currentStudent?.id) {
          const echeancesRes = await api.get(`/api/students/${currentStudent.id}/echeances/`);
          setEcheances(echeancesRes.data);
          
          // Charger les moratoires actifs
          try {
            const moratoiresRes = await api.get(`/api/students/${currentStudent.id}/moratoires-actifs/`);
            setMoratoires(moratoiresRes.data.moratoires || []);
            
            // Alertes pour moratoires proches de l'échéance
            const today = new Date();
            const in7Days = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
            
            moratoiresRes.data.moratoires?.forEach((moratoire: any) => {
              if (moratoire.statut === "Actif") {
                const dateFin = new Date(moratoire.date_fin);
                if (dateFin < today) {
                  toast.error(
                    `Moratoire dépassé. Date de fin: ${dateFin.toLocaleDateString("fr-FR")}`,
                    { duration: 8000 }
                  );
                } else if (dateFin <= in7Days) {
                  const joursRestants = Math.ceil((dateFin.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                  toast(
                    `Moratoire se terminant dans ${joursRestants} jour(s). Date de fin: ${dateFin.toLocaleDateString("fr-FR")}`,
                    { duration: 6000, icon: "⚠️" }
                  );
                }
              }
            });
          } catch (err) {
            console.error("Erreur chargement moratoires:", err);
          }
          
          // Toast d'alerte si échéance proche ou en retard
          if (echeancesRes.data.jours_retard > 0) {
            toast.error(
              `Échéance en retard de ${echeancesRes.data.jours_retard} jours. Montant dû: ${echeancesRes.data.montant_du.toLocaleString("fr-FR")} FCFA`,
              { duration: 8000 }
            );
          } else if (echeancesRes.data.prochaine_echeance) {
            const prochaineDate = new Date(echeancesRes.data.prochaine_echeance);
            const joursRestants = Math.ceil((prochaineDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
            if (joursRestants <= 7 && joursRestants >= 0 && echeancesRes.data.montant_du > 0) {
              toast(
                `Échéance prochaine dans ${joursRestants} jour(s). Montant à payer: ${echeancesRes.data.montant_du.toLocaleString("fr-FR")} FCFA`,
                { duration: 6000, icon: "⚠️" }
              );
            }
          }
        }
      } catch (err) {
        console.error("Erreur chargement échéances:", err);
      } finally {
        setLoadingEcheances(false);
      }
    };
    fetchEcheances();
  }, [user?.email, activeRole]);

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

  // RECTEUR / DAF / SG / VIEWER_STRATEGIC / ADMIN_SI
  if (activeRole === "RECTEUR" || activeRole === "DAF" || activeRole === "SG" || activeRole === "VIEWER_STRATEGIC" || activeRole === "ADMIN_SI") {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Tableau de bord institutionnel</Typography>
          {activeRole === "RECTEUR" && (
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button variant="outlined" component={Link} to="/faculties">
                Gérer les facultés
              </Button>
              <Button variant="outlined" component={Link} to="/students">
                Gérer les étudiants
              </Button>
              <Button variant="outlined" component={Link} to="/notes">
                Vue globale notes
              </Button>
            </Box>
          )}
        </Box>
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
              value={`${data?.kpis?.attendanceRate || 92}%`}
              subtitle="Moyenne globale"
              trend="up"
              trendValue="+2% vs trimestre dernier"
              color="info"
              icon={<TrendingUp />}
            />
          </Grid>
          <Grid item xs={12}>
            <KpiGraph
              data={data?.graph || []}
              title="Évolution des inscriptions (2025-2026)"
              dataKey="value"
              color="#1976d2"
              height={300}
            />
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
          <Button variant="contained" color="primary" component={Link} to="/notes">
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
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Mon tableau de bord étudiant</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="contained" component={Link} to="/students">
              Mon dossier
            </Button>
            <Button variant="outlined" component={Link} to="/notes">
              Mes notes
            </Button>
          </Box>
        </Box>
        <Grid container spacing={3}>
          {/* Card Solde & Échéances */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Solde & Échéances
                </Typography>
                <Typography
                  variant="h4"
                  sx={{
                    color: isBalancePositive ? "success.main" : "error.main",
                    fontWeight: "bold",
                    mb: 2,
                  }}
                >
                  {Math.abs(data?.balance || 0).toLocaleString("fr-FR")} FCFA
                </Typography>
                {loadingEcheances ? (
                  <CircularProgress size={24} />
                ) : echeances ? (
                  <Box>
                    {echeances.montant_du > 0 ? (
                      <Alert
                        severity={echeances.jours_retard > 0 ? "error" : echeances.jours_retard >= -7 ? "warning" : "info"}
                        sx={{ mb: 2 }}
                      >
                        <Typography variant="body2" fontWeight="bold">
                          {echeances.prochaine_echeance
                            ? `À payer avant ${new Date(echeances.prochaine_echeance).toLocaleDateString("fr-FR")}`
                            : "Montant dû"}
                        </Typography>
                        <Typography variant="h6" color="error.main">
                          {echeances.montant_du.toLocaleString("fr-FR")} FCFA
                        </Typography>
                        {echeances.jours_retard > 0 && (
                          <Typography variant="body2" color="error.main" sx={{ mt: 1 }}>
                            En retard de {echeances.jours_retard} jour(s)
                          </Typography>
                        )}
                      </Alert>
                    ) : (
                      <Alert severity="success">
                        <Typography variant="body2">À jour</Typography>
                      </Alert>
                    )}
                    <Typography variant="body2" color="text.secondary">
                      {echeances.statut}
                    </Typography>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Chargement des échéances...
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
          {/* Card Moratoires actifs */}
          {echeances && echeances.montant_du > 0 && (
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Moratoires actifs
                  </Typography>
                  {loadingMoratoires ? (
                    <CircularProgress size={24} />
                  ) : moratoires && moratoires.length > 0 ? (
                    <Box>
                      {moratoires
                        .filter((m) => m.statut === "Actif")
                        .map((moratoire) => {
                          const dateFin = new Date(moratoire.date_fin);
                          const today = new Date();
                          const joursRestants = Math.ceil((dateFin.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
                          const isDueSoon = joursRestants <= 7 && joursRestants >= 0;
                          const isOverdue = dateFin < today;

                          return (
                            <Alert
                              key={moratoire.id}
                              severity={isOverdue ? "error" : isDueSoon ? "warning" : "info"}
                              sx={{ mb: 2 }}
                            >
                              <Typography variant="body2" fontWeight="bold">
                                Moratoire en cours
                              </Typography>
                              <Typography variant="body2">
                                Montant restant: {moratoire.montant_reporte.toLocaleString("fr-FR")} FCFA
                              </Typography>
                              <Typography
                                variant="body2"
                                sx={{ color: isOverdue || isDueSoon ? "error.main" : "text.secondary" }}
                              >
                                Date fin: {dateFin.toLocaleDateString("fr-FR")}
                                {isDueSoon && ` (Dans ${joursRestants} jour(s))`}
                                {isOverdue && " (Dépassé)"}
                              </Typography>
                            </Alert>
                          );
                        })}
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Aucun moratoire actif.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          )}
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
                      {data?.grades && data.grades.length > 0 ? (
                        data.grades.map((grade: any, index: number) => (
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
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={3} align="center">
                            <Typography variant="body2" color="text.secondary">
                              Aucune note disponible
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
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
    const invoiceColumns: GridColDef[] = [
      {
        field: "student",
        headerName: "Étudiant",
        minWidth: 200,
        flex: 1,
        valueGetter: (params) => {
          // Si c'est déjà une string, la retourner
          if (typeof params.row.student === "string") {
            return params.row.student;
          }
          // Sinon, essayer de récupérer depuis identity_uuid
          return params.row.identity_uuid || "—";
        },
      },
      {
        field: "total_amount",
        headerName: "Montant",
        minWidth: 150,
        flex: 1,
        valueFormatter: (params) => `${Number(params.value || 0).toLocaleString("fr-FR")} XAF`,
        renderCell: (params) => (
          <Typography variant="body1" sx={{ fontWeight: "bold" }}>
            {Number(params.value || 0).toLocaleString("fr-FR")} XAF
          </Typography>
        ),
      },
      {
        field: "due_date",
        headerName: "Échéance",
        minWidth: 150,
        flex: 1,
        valueFormatter: (params) => {
          if (!params.value) return "—";
          return new Date(params.value).toLocaleDateString("fr-FR");
        },
      },
      {
        field: "actions",
        type: "actions",
        headerName: "Actions",
        width: 120,
        getActions: (params) => [
          <GridActionsCellItem
            key="encash"
            icon={<CheckCircle />}
            label="Encaisser"
            onClick={() => {
              toast("Fonctionnalité d'encaissement à venir", { icon: "💳" });
            }}
          />,
        ],
      },
    ];

    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Tableau de bord Finance</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="outlined" component={Link} to="/students?status=Bloqué">
              Étudiants bloqués
            </Button>
            <Button variant="contained" color="primary" onClick={() => alert("Fonctionnalité d'encaissement à venir")}>
              Encaisser
            </Button>
          </Box>
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Factures impayées
                </Typography>
                {invoicesLoading ? (
                  <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Box sx={{ height: 400, width: "100%" }}>
                    <DataGrid
                      rows={invoices.map((inv, idx) => ({ id: inv.id || idx, ...inv }))}
                      columns={invoiceColumns}
                      pageSizeOptions={[10, 25, 50]}
                      initialState={{
                        pagination: {
                          paginationModel: { pageSize: 10 },
                        },
                      }}
                    />
                  </Box>
                )}
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
                  {data?.unpaidInvoices?.length || invoices.length || 0} facture(s) en attente de paiement
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
    );
  }

  // DOYEN / VALIDATOR_ACAD
  if (activeRole === "DOYEN" || activeRole === "VALIDATOR_ACAD") {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Pilotage académique</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="contained" component={Link} to="/students">
              Gérer les étudiants
            </Button>
            <Button variant="contained" color="primary" component={Link} to="/notes">
              PV Jury / Validation
            </Button>
          </Box>
        </Box>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Règles académiques de la faculté
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Ajustez les règles de notation et les règles financières selon votre scope.
            </Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Button variant="contained" component={Link} to="/faculties">
                Ouvrir la gestion des facultés
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  // SCOLARITE
  if (activeRole === "SCOLARITE") {
    return (
      <Box>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
          <Typography variant="h4">Gestion de la scolarité</Typography>
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button variant="contained" component={Link} to="/students">
              Inscrire / Gérer étudiants
            </Button>
          </Box>
        </Box>
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Total étudiants"
              value={data?.kpis?.totalStudents?.toLocaleString() || "0"}
              subtitle="Tous les étudiants"
              color="primary"
              icon={<People />}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Total inscriptions"
              value={data?.kpis?.totalRegistrations?.toLocaleString() || "0"}
              subtitle="Toutes les inscriptions"
              color="info"
              icon={<School />}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <KpiCard
              title="Inscriptions cette année"
              value={data?.kpis?.registrationsThisYear?.toLocaleString() || "0"}
              subtitle="Année académique active"
              color="success"
              icon={<TrendingUp />}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Actions rapides
                </Typography>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  <Button variant="outlined" fullWidth component={Link} to="/students">
                    Liste des étudiants
                  </Button>
                  <Button variant="outlined" fullWidth onClick={() => alert("Fonctionnalité à venir")}>
                    Nouvelle inscription
                  </Button>
                </Box>
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
