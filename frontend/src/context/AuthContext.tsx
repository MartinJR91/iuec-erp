import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { jwtDecode } from "jwt-decode";
import { useNavigate } from "react-router-dom";
import axios from "axios";

import api from "../services/api";

export type UserRole =
  | "RECTEUR"
  | "DAF"
  | "SG"
  | "ADMIN_SI"
  | "USER_TEACHER"
  | "ENSEIGNANT"
  | "OPERATOR_FINANCE";

export interface User {
  email: string;
  roles: UserRole[];
  activeRole: UserRole;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface TokenResponse {
  access: string;
  refresh: string;
}

interface JwtPayload {
  email?: string;
  roles?: string[];
  role_active?: string;
  exp?: number;
  [key: string]: unknown;
}

export interface AuthContextValue {
  user: User | null;
  token: string | null;
  roles: UserRole[];
  activeRole: UserRole | null;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  setActiveRole: (role: UserRole) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_STORAGE_KEY = "token";
const ROLE_STORAGE_KEY = "role_active";

const decodeToken = (token: string): { email: string; roles: UserRole[]; activeRole: UserRole } | null => {
  try {
    const decoded = jwtDecode<JwtPayload>(token);
    const email = decoded.email || "";
    const roles = (decoded.roles || []) as UserRole[];
    const activeRole = (decoded.role_active || roles[0] || "ADMIN_SI") as UserRole;
    return { email, roles, activeRole };
  } catch {
    return null;
  }
};

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const navigate = useNavigate();
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialiser user depuis token au chargement
  useEffect(() => {
    if (token) {
      const decoded = decodeToken(token);
      if (decoded) {
        const storedRole = localStorage.getItem(ROLE_STORAGE_KEY) as UserRole | null;
        const activeRole = storedRole && decoded.roles.includes(storedRole) ? storedRole : decoded.activeRole;
        setUser({
          email: decoded.email,
          roles: decoded.roles.length > 0 ? decoded.roles : ["ADMIN_SI"],
          activeRole,
        });
        localStorage.setItem(ROLE_STORAGE_KEY, activeRole);
      } else {
        // Token invalide, nettoyer
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setTokenState(null);
      }
    }
    setLoading(false);
  }, []);

  const login = async (credentials: LoginCredentials): Promise<void> => {
    try {
      const response = await api.post<TokenResponse>("/api/token/", credentials);
      const { access } = response.data;
      
      setTokenState(access);
      localStorage.setItem(TOKEN_STORAGE_KEY, access);

      const decoded = decodeToken(access);
      if (decoded) {
        const activeRole = decoded.activeRole;
        setUser({
          email: decoded.email,
          roles: decoded.roles.length > 0 ? decoded.roles : ["ADMIN_SI"],
          activeRole,
        });
        localStorage.setItem(ROLE_STORAGE_KEY, activeRole);
        navigate("/dashboard");
      } else {
        throw new Error("Token invalide");
      }
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) {
        throw new Error("Identifiants incorrects");
      }
      throw new Error("Erreur de connexion. Veuillez réessayer.");
    }
  };

  const logout = () => {
    setTokenState(null);
    setUser(null);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(ROLE_STORAGE_KEY);
    navigate("/login");
  };

  const setActiveRole = (role: UserRole) => {
    if (user && user.roles.includes(role)) {
      setUser({ ...user, activeRole: role });
      localStorage.setItem(ROLE_STORAGE_KEY, role);
    }
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      roles: user?.roles || [],
      activeRole: user?.activeRole || null,
      loading,
      login,
      logout,
      setActiveRole,
    }),
    [user, token, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
