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

import { useRole } from "../context/RoleContext";

const ROLE_LABELS: Record<string, string> = {
  RECTEUR: "Recteur",
  DAF: "DAF",
  SG: "SG",
  ADMIN_SI: "Admin SI",
  USER_TEACHER: "Enseignant",
  ENSEIGNANT: "Enseignant",
  OPERATOR_FINANCE: "Opérateur Finance",
};

const RoleSwitcher: React.FC = () => {
  const { roles, activeRole, setActiveRole } = useRole();
  const [loading, setLoading] = useState(false);

  const handleChange = async (event: SelectChangeEvent<string>) => {
    const role = event.target.value as typeof activeRole;
    setLoading(true);
    await setActiveRole(role);
    setLoading(false);
  };

  if (roles.length <= 1) {
    return <Chip label={ROLE_LABELS[activeRole] ?? activeRole} color="secondary" />;
  }

  return (
    <FormControl size="small" sx={{ minWidth: 180, bgcolor: "white", borderRadius: 1 }}>
      <InputLabel id="role-switcher-label">Rôle actif</InputLabel>
      <Select
        labelId="role-switcher-label"
        value={activeRole}
        label="Rôle actif"
        onChange={handleChange}
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
  const { activeRole } = useRole();

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
