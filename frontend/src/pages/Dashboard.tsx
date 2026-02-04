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
  Chip,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import {
  Assessment,
  School,
  Warning,
  AttachMoney,
} from "@mui/icons-material";
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
import { DataGrid } from "@mui/x-data-grid";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../services/api";

import { useAuth } from "../context/AuthContext";
import DashboardContent from "../components/DashboardContent";
import { useDashboardData } from "../hooks/useDashboardData";
import { Bourse, Moratoire } from "../types/frais";

const Dashboard: React.FC = () => {
  const { activeRole, user, token } = useAuth();
  const navigate = useNavigate();
  const { data } = useDashboardData(activeRole);
  const prevSodAlerts = React.useRef<number | null>(null);

  const isRecteur = activeRole === "RECTEUR";
  const isFinance = activeRole === "OPERATOR_FINANCE";
  const isStudent = activeRole === "USER_STUDENT";

  // État pour la modal de demande (USER_STUDENT)
  const [requestModalOpen, setRequestModalOpen] = React.useState(false);
  const [requestForm, setRequestForm] = React.useState({
    type_demande: "",
    motif: "",
    piece_jointe: null as File | null,
  });
  const [submittingRequest, setSubmittingRequest] = React.useState(false);

  // État pour les moratoires (OPERATOR_FINANCE)
  const [moratoiresActifs, setMoratoiresActifs] = React.useState<Moratoire[]>([]);
  const [moratoiresDepasses, setMoratoiresDepasses] = React.useState<Moratoire[]>([]);
  const [loadingMoratoires, setLoadingMoratoires] = React.useState(false);
  
  // État pour les bourses (RECTEUR)
  const [boursesActives, setBoursesActives] = React.useState<Bourse[]>([]);
  const [loadingBourses, setLoadingBourses] = React.useState(false);
  const [totalStudents, setTotalStudents] = React.useState(0);
  
  // État pour impact bourses (OPERATOR_FINANCE)
  const [montantBoursesMois, setMontantBoursesMois] = React.useState(0);
  const [loadingBoursesFinance, setLoadingBoursesFinance] = React.useState(false);
  const studentsByFaculty = data?.kpis?.studentsByFaculty ?? [];
  const totalStudentsByFaculty = studentsByFaculty.reduce((sum, item) => sum + item.students, 0);
  const monthlyRevenueRaw = data?.kpis?.monthlyRevenue || "0";
  const monthlyRevenueValue = Number(String(monthlyRevenueRaw).replace(/[^0-9]/g, "")) || 0;
  
  // KPI Notes pour RECTEUR
  const ueValidatedPercent = data?.kpis?.ueValidatedPercent ?? 0;
  const studentsWithDebtPercent = data?.kpis?.studentsWithDebtPercent ?? 0;
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

  // Charger les moratoires pour OPERATOR_FINANCE
  React.useEffect(() => {
    if (!isFinance || !token) {
      return;
    }
    const fetchMoratoires = async () => {
      setLoadingMoratoires(true);
      try {
        // Charger les moratoires actifs
        const actifsRes = await api.get<any>("/api/moratoires/", {
          params: { statut: "Actif" },
        });
        const actifs: Moratoire[] = Array.isArray(actifsRes.data) 
          ? actifsRes.data 
          : (actifsRes.data?.results || []);
        setMoratoiresActifs(actifs);

        // Charger les moratoires dépassés
        const depassesRes = await api.get<any>("/api/moratoires/", {
          params: { statut: "Dépassé" },
        });
        const depasses: Moratoire[] = Array.isArray(depassesRes.data) 
          ? depassesRes.data 
          : (depassesRes.data?.results || []);
        setMoratoiresDepasses(depasses);

        // Toast d'alerte si moratoires dépassés
        if (depasses.length > 0) {
          toast.error(
            `${depasses.length} moratoire(s) dépassé(s) nécessitent une attention.`,
            { duration: 8000 }
          );
        }
      } catch (err) {
        console.error("Erreur chargement moratoires:", err);
        toast.error("Erreur lors du chargement des moratoires.");
      } finally {
        setLoadingMoratoires(false);
      }
    };
    fetchMoratoires();
  }, [isFinance, token]);

  // Charger les bourses actives pour RECTEUR
  React.useEffect(() => {
    if (!isRecteur || !token) {
      return;
    }
    const fetchBourses = async () => {
      setLoadingBourses(true);
      try {
        const response = await api.get<any>("/api/bourses/", {
          params: { statut: "Active" },
        });
        const bourses: Bourse[] = Array.isArray(response.data)
          ? response.data
          : response.data?.results || [];
        setBoursesActives(bourses);
        
        // Charger le total d'étudiants pour calculer le pourcentage
        try {
          const studentsRes = await api.get<any>("/api/students/");
          const students = Array.isArray(studentsRes.data)
            ? studentsRes.data
            : studentsRes.data?.results || [];
          setTotalStudents(students.length);
        } catch {
          // Ignorer l'erreur
        }
      } catch (err) {
        console.error("Erreur chargement bourses:", err);
        toast.error("Erreur lors du chargement des bourses.");
      } finally {
        setLoadingBourses(false);
      }
    };
    fetchBourses();
  }, [isRecteur, token]);

  // Charger l'impact bourses sur trésorerie pour OPERATOR_FINANCE
  React.useEffect(() => {
    if (!isFinance || !token) {
      return;
    }
    const fetchBoursesImpact = async () => {
      setLoadingBoursesFinance(true);
      try {
        const response = await api.get<any>("/api/bourses/", {
          params: { statut: "Active" },
        });
        const bourses: Bourse[] = Array.isArray(response.data)
          ? response.data
          : response.data?.results || [];
        
        // Calculer le montant couvert ce mois (bourses actives)
        const today = new Date();
        const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        
        const boursesCeMois = bourses.filter((b) => {
          const dateAttribution = new Date(b.date_attribution);
          return dateAttribution >= firstDayOfMonth;
        });
        
        const montantTotal = boursesCeMois.reduce((sum, b) => sum + b.montant, 0);
        setMontantBoursesMois(montantTotal);
      } catch (err) {
        console.error("Erreur chargement impact bourses:", err);
      } finally {
        setLoadingBoursesFinance(false);
      }
    };
    fetchBoursesImpact();
  }, [isFinance, token]);

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
            <Box sx={{ display: "flex", gap: 1 }}>
              <Button variant="outlined" component={Link} to="/notes">
                Vue globale notes
              </Button>
              <Button variant="outlined" onClick={() => toast("Export PDF/CSV à venir", { icon: "📊" })}>
                Reporting global
              </Button>
            </Box>
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
            <Grid item xs={12} md={4}>
              <Card
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  transition: "transform 0.2s, box-shadow 0.2s",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      % UE validées
                    </Typography>
                    <Assessment sx={{ color: "success.main", opacity: 0.7 }} />
                  </Box>
                  <Typography variant="h4" sx={{ fontWeight: "bold", mb: 1 }}>
                    {ueValidatedPercent.toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Unités d'enseignement validées global
                  </Typography>
                  <Box sx={{ display: "flex", alignItems: "center", mt: 1 }}>
                    <Chip
                      label={ueValidatedPercent >= 70 ? "Excellent" : ueValidatedPercent >= 50 ? "Bon" : "À améliorer"}
                      color={ueValidatedPercent >= 70 ? "success" : ueValidatedPercent >= 50 ? "warning" : "error"}
                      size="small"
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  transition: "transform 0.2s, box-shadow 0.2s",
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: 4,
                  },
                }}
              >
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      % Étudiants avec dette
                    </Typography>
                    <School sx={{ color: "warning.main", opacity: 0.7 }} />
                  </Box>
                  <Typography variant="h4" sx={{ fontWeight: "bold", mb: 1 }}>
                    {studentsWithDebtPercent.toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Étudiants avec solde impayé
                  </Typography>
                  <Box sx={{ display: "flex", alignItems: "center", mt: 1 }}>
                    <Chip
                      label={studentsWithDebtPercent <= 20 ? "Normal" : studentsWithDebtPercent <= 40 ? "Attention" : "Critique"}
                      color={studentsWithDebtPercent <= 20 ? "success" : studentsWithDebtPercent <= 40 ? "warning" : "error"}
                      size="small"
                    />
                  </Box>
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
            
            {/* Section Bourses actives pour RECTEUR */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
                    <Typography variant="h6">Bourses actives</Typography>
                    <Button variant="outlined" component={Link} to="/students?boursier=true">
                      Voir tous les boursiers
                    </Button>
                  </Box>
                  
                  {/* KPI Bourses */}
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={12} sm={4}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary">
                            Nombre de bourses actives
                          </Typography>
                          <Typography variant="h4" sx={{ mt: 1 }}>
                            {loadingBourses ? <CircularProgress size={24} /> : boursesActives.length}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary">
                            Montant total attribué
                          </Typography>
                          <Typography variant="h4" sx={{ mt: 1 }}>
                            {loadingBourses ? (
                              <CircularProgress size={24} />
                            ) : (
                              `${boursesActives.reduce((sum, b) => sum + b.montant, 0).toLocaleString("fr-FR")} XAF`
                            )}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary">
                            % Étudiants boursiers
                          </Typography>
                          <Typography variant="h4" sx={{ mt: 1 }}>
                            {loadingBourses ? (
                              <CircularProgress size={24} />
                            ) : totalStudents > 0 ? (
                              `${((boursesActives.length / totalStudents) * 100).toFixed(1)}%`
                            ) : (
                              "—"
                            )}
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                  
                  {/* DataGrid Bourses actives */}
                  {loadingBourses ? (
                    <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                      <CircularProgress />
                    </Box>
                  ) : boursesActives.length === 0 ? (
                    <Alert severity="info">Aucune bourse active.</Alert>
                  ) : (
                    <Box sx={{ height: 400, width: "100%" }}>
                      <DataGrid
                        rows={boursesActives.map((b) => ({
                          id: b.id,
                          student: b.student_nom || b.student_matricule,
                          matricule: b.student_matricule,
                          type_bourse: b.type_bourse,
                          montant: b.montant,
                          date_fin: b.date_fin_validite,
                          statut: b.statut,
                        }))}
                        columns={[
                          {
                            field: "student",
                            headerName: "Étudiant",
                            minWidth: 200,
                            flex: 1,
                          },
                          {
                            field: "matricule",
                            headerName: "Matricule",
                            minWidth: 120,
                            flex: 0.8,
                          },
                          {
                            field: "type_bourse",
                            headerName: "Type",
                            minWidth: 150,
                            flex: 1,
                            renderCell: (params) => {
                              const typeLabels: Record<string, string> = {
                                Merite: "Mérite",
                                Besoin: "Besoins sociaux",
                                Tutelle: "Tutelle",
                                Externe: "Externe",
                                Interne: "Interne",
                              };
                              return (
                                <Chip
                                  label={typeLabels[params.value] || params.value}
                                  size="small"
                                  color="primary"
                                  variant="outlined"
                                />
                              );
                            },
                          },
                          {
                            field: "montant",
                            headerName: "Montant",
                            minWidth: 150,
                            flex: 1,
                            valueFormatter: (params) => `${Number(params.value || 0).toLocaleString("fr-FR")} XAF`,
                            renderCell: (params) => (
                              <Typography variant="body2" sx={{ fontWeight: "bold" }}>
                                {Number(params.value || 0).toLocaleString("fr-FR")} XAF
                              </Typography>
                            ),
                          },
                          {
                            field: "date_fin",
                            headerName: "Date fin",
                            minWidth: 150,
                            flex: 1,
                            valueFormatter: (params) => {
                              if (!params.value) return "—";
                              return new Date(params.value).toLocaleDateString("fr-FR");
                            },
                            renderCell: (params) => {
                              if (!params.value) return "—";
                              const dateFin = new Date(params.value);
                              const today = new Date();
                              const joursRestants = Math.ceil(
                                (dateFin.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
                              );
                              const isDueSoon = joursRestants <= 30 && joursRestants >= 0;
                              const isOverdue = dateFin < today;

                              return (
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                  <Typography
                                    variant="body2"
                                    sx={{ color: isOverdue ? "error.main" : isDueSoon ? "warning.main" : "text.primary" }}
                                  >
                                    {dateFin.toLocaleDateString("fr-FR")}
                                  </Typography>
                                  {isDueSoon && !isOverdue && (
                                    <Chip label={`Dans ${joursRestants}j`} size="small" color="warning" />
                                  )}
                                  {isOverdue && <Chip label="Expirée" size="small" color="error" />}
                                </Box>
                              );
                            },
                          },
                        ]}
                        pageSizeOptions={[5, 10, 25]}
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
          </Grid>
        </Box>
      )}

      {isFinance && (
        <Box sx={{ mt: 4 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
            <Typography variant="h5">Suivi des moratoires</Typography>
            <Button variant="outlined" component={Link} to="/students?moratoire_actif=true">
              Voir tous
            </Button>
          </Box>
          <Grid container spacing={3}>
            {/* KPI Moratoires */}
            <Grid item xs={12} sm={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Moratoires actifs
                    </Typography>
                    <Warning sx={{ color: "warning.main", opacity: 0.7 }} />
                  </Box>
                  <Typography variant="h4" sx={{ fontWeight: "bold", mb: 1 }}>
                    {loadingMoratoires ? <CircularProgress size={24} /> : moratoiresActifs.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    En cours
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Moratoires dépassés
                    </Typography>
                    <Warning sx={{ color: "error.main", opacity: 0.7 }} />
                  </Box>
                  <Typography
                    variant="h4"
                    sx={{
                      fontWeight: "bold",
                      mb: 1,
                      color: moratoiresDepasses.length > 0 ? "error.main" : "text.primary",
                    }}
                  >
                    {loadingMoratoires ? <CircularProgress size={24} /> : moratoiresDepasses.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Nécessitent attention
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                    <Typography variant="subtitle2" color="text.secondary">
                      Montant total reporté
                    </Typography>
                    <AttachMoney sx={{ color: "info.main", opacity: 0.7 }} />
                  </Box>
                  <Typography variant="h4" sx={{ fontWeight: "bold", mb: 1 }}>
                    {loadingMoratoires ? (
                      <CircularProgress size={24} />
                    ) : (
                      `${moratoiresActifs
                        .reduce((sum, m) => sum + m.montant_reporte, 0)
                        .toLocaleString("fr-FR")} FCFA`
                    )}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total en moratoire
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* DataGrid Moratoires actifs */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Moratoires actifs
                  </Typography>
                  {loadingMoratoires ? (
                    <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                      <CircularProgress />
                    </Box>
                  ) : moratoiresActifs.length === 0 ? (
                    <Alert severity="info">Aucun moratoire actif.</Alert>
                  ) : (
                    <Box sx={{ height: 400, width: "100%" }}>
                      <DataGrid
                        rows={moratoiresActifs.map((m) => ({
                          id: m.id,
                          student: m.student_nom || m.student_matricule,
                          matricule: m.student_matricule,
                          montant: m.montant_reporte,
                          date_fin: m.date_fin,
                          statut: m.statut,
                          motif: m.motif,
                          accorde_par: m.accorde_par_email,
                        }))}
                        columns={[
                          {
                            field: "student",
                            headerName: "Étudiant",
                            minWidth: 200,
                            flex: 1,
                          },
                          {
                            field: "matricule",
                            headerName: "Matricule",
                            minWidth: 120,
                            flex: 0.8,
                          },
                          {
                            field: "montant",
                            headerName: "Montant reporté",
                            minWidth: 150,
                            flex: 1,
                            valueFormatter: (params) => `${Number(params.value || 0).toLocaleString("fr-FR")} FCFA`,
                            renderCell: (params) => (
                              <Typography variant="body2" sx={{ fontWeight: "bold" }}>
                                {Number(params.value || 0).toLocaleString("fr-FR")} FCFA
                              </Typography>
                            ),
                          },
                          {
                            field: "date_fin",
                            headerName: "Date de fin",
                            minWidth: 150,
                            flex: 1,
                            valueFormatter: (params) => {
                              if (!params.value) return "—";
                              return new Date(params.value).toLocaleDateString("fr-FR");
                            },
                            renderCell: (params) => {
                              if (!params.value) return "—";
                              const dateFin = new Date(params.value);
                              const today = new Date();
                              const joursRestants = Math.ceil(
                                (dateFin.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
                              );
                              const isDueSoon = joursRestants <= 7 && joursRestants >= 0;
                              const isOverdue = dateFin < today;

                              return (
                                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                                  <Typography
                                    variant="body2"
                                    sx={{ color: isOverdue ? "error.main" : isDueSoon ? "warning.main" : "text.primary" }}
                                  >
                                    {dateFin.toLocaleDateString("fr-FR")}
                                  </Typography>
                                  {isDueSoon && !isOverdue && (
                                    <Chip label={`Dans ${joursRestants}j`} size="small" color="warning" />
                                  )}
                                  {isOverdue && <Chip label="Dépassé" size="small" color="error" />}
                                </Box>
                              );
                            },
                          },
                          {
                            field: "statut",
                            headerName: "Statut",
                            minWidth: 120,
                            flex: 0.8,
                            renderCell: (params) => (
                              <Chip
                                label={params.value}
                                color={params.value === "Dépassé" ? "error" : params.value === "Respecté" ? "success" : "warning"}
                                size="small"
                              />
                            ),
                          },
                          {
                            field: "motif",
                            headerName: "Motif",
                            minWidth: 200,
                            flex: 1.2,
                            valueGetter: (params) => params.value || "—",
                          },
                          {
                            field: "accorde_par",
                            headerName: "Accordé par",
                            minWidth: 150,
                            flex: 1,
                            valueGetter: (params) => params.value || "—",
                          },
                        ]}
                        pageSizeOptions={[5, 10, 25]}
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
            
            {/* Section Impact bourses sur trésorerie pour OPERATOR_FINANCE */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                    <Typography variant="h6">Impact bourses sur trésorerie</Typography>
                    <Button variant="outlined" component={Link} to="/students?boursier=true">
                      Étudiants boursiers
                    </Button>
                  </Box>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Card variant="outlined">
                        <CardContent>
                          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                            <Typography variant="subtitle2" color="text.secondary">
                              Montant couvert par bourses ce mois
                            </Typography>
                            <AttachMoney sx={{ color: "info.main", opacity: 0.7 }} />
                          </Box>
                          <Typography variant="h4" sx={{ fontWeight: "bold", mb: 1 }}>
                            {loadingBoursesFinance ? (
                              <CircularProgress size={24} />
                            ) : (
                              `${montantBoursesMois.toLocaleString("fr-FR")} XAF`
                            )}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Bourses actives attribuées ce mois
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Alert severity="info">
                        Les bourses actives réduisent le montant dû par les étudiants et impactent directement la trésorerie.
                        <br />
                        <Button
                          component={Link}
                          to="/students?boursier=true"
                          size="small"
                          sx={{ mt: 1 }}
                        >
                          Voir la liste des étudiants boursiers
                        </Button>
                      </Alert>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Vue USER_STUDENT */}
      {activeRole === "USER_STUDENT" && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h4" gutterBottom>
            Mon Espace Étudiant
          </Typography>
          <Grid container spacing={3}>
            {/* Card Mon Profil */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Mon Profil
                  </Typography>
                  <DashboardContent />
                </CardContent>
              </Card>
            </Grid>

            {/* Card Solde & Paiements */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Solde & Paiements
                  </Typography>
                  <StudentBalanceCard />
                </CardContent>
              </Card>
            </Grid>

            {/* Card Mes Inscriptions */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Mes Inscriptions
                  </Typography>
                  <StudentRegistrationsCard />
                </CardContent>
              </Card>
            </Grid>

            {/* Card Mes Notes */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Mes Notes
                  </Typography>
                  <Button
                    variant="outlined"
                    fullWidth
                    onClick={() => navigate("/notes")}
                    sx={{ mt: 2 }}
                  >
                    Consulter mes notes
                  </Button>
                </CardContent>
              </Card>
            </Grid>

            {/* Card Mes Bourses/Moratoires */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Mes Bourses & Moratoires
                  </Typography>
                  <StudentBoursesMoratoiresCard />
                </CardContent>
              </Card>
            </Grid>

            {/* Card Actions */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Actions
                  </Typography>
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 2 }}>
                    <Button
                      variant="contained"
                      fullWidth
                      onClick={() => setRequestModalOpen(true)}
                    >
                      Soumettre une demande
                    </Button>
                    <Button
                      variant="outlined"
                      fullWidth
                      onClick={() => {
                        toast("Paiement mobile bientôt disponible", { icon: "💳" });
                      }}
                    >
                      Payer en ligne
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Modal de soumission de demande */}
      <Dialog open={requestModalOpen} onClose={() => setRequestModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Soumettre une demande</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Type de demande</InputLabel>
              <Select
                value={requestForm.type_demande}
                onChange={(e) => setRequestForm({ ...requestForm, type_demande: e.target.value })}
                label="Type de demande"
              >
                <MenuItem value="Releve">Relevé de notes</MenuItem>
                <MenuItem value="Certificat">Certificat de scolarité</MenuItem>
                <MenuItem value="Moratoire">Demande de moratoire</MenuItem>
                <MenuItem value="Bourse">Demande de bourse</MenuItem>
                <MenuItem value="Autre">Autre demande</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Motif"
              multiline
              rows={4}
              value={requestForm.motif}
              onChange={(e) => setRequestForm({ ...requestForm, motif: e.target.value })}
              fullWidth
            />
            <Button variant="outlined" component="label" fullWidth>
              {requestForm.piece_jointe ? requestForm.piece_jointe.name : "Joindre un fichier (optionnel)"}
              <input
                type="file"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) setRequestForm({ ...requestForm, piece_jointe: file });
                }}
              />
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRequestModalOpen(false)}>Annuler</Button>
          <Button
            variant="contained"
            onClick={async () => {
              if (!requestForm.type_demande || !requestForm.motif) {
                toast.error("Veuillez remplir tous les champs obligatoires.");
                return;
              }
              setSubmittingRequest(true);
              try {
                const formData = new FormData();
                formData.append("type_demande", requestForm.type_demande);
                formData.append("motif", requestForm.motif);
                if (requestForm.piece_jointe) {
                  formData.append("piece_jointe", requestForm.piece_jointe);
                }
                await api.post("/api/requests/", formData, {
                  headers: { "Content-Type": "multipart/form-data" },
                });
                toast.success("Demande soumise avec succès.");
                setRequestModalOpen(false);
                setRequestForm({ type_demande: "", motif: "", piece_jointe: null });
              } catch (err: any) {
                toast.error(err.response?.data?.detail || "Erreur lors de la soumission.");
              } finally {
                setSubmittingRequest(false);
              }
            }}
            disabled={submittingRequest}
          >
            {submittingRequest ? "Envoi..." : "Soumettre"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

// Composants pour USER_STUDENT
const StudentBalanceCard: React.FC = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [balance, setBalance] = React.useState<number | null>(null);
  const [financeStatus, setFinanceStatus] = React.useState<string>("");
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!token || !user) return;
    const fetchBalance = async () => {
      try {
        // Récupérer le profil étudiant
        const response = await api.get("/api/students/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const students = Array.isArray(response.data) ? response.data : response.data?.results || [];
        if (students.length > 0) {
          const student = students[0];
          setBalance(student.solde || 0);
          setFinanceStatus(student.finance_status || "OK");
        }
      } catch (err) {
        console.error("Erreur chargement solde:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchBalance();
  }, [token, user]);

  if (loading) {
    return <CircularProgress />;
  }

  const balanceColor = balance !== null && balance <= 0 ? "success.main" : "error.main";
  const balanceText = balance !== null && balance <= 0 ? "Couvert" : `${Math.abs(balance || 0).toLocaleString("fr-FR")} FCFA`;

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="body1">Solde actuel</Typography>
        <Typography variant="h5" sx={{ color: balanceColor, fontWeight: "bold" }}>
          {balanceText}
        </Typography>
      </Box>
      <Chip
        label={financeStatus}
        color={financeStatus === "OK" ? "success" : financeStatus === "Moratoire" ? "warning" : "error"}
        size="small"
        sx={{ mb: 2 }}
      />
      <Button
        variant="outlined"
        fullWidth
        onClick={() => navigate("/students")}
      >
        Voir factures & reçus
      </Button>
    </Box>
  );
};

const StudentRegistrationsCard: React.FC = () => {
  const { user, token } = useAuth();
  const [registrations, setRegistrations] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!token || !user) return;
    const fetchRegistrations = async () => {
      try {
        const response = await api.get("/api/students/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const students = Array.isArray(response.data) ? response.data : response.data?.results || [];
        if (students.length > 0) {
          const student = students[0];
          const detailResponse = await api.get(`/api/students/${student.id}/`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          setRegistrations(detailResponse.data.registrations || []);
        }
      } catch (err) {
        console.error("Erreur chargement inscriptions:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchRegistrations();
  }, [token, user]);

  if (loading) {
    return <CircularProgress />;
  }

  if (registrations.length === 0) {
    return <Alert severity="info">Aucune inscription trouvée.</Alert>;
  }

  return (
    <Box>
      {registrations.map((reg, idx) => (
        <Box key={idx} sx={{ mb: 2, p: 1, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="body2" fontWeight="bold">
            {reg.academic_year?.code || reg.academic_year || "N/A"}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Niveau: {reg.level || "N/A"}
          </Typography>
          <Chip
            label={reg.finance_status || "OK"}
            size="small"
            color={reg.finance_status === "OK" ? "success" : "warning"}
            sx={{ mt: 1 }}
          />
        </Box>
      ))}
    </Box>
  );
};

const StudentBoursesMoratoiresCard: React.FC = () => {
  const { user, token } = useAuth();
  const [bourses, setBourses] = React.useState<Bourse[]>([]);
  const [moratoires, setMoratoires] = React.useState<Moratoire[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!token || !user) return;
    const fetchData = async () => {
      try {
        // Récupérer les bourses
        const boursesRes = await api.get("/api/bourses/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const boursesData = Array.isArray(boursesRes.data) ? boursesRes.data : boursesRes.data?.results || [];
        setBourses(boursesData.filter((b: Bourse) => b.statut !== "Terminee"));

        // Récupérer les moratoires
        const moratoiresRes = await api.get("/api/moratoires/", {
          headers: { Authorization: `Bearer ${token}` },
        });
        const moratoiresData = Array.isArray(moratoiresRes.data) ? moratoiresRes.data : moratoiresRes.data?.results || [];
        setMoratoires(moratoiresData.filter((m: Moratoire) => m.statut === "Actif"));
      } catch (err) {
        console.error("Erreur chargement bourses/moratoires:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token, user]);

  if (loading) {
    return <CircularProgress />;
  }

  return (
    <Box>
      {bourses.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Bourses actives
          </Typography>
          {bourses.map((b, idx) => (
            <Box key={idx} sx={{ mb: 1, p: 1, bgcolor: "action.hover", borderRadius: 1 }}>
              <Typography variant="body2">{b.type_bourse}</Typography>
              <Typography variant="body2" color="text.secondary">
                {b.montant.toLocaleString("fr-FR")} FCFA
              </Typography>
            </Box>
          ))}
        </Box>
      )}
      {moratoires.length > 0 && (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Moratoires actifs
          </Typography>
          {moratoires.map((m, idx) => (
            <Box key={idx} sx={{ mb: 1, p: 1, bgcolor: "action.hover", borderRadius: 1 }}>
              <Typography variant="body2">{m.montant_reporte.toLocaleString("fr-FR")} FCFA</Typography>
              <Typography variant="body2" color="text.secondary">
                Jusqu'au {new Date(m.date_fin).toLocaleDateString("fr-FR")}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
      {bourses.length === 0 && moratoires.length === 0 && (
        <Alert severity="info">Aucune bourse ou moratoire actif.</Alert>
      )}
    </Box>
  );
};

export default Dashboard;
