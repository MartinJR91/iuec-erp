import React, { createContext, useContext, useMemo, useState } from "react";

export type UserRole =
  | "RECTEUR"
  | "DAF"
  | "SG"
  | "ADMIN_SI"
  | "USER_TEACHER"
  | "ENSEIGNANT"
  | "OPERATOR_FINANCE";

export interface AuthState {
  token: string | null;
  activeRole: UserRole;
}

export interface AuthContextValue extends AuthState {
  setToken: (token: string | null) => void;
  setActiveRole: (role: UserRole) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [token, setTokenState] = useState<string | null>(null);
  const [activeRole, setActiveRoleState] = useState<UserRole>("ADMIN_SI");

  const setToken = (value: string | null) => {
    setTokenState(value);
  };

  const setActiveRole = (role: UserRole) => {
    setActiveRoleState(role);
  };

  const logout = () => {
    setTokenState(null);
    setActiveRoleState("ADMIN_SI");
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      activeRole,
      setToken,
      setActiveRole,
      logout,
    }),
    [token, activeRole]
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
