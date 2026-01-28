import React from "react";
import { MenuItem, Select, SelectChangeEvent } from "@mui/material";

import { UserRole, useAuth } from "../context/AuthContext";

const roles: UserRole[] = [
  "RECTEUR",
  "DAF",
  "SG",
  "ADMIN_SI",
  "USER_TEACHER",
  "ENSEIGNANT",
  "OPERATOR_FINANCE",
];

const RoleSelector: React.FC = () => {
  const { activeRole, setActiveRole } = useAuth();

  const handleChange = (event: SelectChangeEvent) => {
    setActiveRole(event.target.value as UserRole);
  };

  return (
    <Select
      value={activeRole || ""}
      onChange={handleChange}
      size="small"
      sx={{ bgcolor: "white", borderRadius: 1, minWidth: 160 }}
    >
      {roles.map((role) => (
        <MenuItem key={role} value={role}>
          {role.toUpperCase()}
        </MenuItem>
      ))}
    </Select>
  );
};

export default RoleSelector;
