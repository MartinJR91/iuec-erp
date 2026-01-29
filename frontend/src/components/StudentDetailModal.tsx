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
} from "@mui/material";

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
  const [loading, setLoading] = React.useState(false);
  const [student, setStudent] = React.useState<StudentDetail | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open || !studentId) {
      return;
    }
    const fetchStudent = async () => {
      setLoading(true);
      setError(null);
      try {
        const api = (await import("../services/api")).default;
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
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fermer</Button>
      </DialogActions>
    </Dialog>
  );
};

export default StudentDetailModal;
