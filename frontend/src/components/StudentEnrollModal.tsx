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
} from "@mui/material";
import toast from "react-hot-toast";
import axios from "axios";

import { useAuth } from "../context/AuthContext";

interface StudentEnrollModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface Program {
  id: string;
  code: string;
  name: string;
}

const StudentEnrollModal: React.FC<StudentEnrollModalProps> = ({ open, onClose, onSuccess }) => {
  const { token, activeRole } = useAuth();
  const [loading, setLoading] = useState(false);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [formData, setFormData] = useState({
    matricule_permanent: "",
    program_id: "",
    academic_year_id: "",
    level: "L1",
    finance_status: "OK",
  });

  useEffect(() => {
    if (open) {
      // Charger les programmes
      const fetchData = async () => {
        try {
          const programsRes = await axios.get("/api/programs/", {
            headers: {
              Authorization: `Bearer ${token}`,
              "X-Role-Active": activeRole,
            },
          });
          setPrograms(Array.isArray(programsRes.data) ? programsRes.data : programsRes.data.results || []);
          // Utiliser l'année académique active par défaut (2025-2026)
          // TODO: Récupérer depuis l'API si un endpoint existe
          setFormData((prev) => ({ ...prev, academic_year_id: "1" }));
        } catch (err) {
          toast.error("Erreur lors du chargement des programmes");
        }
      };
      fetchData();
    }
  }, [open, token, activeRole]);

  const handleSubmit = async () => {
    if (!formData.matricule_permanent || !formData.program_id || !formData.academic_year_id) {
      toast.error("Veuillez remplir tous les champs obligatoires");
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        "/api/students/",
        {
          matricule_permanent: formData.matricule_permanent,
          program_id: formData.program_id,
          academic_year_id: formData.academic_year_id,
          level: formData.level,
          finance_status: formData.finance_status,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Role-Active": activeRole,
          },
        }
      );
      toast.success("Étudiant inscrit avec succès");
      onSuccess?.();
      onClose();
      // Reset form
      setFormData({
        matricule_permanent: "",
        program_id: "",
        academic_year_id: "",
        level: "L1",
        finance_status: "OK",
      });
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Erreur lors de l'inscription";
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Inscrire un étudiant</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 2 }}>
          <TextField
            label="Matricule permanent"
            value={formData.matricule_permanent}
            onChange={(e) => setFormData({ ...formData, matricule_permanent: e.target.value })}
            required
            fullWidth
            placeholder="Ex: 25B001UE"
          />
          <TextField
            select
            label="Programme"
            value={formData.program_id}
            onChange={(e) => setFormData({ ...formData, program_id: e.target.value })}
            required
            fullWidth
          >
            {programs.map((program) => (
              <MenuItem key={program.id} value={program.id}>
                {program.code} - {program.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label="Niveau"
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
          <TextField
            select
            label="Statut financier initial"
            value={formData.finance_status}
            onChange={(e) => setFormData({ ...formData, finance_status: e.target.value })}
            required
            fullWidth
          >
            <MenuItem value="OK">OK</MenuItem>
            <MenuItem value="Moratoire">Moratoire</MenuItem>
          </TextField>
          <Alert severity="info">
            L'identité de l'étudiant doit déjà exister dans le système. Le matricule doit être unique.
          </Alert>
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
