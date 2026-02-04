import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Alert,
} from "@mui/material";
import { AttachFile } from "@mui/icons-material";
import toast from "react-hot-toast";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";

interface DemandeModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const DemandeModal: React.FC<DemandeModalProps> = ({ open, onClose, onSuccess }) => {
  const { token, activeRole } = useAuth();
  const [submitting, setSubmitting] = React.useState(false);
  const [formData, setFormData] = React.useState({
    type_demande: "",
    motif: "",
    piece_jointe: null as File | null,
  });
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const handleClose = () => {
    if (!submitting) {
      setFormData({ type_demande: "", motif: "", piece_jointe: null });
      setErrors({});
      onClose();
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.type_demande) {
      newErrors.type_demande = "Le type de demande est requis";
    }

    if (!formData.motif || formData.motif.trim().length < 10) {
      newErrors.motif = "Le motif doit contenir au moins 10 caractères";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      toast.error("Veuillez corriger les erreurs dans le formulaire");
      return;
    }

    if (activeRole !== "USER_STUDENT") {
      toast.error("Seuls les étudiants peuvent soumettre des demandes");
      return;
    }

    setSubmitting(true);
    try {
      const formDataToSend = new FormData();
      formDataToSend.append("type_demande", formData.type_demande);
      formDataToSend.append("motif", formData.motif);
      if (formData.piece_jointe) {
        formDataToSend.append("piece_jointe", formData.piece_jointe);
      }

      await api.post("/api/demandes/", formDataToSend, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
      });

      toast.success("Demande envoyée ! Vous serez notifié du traitement");
      setFormData({ type_demande: "", motif: "", piece_jointe: null });
      setErrors({});
      handleClose();
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.response?.data?.motif?.[0] ||
        err.response?.data?.type_demande?.[0] ||
        "Erreur lors de l'envoi de la demande";
      toast.error(errorMsg);
      console.error("Erreur soumission demande:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Soumettre une demande administrative</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mt: 2 }}>
          <FormControl fullWidth error={!!errors.type_demande}>
            <InputLabel>Type de demande *</InputLabel>
            <Select
              value={formData.type_demande}
              onChange={(e) => {
                setFormData({ ...formData, type_demande: e.target.value });
                setErrors({ ...errors, type_demande: "" });
              }}
              label="Type de demande *"
            >
              <MenuItem value="Releve_notes">Relevé de notes</MenuItem>
              <MenuItem value="Certificat_scolarite">Certificat de scolarité</MenuItem>
              <MenuItem value="Attestation_reussite">Attestation de réussite</MenuItem>
              <MenuItem value="Autre">Autre (préciser)</MenuItem>
            </Select>
            {errors.type_demande && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                {errors.type_demande}
              </Typography>
            )}
          </FormControl>

          <TextField
            label="Motif *"
            multiline
            rows={4}
            value={formData.motif}
            onChange={(e) => {
              setFormData({ ...formData, motif: e.target.value });
              setErrors({ ...errors, motif: "" });
            }}
            error={!!errors.motif}
            helperText={errors.motif || "Décrivez votre demande en détail (minimum 10 caractères)"}
            fullWidth
          />

          <Box>
            <Button
              variant="outlined"
              component="label"
              startIcon={<AttachFile />}
              fullWidth
              sx={{ mb: 1 }}
            >
              {formData.piece_jointe ? formData.piece_jointe.name : "Joindre un fichier (optionnel)"}
              <input
                type="file"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    // Vérifier la taille (max 10MB)
                    if (file.size > 10 * 1024 * 1024) {
                      toast.error("Le fichier ne doit pas dépasser 10MB");
                      return;
                    }
                    setFormData({ ...formData, piece_jointe: file });
                  }
                }}
              />
            </Button>
            {formData.piece_jointe && (
              <Typography variant="caption" color="text.secondary">
                Fichier sélectionné : {formData.piece_jointe.name} ({(formData.piece_jointe.size / 1024).toFixed(2)} KB)
              </Typography>
            )}
          </Box>

          <Alert severity="info">
            Votre demande sera traitée par l'administration. Vous recevrez une notification une fois le traitement terminé.
          </Alert>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          Annuler
        </Button>
        <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
          {submitting ? "Envoi..." : "Envoyer"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DemandeModal;
