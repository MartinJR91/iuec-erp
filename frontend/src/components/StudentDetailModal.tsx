import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Divider,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  CircularProgress,
  TextField,
  MenuItem,
  DialogContentText,
} from "@mui/material";
import { CheckCircle, Warning, Error, Add } from "@mui/icons-material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import toast from "react-hot-toast";
import api from "../services/api";
import { Bourse, BoursesActivesResponse, EcheanceResponse, Moratoire } from "../types/frais";
import { useAuth } from "../context/AuthContext";

interface StudentDetail {
  id: string;
  identity_nested?: {
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
  };
  email?: string;
  matricule_permanent: string;
  date_entree: string;
  current_program?: {
    id: number;
    code: string;
    name: string;
  };
  program_code?: string;
  program_name?: string;
  faculty_code?: string;
  finance_status: string;
  finance_status_effective?: string;
  academic_status?: string;
  balance: number;
  registrations_admin?: Array<{
    id: number;
    academic_year: { code: string; label: string } | string;
    level: string;
    finance_status: string;
    registration_date: string;
  }>;
}

interface StudentDetailModalProps {
  open: boolean;
  onClose: () => void;
  studentId: string | null;
}

const StudentDetailModal: React.FC<StudentDetailModalProps> = ({ open, onClose, studentId }) => {
  const { activeRole } = useAuth();
  const [loading, setLoading] = React.useState(false);
  const [student, setStudent] = React.useState<StudentDetail | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [echeances, setEcheances] = React.useState<EcheanceResponse | null>(null);
  const [loadingEcheances, setLoadingEcheances] = React.useState(false);
  const [moratoires, setMoratoires] = React.useState<Moratoire[]>([]);
  const [loadingMoratoires, setLoadingMoratoires] = React.useState(false);
  const [moratoireModalOpen, setMoratoireModalOpen] = React.useState(false);
  const [moratoireForm, setMoratoireForm] = React.useState({
    montant_reporte: "",
    duree_jours: 30,
    motif: "",
  });
  const [submittingMoratoire, setSubmittingMoratoire] = React.useState(false);
  const [bourses, setBourses] = React.useState<Bourse[]>([]);
  const [loadingBourses, setLoadingBourses] = React.useState(false);
  const [bourseModalOpen, setBourseModalOpen] = React.useState(false);
  const [bourseForm, setBourseForm] = React.useState({
    type_bourse: "Merite" as Bourse["type_bourse"],
    montant: "",
    pourcentage: "",
    annee_academique: "",
    date_fin_validite: null as Date | null,
    motif: "",
  });
  const [submittingBourse, setSubmittingBourse] = React.useState(false);
  const [academicYears, setAcademicYears] = React.useState<Array<{ id: number; code: string; label: string }>>([]);

  React.useEffect(() => {
    if (!open || !studentId) {
      return;
    }
    const fetchStudent = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get(`/api/students/${studentId}/`);
        setStudent(response.data.student || response.data);
      } catch (err) {
        setError("Impossible de charger les détails de l'étudiant.");
      } finally {
        setLoading(false);
      }
    };
    fetchStudent();
  }, [open, studentId]);

  React.useEffect(() => {
    if (!open || !studentId) {
      return;
    }
    const fetchEcheances = async () => {
      setLoadingEcheances(true);
      try {
        const response = await api.get<EcheanceResponse>(`/api/students/${studentId}/echeances/`);
        setEcheances(response.data);
      } catch (err) {
        // Ignorer les erreurs silencieusement
        setEcheances(null);
      } finally {
        setLoadingEcheances(false);
      }
    };
    fetchEcheances();
  }, [open, studentId]);

  React.useEffect(() => {
    if (!open || !studentId) {
      return;
    }
    const fetchMoratoires = async () => {
      setLoadingMoratoires(true);
      try {
        const response = await api.get<{ moratoires: Moratoire[] }>(`/api/students/${studentId}/moratoires-actifs/`);
        setMoratoires(response.data.moratoires || []);
        
        // Alertes pour moratoires proches de l'échéance
        const today = new Date();
        const in7Days = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
        
        response.data.moratoires?.forEach((moratoire) => {
          if (moratoire.statut === "Actif") {
            const dateFin = new Date(moratoire.date_fin);
            if (dateFin < today) {
              toast.error(
                `Moratoire dépassé pour ${moratoire.student_matricule}. Date de fin: ${dateFin.toLocaleDateString("fr-FR")}`,
                { duration: 8000 }
              );
            } else if (dateFin <= in7Days) {
              toast(
                `Moratoire se terminant bientôt pour ${moratoire.student_matricule}. Date de fin: ${dateFin.toLocaleDateString("fr-FR")}`,
                { duration: 6000, icon: "⚠️" }
              );
            }
          }
        });
      } catch (err) {
        console.error("Erreur chargement moratoires:", err);
        setMoratoires([]);
      } finally {
        setLoadingMoratoires(false);
      }
    };
    fetchMoratoires();
  }, [open, studentId]);

  React.useEffect(() => {
    if (!open || !studentId) {
      return;
    }
    const fetchBourses = async () => {
      setLoadingBourses(true);
      try {
        const response = await api.get<BoursesActivesResponse>(`/api/students/${studentId}/bourses-actives/`);
        setBourses(response.data.bourses || []);
        
        // Alertes pour bourses proches de fin ou suspendues
        const today = new Date();
        const in30Days = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
        
        response.data.bourses?.forEach((bourse) => {
          if (bourse.statut === "Suspendue") {
            toast(
              `Bourse suspendue pour ${bourse.student_matricule}. Type: ${bourse.type_bourse}`,
              { duration: 6000, icon: "⚠️" }
            );
          } else if (bourse.statut === "Active" && bourse.date_fin_validite) {
            const dateFin = new Date(bourse.date_fin_validite);
            if (dateFin < today) {
              toast.error(
                `Bourse expirée pour ${bourse.student_matricule}. Date de fin: ${dateFin.toLocaleDateString("fr-FR")}`,
                { duration: 8000 }
              );
            } else if (dateFin <= in30Days) {
              toast(
                `Bourse se terminant bientôt pour ${bourse.student_matricule}. Date de fin: ${dateFin.toLocaleDateString("fr-FR")}`,
                { duration: 6000, icon: "⚠️" }
              );
            }
          }
        });
      } catch (err) {
        console.error("Erreur chargement bourses:", err);
        setBourses([]);
      } finally {
        setLoadingBourses(false);
      }
    };
    fetchBourses();
  }, [open, studentId]);

  React.useEffect(() => {
    // Charger les années académiques pour le formulaire
    const fetchAcademicYears = async () => {
      try {
        // Essayer d'abord l'endpoint dédié
        try {
          const response = await api.get("/api/academic-years/");
          setAcademicYears(response.data.results || response.data || []);
        } catch {
          // Fallback: récupérer depuis les inscriptions de l'étudiant
          if (student?.registrations_admin && student.registrations_admin.length > 0) {
            const years = student.registrations_admin
              .map((reg) => {
                const year = typeof reg.academic_year === "object" ? reg.academic_year : null;
                // Vérifier si year a une propriété id, sinon utiliser un id par défaut basé sur l'index
                return year ? { 
                  id: (year as any).id || 0, 
                  code: (year as any).code || "", 
                  label: (year as any).label || "" 
                } : null;
              })
              .filter((y): y is { id: number; code: string; label: string } => y !== null);
            setAcademicYears(years);
          } else {
            // Dernier fallback: année actuelle
            const currentYear = new Date().getFullYear();
            setAcademicYears([
              { id: 1, code: `${currentYear}-${currentYear + 1}`, label: `${currentYear}-${currentYear + 1}` },
            ]);
          }
        }
      } catch (err) {
        console.error("Erreur chargement années académiques:", err);
        // Fallback minimal
        const currentYear = new Date().getFullYear();
        setAcademicYears([
          { id: 1, code: `${currentYear}-${currentYear + 1}`, label: `${currentYear}-${currentYear + 1}` },
        ]);
      }
    };
    if (bourseModalOpen) {
      fetchAcademicYears();
    }
  }, [bourseModalOpen, student]);

  if (!student && !loading && !error) {
    return null;
  }

  const getFinanceStatusColor = (status: string) => {
    switch (status) {
      case "OK":
        return "success";
      case "BLOQUE":
        return "error";
      case "MORATOIRE":
        return "warning";
      default:
        return "default";
    }
  };

  const getAcademicStatusColor = (status?: string) => {
    switch (status) {
      case "ACTIF":
        return "success";
      case "AJOURE":
        return "warning";
      case "EXCLU":
        return "error";
      default:
        return "default";
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Détails de l'étudiant</DialogTitle>
      <DialogContent>
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <Typography>Chargement...</Typography>
          </Box>
        )}
        {error && (
          <Box sx={{ py: 2 }}>
            <Typography color="error">{error}</Typography>
          </Box>
        )}
        {student && (
          <Box>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Nom complet
                </Typography>
                <Typography variant="h6">
                  {student.identity_nested
                    ? `${student.identity_nested.last_name} ${student.identity_nested.first_name}`
                    : "—"}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Matricule
                </Typography>
                <Typography variant="body1">{student.matricule_permanent}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Email
                </Typography>
                <Typography variant="body1">
                  {student.identity_nested?.email || student.email || "—"}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Téléphone
                </Typography>
                <Typography variant="body1">{student.identity_nested?.phone || "—"}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Programme
                </Typography>
                <Typography variant="body1">
                  {student.program_name || student.current_program?.name || "—"} (
                  {student.program_code || student.current_program?.code || "—"})
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Faculté
                </Typography>
                <Typography variant="body1">{student.faculty_code || "—"}</Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Date d'entrée
                </Typography>
                <Typography variant="body1">
                  {new Date(student.date_entree).toLocaleDateString("fr-FR")}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Statut financier
                </Typography>
                <Chip
                  label={student.finance_status_effective || student.finance_status}
                  color={getFinanceStatusColor(student.finance_status_effective || student.finance_status)}
                  size="small"
                />
              </Grid>
              {student.academic_status && (
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Statut académique
                  </Typography>
                  <Chip
                    label={student.academic_status}
                    color={getAcademicStatusColor(student.academic_status)}
                    size="small"
                  />
                </Grid>
              )}
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="text.secondary">
                  Solde
                </Typography>
                <Typography
                  variant="body1"
                  sx={{ fontWeight: "bold", color: student.balance > 0 ? "error.main" : "success.main" }}
                >
                  {Math.abs(student.balance).toLocaleString("fr-FR")} XAF
                </Typography>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              Inscriptions administratives
            </Typography>
            {student.registrations_admin && student.registrations_admin.length > 0 ? (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Année académique</TableCell>
                      <TableCell>Niveau</TableCell>
                      <TableCell>Statut finance</TableCell>
                      <TableCell>Date inscription</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {student.registrations_admin.map((reg) => (
                      <TableRow key={reg.id}>
                        <TableCell>
                          {typeof reg.academic_year === "object"
                            ? reg.academic_year.label
                            : reg.academic_year}
                        </TableCell>
                        <TableCell>{reg.level}</TableCell>
                        <TableCell>
                          <Chip
                            label={reg.finance_status}
                            color={getFinanceStatusColor(reg.finance_status)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          {new Date(reg.registration_date).toLocaleDateString("fr-FR")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Aucune inscription administrative trouvée.
              </Typography>
            )}
            <Divider sx={{ my: 2 }} />
            <Typography variant="h6" gutterBottom>
              Échéancier
            </Typography>
            {loadingEcheances ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                <CircularProgress size={24} />
              </Box>
            ) : echeances ? (
              <Box>
                {echeances.statut && (
                  <Alert
                    severity={
                      echeances.jours_retard > 30
                        ? "error"
                        : echeances.jours_retard > 0
                        ? "warning"
                        : echeances.montant_du > 0
                        ? "info"
                        : "success"
                    }
                    sx={{ mb: 2 }}
                    icon={
                      echeances.jours_retard > 30 ? (
                        <Error />
                      ) : echeances.jours_retard > 0 ? (
                        <Warning />
                      ) : echeances.montant_du > 0 ? (
                        <Warning />
                      ) : (
                        <CheckCircle />
                      )
                    }
                  >
                    <Typography variant="body2" fontWeight="bold">
                      {echeances.statut}
                    </Typography>
                    {echeances.montant_du > 0 && (
                      <Typography variant="body2">
                        Montant dû: {echeances.montant_du.toLocaleString("fr-FR")} FCFA
                      </Typography>
                    )}
                    {echeances.prochaine_echeance && (
                      <Typography variant="body2">
                        Prochaine échéance: {new Date(echeances.prochaine_echeance).toLocaleDateString("fr-FR")}
                      </Typography>
                    )}
                  </Alert>
                )}
                {echeances.tranches && echeances.tranches.length > 0 ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Type</TableCell>
                          <TableCell>Libellé</TableCell>
                          <TableCell align="right">Montant</TableCell>
                          <TableCell>Échéance</TableCell>
                          <TableCell align="center">Statut</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {echeances.tranches.map((tranche, index) => {
                          const echeanceDate = new Date(tranche.echeance);
                          const isOverdue = tranche.due && !tranche.payee && echeanceDate < new Date();
                          const daysUntilDue = Math.ceil(
                            (echeanceDate.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)
                          );
                          const isDueSoon = daysUntilDue <= 7 && daysUntilDue >= 0;

                          return (
                            <TableRow
                              key={index}
                              sx={{
                                backgroundColor: isOverdue
                                  ? "error.light"
                                  : isDueSoon
                                  ? "warning.light"
                                  : tranche.payee
                                  ? "success.light"
                                  : "transparent",
                              }}
                            >
                              <TableCell>
                                <Chip
                                  label={tranche.type}
                                  size="small"
                                  color={
                                    tranche.type === "inscription"
                                      ? "primary"
                                      : tranche.type === "scolarite"
                                      ? "secondary"
                                      : "default"
                                  }
                                />
                              </TableCell>
                              <TableCell>{tranche.label}</TableCell>
                              <TableCell align="right">
                                {tranche.montant_restant !== undefined
                                  ? `${tranche.montant_restant.toLocaleString("fr-FR")} FCFA`
                                  : `${tranche.montant.toLocaleString("fr-FR")} FCFA`}
                              </TableCell>
                              <TableCell>
                                {echeanceDate.toLocaleDateString("fr-FR")}
                                {isDueSoon && !tranche.payee && (
                                  <Chip
                                    label={`Dans ${daysUntilDue} jour(s)`}
                                    size="small"
                                    color="warning"
                                    sx={{ ml: 1 }}
                                  />
                                )}
                                {isOverdue && (
                                  <Chip
                                    label={`En retard de ${Math.abs(daysUntilDue)} jour(s)`}
                                    size="small"
                                    color="error"
                                    sx={{ ml: 1 }}
                                  />
                                )}
                              </TableCell>
                              <TableCell align="center">
                                {tranche.payee ? (
                                  <Chip label="Payée" color="success" size="small" icon={<CheckCircle />} />
                                ) : tranche.due ? (
                                  <Chip label="Due" color="error" size="small" icon={<Error />} />
                                ) : (
                                  <Chip label="À venir" color="default" size="small" />
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Aucune échéance trouvée.
                  </Typography>
                )}
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Impossible de charger les échéances.
              </Typography>
            )}
            <Divider sx={{ my: 2 }} />
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="h6">Bourses</Typography>
              {(activeRole === "SCOLARITE" || activeRole === "RECTEUR" || activeRole === "ADMIN_SI") && (
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<Add />}
                  onClick={() => setBourseModalOpen(true)}
                >
                  Accorder bourse
                </Button>
              )}
            </Box>
            {loadingBourses ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                <CircularProgress size={24} />
              </Box>
            ) : bourses.length > 0 ? (
              <Box sx={{ height: 400, width: "100%" }}>
                <DataGrid
                  rows={bourses}
                  columns={[
                    {
                      field: "type_bourse",
                      headerName: "Type",
                      width: 150,
                      renderCell: (params) => {
                        const typeLabels: Record<string, string> = {
                          Merite: "Mérite",
                          Besoin: "Besoins sociaux",
                          Tutelle: "Tutelle",
                          Externe: "Externe",
                          Interne: "Interne",
                        };
                        return <Chip label={typeLabels[params.value] || params.value} size="small" />;
                      },
                    },
                    {
                      field: "montant",
                      headerName: "Montant",
                      width: 150,
                      valueFormatter: (params) => `${Number(params.value || 0).toLocaleString("fr-FR")} XAF`,
                    },
                    {
                      field: "pourcentage",
                      headerName: "Pourcentage",
                      width: 120,
                      valueFormatter: (params) => (params.value ? `${params.value}%` : "—"),
                    },
                    {
                      field: "date_attribution",
                      headerName: "Date attribution",
                      width: 150,
                      valueFormatter: (params) => new Date(params.value).toLocaleDateString("fr-FR"),
                    },
                    {
                      field: "date_fin_validite",
                      headerName: "Date fin",
                      width: 150,
                      valueFormatter: (params) => (params.value ? new Date(params.value).toLocaleDateString("fr-FR") : "—"),
                    },
                    {
                      field: "statut",
                      headerName: "Statut",
                      width: 120,
                      renderCell: (params) => {
                        const color =
                          params.value === "Active"
                            ? "success"
                            : params.value === "Suspendue"
                              ? "warning"
                              : "error";
                        return <Chip label={params.value} color={color} size="small" />;
                      },
                    },
                    {
                      field: "motif",
                      headerName: "Motif",
                      flex: 1,
                      minWidth: 200,
                    },
                    {
                      field: "accorde_par_email",
                      headerName: "Accordé par",
                      width: 200,
                    },
                  ]}
                  pageSizeOptions={[5, 10]}
                  initialState={{ pagination: { paginationModel: { pageSize: 5 } } }}
                />
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Aucune bourse active trouvée.
              </Typography>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fermer</Button>
      </DialogActions>

      {/* Modal pour accorder une bourse */}
      <Dialog open={bourseModalOpen} onClose={() => setBourseModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Accorder une bourse</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
            <TextField
              select
              label="Type de bourse"
              value={bourseForm.type_bourse}
              onChange={(e) => setBourseForm({ ...bourseForm, type_bourse: e.target.value as Bourse["type_bourse"] })}
              fullWidth
              SelectProps={{ native: false }}
            >
              <MenuItem value="Merite">Mérite académique</MenuItem>
              <MenuItem value="Besoin">Besoins sociaux</MenuItem>
              <MenuItem value="Tutelle">Bourse tutelle/université partenaire</MenuItem>
              <MenuItem value="Externe">Bourse externe (ONG, État, etc.)</MenuItem>
              <MenuItem value="Interne">Bourse IUEC interne</MenuItem>
            </TextField>
            <TextField
              label="Montant (XAF)"
              type="number"
              value={bourseForm.montant}
              onChange={(e) => setBourseForm({ ...bourseForm, montant: e.target.value })}
              fullWidth
              helperText="Ou utilisez le pourcentage ci-dessous"
            />
            <TextField
              label="Pourcentage (%)"
              type="number"
              value={bourseForm.pourcentage}
              onChange={(e) => setBourseForm({ ...bourseForm, pourcentage: e.target.value })}
              fullWidth
              helperText="Pourcentage de réduction (ex: 50 pour 50%)"
              inputProps={{ min: 0, max: 100 }}
            />
            <TextField
              select
              label="Année académique"
              value={bourseForm.annee_academique}
              onChange={(e) => setBourseForm({ ...bourseForm, annee_academique: e.target.value })}
              fullWidth
              required
            >
              {academicYears.map((year) => (
                <MenuItem key={year.id} value={year.id}>
                  {year.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Date de fin de validité"
              type="date"
              value={bourseForm.date_fin_validite ? bourseForm.date_fin_validite.toISOString().split("T")[0] : ""}
              onChange={(e) => setBourseForm({ ...bourseForm, date_fin_validite: e.target.value ? new Date(e.target.value) : null })}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Motif"
              multiline
              rows={3}
              value={bourseForm.motif}
              onChange={(e) => setBourseForm({ ...bourseForm, motif: e.target.value })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBourseModalOpen(false)}>Annuler</Button>
          <Button
            variant="contained"
            onClick={async () => {
              if (!bourseForm.montant && !bourseForm.pourcentage) {
                toast.error("Veuillez fournir un montant ou un pourcentage.");
                return;
              }
              if (!bourseForm.annee_academique) {
                toast.error("Veuillez sélectionner une année académique.");
                return;
              }
              setSubmittingBourse(true);
              try {
                const payload: any = {
                  type_bourse: bourseForm.type_bourse,
                  annee_academique: Number(bourseForm.annee_academique),
                  motif: bourseForm.motif,
                };
                if (bourseForm.montant) {
                  payload.montant = bourseForm.montant;
                }
                if (bourseForm.pourcentage) {
                  payload.pourcentage = bourseForm.pourcentage;
                }
                if (bourseForm.date_fin_validite) {
                  payload.date_fin_validite = bourseForm.date_fin_validite.toISOString().split("T")[0];
                }
                const response = await api.post(`/api/students/${studentId}/bourse/`, payload);
                toast.success("Bourse accordée avec succès.");
                setBourseModalOpen(false);
                setBourseForm({
                  type_bourse: "Merite",
                  montant: "",
                  pourcentage: "",
                  annee_academique: "",
                  date_fin_validite: null,
                  motif: "",
                });
                // Recharger les données
                const studentResponse = await api.get(`/api/students/${studentId}/`);
                setStudent(studentResponse.data.student || studentResponse.data);
                const boursesResponse = await api.get<BoursesActivesResponse>(`/api/students/${studentId}/bourses-actives/`);
                setBourses(boursesResponse.data.bourses || []);
              } catch (err: any) {
                toast.error(err.response?.data?.detail || "Erreur lors de l'attribution de la bourse.");
              } finally {
                setSubmittingBourse(false);
              }
            }}
            disabled={submittingBourse}
          >
            {submittingBourse ? "En cours..." : "Accorder"}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};

export default StudentDetailModal;
