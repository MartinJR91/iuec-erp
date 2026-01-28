import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

import api from "../services/api";
import { UserRole, useAuth } from "./AuthContext";

export interface RoleContextValue {
  roles: UserRole[];
  activeRole: UserRole;
  setActiveRole: (role: UserRole) => Promise<void>;
  token: string | null;
  regenerateToken: (role: UserRole) => Promise<void>;
}

const ROLE_STORAGE_KEY = "role_active";
const ROLES_STORAGE_KEY = "roles";

const DEFAULT_ROLES: UserRole[] = [
  "RECTEUR",
  "DAF",
  "SG",
  "ADMIN_SI",
  "USER_TEACHER",
  "ENSEIGNANT",
  "OPERATOR_FINANCE",
];

const RoleContext = createContext<RoleContextValue | undefined>(undefined);

const loadRoles = (): UserRole[] => {
  const raw = localStorage.getItem(ROLES_STORAGE_KEY);
  if (!raw) {
    return DEFAULT_ROLES;
  }
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed as UserRole[];
    }
  } catch {
    return DEFAULT_ROLES;
  }
  return DEFAULT_ROLES;
};

const loadActiveRole = (roles: UserRole[]): UserRole => {
  const stored = localStorage.getItem(ROLE_STORAGE_KEY);
  if (stored && roles.includes(stored as UserRole)) {
    return stored as UserRole;
  }
  return roles[0] ?? "ADMIN_SI";
};

export const RoleProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const { token, activeRole, setActiveRole: setAuthRole, roles: authRoles } = useAuth();
  const [roles] = useState<UserRole[]>(() => authRoles.length > 0 ? authRoles : loadRoles());

  const regenerateToken = useCallback(
    async (role: UserRole) => {
      if (!token) {
        return;
      }
      try {
        const response = await api.post<{ token: string }>("/auth/refresh-role", {
          role_active: role,
        });
        if (response.data?.token) {
          localStorage.setItem("token", response.data.token);
          // Recharger la page pour mettre à jour le token dans AuthContext
          window.location.reload();
        }
      } catch {
        // Si l'endpoint n'existe pas, on conserve le token existant.
      }
    },
    [token]
  );

  const setActiveRole = useCallback(
    async (role: UserRole) => {
      setAuthRole(role);
      localStorage.setItem(ROLE_STORAGE_KEY, role);
      await regenerateToken(role);
    },
    [regenerateToken, setAuthRole]
  );

  const roleValue = useMemo<RoleContextValue>(
    () => ({
      roles,
      activeRole: activeRole || loadActiveRole(roles),
      setActiveRole,
      token,
      regenerateToken,
    }),
    [activeRole, regenerateToken, roles, setActiveRole, token]
  );

  return <RoleContext.Provider value={roleValue}>{children}</RoleContext.Provider>;
};

export const useRole = (): RoleContextValue => {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error("useRole must be used within a RoleProvider");
  }
  return context;
};
