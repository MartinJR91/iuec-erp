import React, { useState } from "react";
import {
  Box,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Stack,
  Typography,
} from "@mui/material";
import toast from "react-hot-toast";

import { useAuth, UserRole } from "../context/AuthContext";
import api from "../services/api";

const ROLE_LABELS: Record<string, string> = {
  RECTEUR: "Recteur",
  DAF: "DAF",
  SG: "SG",
  ADMIN_SI: "Admin SI",
  USER_TEACHER: "Enseignant",
  ENSEIGNANT: "Enseignant",
  OPERATOR_FINANCE: "Opérateur Finance",
  VALIDATOR_ACAD: "Validateur Acad.",
  DOYEN: "Doyen",
};

const RoleSwitcher: React.FC = () => {
  const { roles, activeRole, setActiveRole, token } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleChange = async (event: SelectChangeEvent<string>) => {
    const role = event.target.value as UserRole;
    setLoading(true);
    
    try {
      // Mettre à jour le rôle actif dans le contexte
      setActiveRole(role);
      
      // Régénérer le token avec le nouveau rôle actif
      if (token) {
        try {
          const response = await api.post<{ token: string; access: string }>("/api/auth/regenerate-token/", { role_active: role });
          if (response.data?.token || response.data?.access) {
            const newToken = response.data.token || response.data.access;
            localStorage.setItem("token", newToken);
            toast.success(`Rôle changé vers ${ROLE_LABELS[role] || role}`);
            // Recharger la page pour mettre à jour le token dans AuthContext
            window.location.reload();
          }
        } catch (error) {
          // Si l'endpoint échoue, on continue avec le rôle mis à jour localement
          console.warn("Impossible de régénérer le token:", error);
          toast.success(`Rôle changé vers ${ROLE_LABELS[role] || role}`);
        }
      } else {
        toast.success(`Rôle changé vers ${ROLE_LABELS[role] || role}`);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!activeRole || roles.length <= 1) {
    const roleToDisplay = activeRole || "ADMIN_SI";
    return <Chip label={ROLE_LABELS[roleToDisplay] ?? roleToDisplay} color="secondary" />;
  }

  return (
    <FormControl size="small" sx={{ minWidth: 180, bgcolor: "white", borderRadius: 1 }}>
      <InputLabel id="role-switcher-label">Rôle actif</InputLabel>
      <Select
        labelId="role-switcher-label"
        value={activeRole || ""}
        label="Rôle actif"
        onChange={handleChange}
        disabled={loading}
      >
        {roles.map((role) => (
          <MenuItem key={role} value={role}>
            {ROLE_LABELS[role] ?? role}
          </MenuItem>
        ))}
      </Select>
      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 1 }}>
          <CircularProgress size={18} />
        </Box>
      )}
    </FormControl>
  );
};

export const RoleDashboardHint: React.FC = () => {
  const { activeRole } = useAuth();

  if (activeRole === "RECTEUR") {
    return (
      <Stack spacing={1}>
        <Typography variant="h6">KPI institutionnels</Typography>
        <Typography variant="body2">Effectifs, taux de réussite, budget global.</Typography>
      </Stack>
    );
  }

  if (activeRole === "ENSEIGNANT" || activeRole === "USER_TEACHER") {
    return (
      <Stack spacing={1}>
        <Typography variant="h6">Mes cours</Typography>
        <Typography variant="body2">Classes assignées, évaluations, notes à saisir.</Typography>
      </Stack>
    );
  }

  return (
    <Stack spacing={1}>
      <Typography variant="h6">Tableau de bord</Typography>
      <Typography variant="body2">Vue personnalisée selon votre rôle.</Typography>
    </Stack>
  );
};

export default RoleSwitcher;
