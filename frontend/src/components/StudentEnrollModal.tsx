import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Alert,
  CircularProgress,
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Divider,
  Chip,
} from "@mui/material";
import toast from "react-hot-toast";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";
import {
  FraisOptionsResponse,
  ProgramOption,
  SpecialitesOptionsResponse,
} from "../types/frais";

interface StudentEnrollModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const FACULTES = [
  { code: "FST", name: "Faculté des Sciences et Techniques" },
  { code: "FASE", name: "Faculté d'Agronomie et Sciences de l'Environnement" },
  { code: "FSE", name: "Faculté des Sciences Économiques" },
  { code: "BTS", name: "Brevet de Technicien Supérieur" },
  { code: "Capacite_Droit", name: "Capacité en Droit" },
];

const StudentEnrollModal: React.FC<StudentEnrollModalProps> = ({
  open,
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingNiveaux, setLoadingNiveaux] = useState(false);
  const [loadingSpecialites, setLoadingSpecialites] = useState(false);
  const [loadingFrais, setLoadingFrais] = useState(false);

  const [niveaux, setNiveaux] = useState<string[]>([]);
  const [specialites, setSpecialites] = useState<SpecialitesOptionsResponse["specialites"]>([]);
  const [fraisData, setFraisData] = useState<FraisOptionsResponse | null>(null);

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    date_naissance: "",
    sexe: "",
    faculte: "",
    niveau: "",
    specialite: "",
    program_id: "",
    academic_year: "2024-2025",
    level: "L1",
    finance_status: "OK",
  });

  // Reset form quand le modal s'ouvre
  useEffect(() => {
    if (open) {
      setFormData({
        first_name: "",
        last_name: "",
        email: "",
        phone: "",
        date_naissance: "",
        sexe: "",
        faculte: "",
        niveau: "",
        specialite: "",
        program_id: "",
        academic_year: "2024-2025",
        level: "L1",
        finance_status: "OK",
      });
      setNiveaux([]);
      setSpecialites([]);
      setFraisData(null);
    }
  }, [open]);

  // Fetch niveaux quand faculté change
  useEffect(() => {
    if (formData.faculte) {
      setLoadingNiveaux(true);
      api
        .get<ProgramOption>("/api/programs-options/", {
          params: { faculte: formData.faculte },
        })
        .then((res) => {
          setNiveaux(res.data.niveaux);
          // Reset niveau et spécialité
          setFormData((prev) => ({ ...prev, niveau: "", specialite: "", program_id: "" }));
          setSpecialites([]);
          setFraisData(null);
        })
        .catch((err) => {
          toast.error(err.response?.data?.detail || "Erreur lors du chargement des niveaux");
        })
        .finally(() => {
          setLoadingNiveaux(false);
        });
    }
  }, [formData.faculte]);

  // Fetch spécialités quand niveau change
  useEffect(() => {
    if (formData.faculte && formData.niveau) {
      setLoadingSpecialites(true);
      api
        .get<SpecialitesOptionsResponse>("/api/specialites-options/", {
          params: {
            faculte: formData.faculte,
            niveau: formData.niveau,
          },
        })
        .then((res) => {
          setSpecialites(res.data.specialites);
          // Reset spécialité
          setFormData((prev) => ({ ...prev, specialite: "", program_id: "" }));
          setFraisData(null);
        })
        .catch((err) => {
          toast.error(err.response?.data?.detail || "Erreur lors du chargement des spécialités");
        })
        .finally(() => {
          setLoadingSpecialites(false);
        });
    }
  }, [formData.faculte, formData.niveau]);

  // Fetch frais quand spécialité change
  useEffect(() => {
    if (formData.faculte && formData.niveau && formData.specialite) {
      setLoadingFrais(true);
      const selectedSpecialite = specialites.find((s) => s.key === formData.specialite);
      if (selectedSpecialite) {
        setFormData((prev) => ({ ...prev, program_id: selectedSpecialite.program_id }));
      }

      api
        .get<FraisOptionsResponse>("/api/frais-options/", {
          params: {
            faculte: formData.faculte,
            niveau: formData.niveau,
            specialite: formData.specialite,
            academic_year: formData.academic_year,
          },
        })
        .then((res) => {
          setFraisData(res.data);
        })
        .catch((err) => {
          toast.error(err.response?.data?.detail || "Erreur lors du chargement des frais");
          setFraisData(null);
        })
        .finally(() => {
          setLoadingFrais(false);
        });
    }
  }, [formData.faculte, formData.niveau, formData.specialite, formData.academic_year, specialites]);

  const handleSubmit = async () => {
    // Validation des champs requis
    if (!formData.first_name || !formData.last_name || !formData.email || !formData.phone) {
      toast.error("Veuillez remplir tous les champs obligatoires (nom, prénom, email, téléphone)");
      return;
    }
    if (!formData.faculte || !formData.niveau || !formData.specialite || !formData.program_id) {
      toast.error("Veuillez sélectionner une faculté, un niveau et une spécialité");
      return;
    }

    // Validation format email basique
    if (!formData.email.includes("@")) {
      toast.error("Format d'email invalide");
      return;
    }

    setLoading(true);
    try {
      const payload: any = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim().toLowerCase(),
        phone: formData.phone.trim(),
        program_id: formData.program_id,
        academic_year_id: "1", // TODO: Récupérer depuis l'API
        level: formData.level,
        finance_status: formData.finance_status,
      };

      // Ajouter les champs optionnels s'ils sont remplis
      if (formData.date_naissance) {
        payload.date_naissance = formData.date_naissance;
      }
      if (formData.sexe) {
        payload.sexe = formData.sexe;
      }

      const response = await api.post("/api/students/", payload);
      const matricule = response.data.matricule || "N/A";
      const totalFrais = fraisData?.total_estime || 0;
      const totalFraisFormatted = new Intl.NumberFormat("fr-FR", {
        style: "currency",
        currency: "XAF",
        minimumFractionDigits: 0,
      }).format(totalFrais);

      toast.success(
        `Étudiant ${formData.first_name} ${formData.last_name} inscrit ! Matricule: ${matricule} | Frais totaux: ${totalFraisFormatted} (détails)`,
        { duration: 6000 }
      );
      onSuccess?.();
      onClose();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Erreur lors de l'inscription";
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "XAF",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Inscrire un étudiant</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 2 }}>
          <Alert severity="info">
            Le matricule sera généré automatiquement. Si l'identité existe déjà (email ou téléphone), elle sera réutilisée.
          </Alert>

          <Grid container spacing={2}>
            {/* Informations personnelles */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Informations personnelles
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Prénom *"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                required
                fullWidth
                placeholder="Ex: Jean"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Nom *"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                required
                fullWidth
                placeholder="Ex: Dupont"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Email *"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                fullWidth
                placeholder="Ex: jean.dupont@example.com"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Téléphone *"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                required
                fullWidth
                placeholder="Ex: +237 6XX XXX XXX"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Date de naissance"
                type="date"
                value={formData.date_naissance}
                onChange={(e) => setFormData({ ...formData, date_naissance: e.target.value })}
                fullWidth
                InputLabelProps={{
                  shrink: true,
                }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Sexe"
                value={formData.sexe}
                onChange={(e) => setFormData({ ...formData, sexe: e.target.value })}
                fullWidth
              >
                <MenuItem value="">Non spécifié</MenuItem>
                <MenuItem value="M">Masculin</MenuItem>
                <MenuItem value="F">Féminin</MenuItem>
              </TextField>
            </Grid>

            {/* Sélection académique */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" gutterBottom>
                Sélection académique
              </Typography>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                select
                label="Faculté *"
                value={formData.faculte}
                onChange={(e) => setFormData({ ...formData, faculte: e.target.value })}
                required
                fullWidth
              >
                {FACULTES.map((fac) => (
                  <MenuItem key={fac.code} value={fac.code}>
                    {fac.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                select
                label="Niveau *"
                value={formData.niveau}
                onChange={(e) => setFormData({ ...formData, niveau: e.target.value })}
                required
                fullWidth
                disabled={!formData.faculte || loadingNiveaux}
              >
                {loadingNiveaux ? (
                  <MenuItem disabled>
                    <CircularProgress size={20} />
                  </MenuItem>
                ) : (
                  niveaux.map((niveau) => (
                    <MenuItem key={niveau} value={niveau}>
                      {niveau}
                    </MenuItem>
                  ))
                )}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                select
                label="Spécialité *"
                value={formData.specialite}
                onChange={(e) => setFormData({ ...formData, specialite: e.target.value })}
                required
                fullWidth
                disabled={!formData.niveau || loadingSpecialites}
              >
                {loadingSpecialites ? (
                  <MenuItem disabled>
                    <CircularProgress size={20} />
                  </MenuItem>
                ) : (
                  specialites.map((spec) => (
                    <MenuItem key={spec.key} value={spec.key}>
                      {spec.name}
                    </MenuItem>
                  ))
                )}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Niveau d'entrée *"
                value={formData.level}
                onChange={(e) => setFormData({ ...formData, level: e.target.value })}
                required
                fullWidth
              >
                <MenuItem value="L1">L1</MenuItem>
                <MenuItem value="L2">L2</MenuItem>
                <MenuItem value="L3">L3</MenuItem>
                <MenuItem value="M1">M1</MenuItem>
                <MenuItem value="M2">M2</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Statut financier initial *"
                value={formData.finance_status}
                onChange={(e) => setFormData({ ...formData, finance_status: e.target.value })}
                required
                fullWidth
              >
                <MenuItem value="OK">OK</MenuItem>
                <MenuItem value="Moratoire">Moratoire</MenuItem>
              </TextField>
            </Grid>

            {/* Affichage des frais */}
            {fraisData && (
              <Grid item xs={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Frais estimés
                </Typography>
                <Card variant="outlined">
                  <CardContent>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Frais d'inscription
                        </Typography>
                        <Typography variant="body2">
                          IUEC: {formatCurrency(fraisData.frais.inscription.iuec)}
                        </Typography>
                        <Typography variant="body2">
                          Tutelle: {formatCurrency(fraisData.frais.inscription.tutelle)}
                        </Typography>
                        <Typography variant="body1" fontWeight="bold" sx={{ mt: 1 }}>
                          Total: {formatCurrency(fraisData.frais.inscription.total)}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="subtitle2" color="text.secondary">
                          Frais de scolarité
                        </Typography>
                        {fraisData.frais.scolarite.echeances && fraisData.frais.scolarite.echeances.length > 0 ? (
                          <>
                            <Typography variant="body2">
                              Tranche 1: {formatCurrency(fraisData.frais.scolarite.tranche1)} 
                              {fraisData.frais.scolarite.echeances[0] && (
                                <Chip 
                                  label={`Due le ${new Date(fraisData.frais.scolarite.echeances[0]).toLocaleDateString("fr-FR")}`}
                                  size="small"
                                  color="primary"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </Typography>
                            <Typography variant="body2">
                              Tranche 2: {formatCurrency(fraisData.frais.scolarite.tranche2)}
                              {fraisData.frais.scolarite.echeances[1] && (
                                <Chip 
                                  label={`Due le ${new Date(fraisData.frais.scolarite.echeances[1]).toLocaleDateString("fr-FR")}`}
                                  size="small"
                                  color="primary"
                                  sx={{ ml: 1 }}
                                />
                              )}
                            </Typography>
                            {fraisData.frais.scolarite.tranche3 && fraisData.frais.scolarite.echeances[2] && (
                              <Typography variant="body2">
                                Tranche 3: {formatCurrency(fraisData.frais.scolarite.tranche3)}
                                <Chip 
                                  label={`Due le ${new Date(fraisData.frais.scolarite.echeances[2]).toLocaleDateString("fr-FR")}`}
                                  size="small"
                                  color="primary"
                                  sx={{ ml: 1 }}
                                />
                              </Typography>
                            )}
                          </>
                        ) : (
                          <>
                            <Typography variant="body2">
                              Tranche 1: {formatCurrency(fraisData.frais.scolarite.tranche1)}
                            </Typography>
                            <Typography variant="body2">
                              Tranche 2: {formatCurrency(fraisData.frais.scolarite.tranche2)}
                            </Typography>
                            {fraisData.frais.scolarite.tranche3 && (
                              <Typography variant="body2">
                                Tranche 3: {formatCurrency(fraisData.frais.scolarite.tranche3)}
                              </Typography>
                            )}
                          </>
                        )}
                        <Typography variant="body1" fontWeight="bold" sx={{ mt: 1 }}>
                          Total: {formatCurrency(fraisData.frais.scolarite.total)}
                        </Typography>
                      </Grid>
                      {Object.keys(fraisData.frais.autres).length > 0 && (
                        <Grid item xs={12}>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            Autres frais
                          </Typography>
                          {Object.entries(fraisData.frais.autres).map(([key, value]) => (
                            <Chip
                              key={key}
                              label={`${key}: ${formatCurrency(typeof value === "number" ? value : parseFloat(value as string) || 0)}`}
                              size="small"
                              sx={{ mr: 1, mb: 1 }}
                            />
                          ))}
                        </Grid>
                      )}
                      <Grid item xs={12}>
                        <Divider sx={{ my: 1 }} />
                        <Typography variant="h6" color="primary" fontWeight="bold">
                          Total estimé: {formatCurrency(fraisData.total_estime)}
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            )}
            {loadingFrais && (
              <Grid item xs={12}>
                <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              </Grid>
            )}
          </Grid>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Annuler
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {loading ? <CircularProgress size={20} /> : "Inscrire"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default StudentEnrollModal;
