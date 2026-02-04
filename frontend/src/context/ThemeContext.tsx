import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Theme, createTheme } from "@mui/material/styles";

interface ThemeContextValue {
  darkMode: boolean;
  toggleDarkMode: () => void;
  theme: Theme;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const THEME_STORAGE_KEY = "darkMode";

const getInitialDarkMode = (): boolean => {
  if (typeof window === "undefined") {
    return false;
  }
  return localStorage.getItem(THEME_STORAGE_KEY) === "true";
};

export const ThemeProviderContext: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [darkMode, setDarkMode] = useState<boolean>(() => getInitialDarkMode());

  useEffect(() => {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === null) {
      return;
    }
    const next = stored === "true";
    if (next !== darkMode) {
      setDarkMode(next);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Initialisation unique au montage

  const toggleDarkMode = () => {
    setDarkMode((prev) => {
      const next = !prev;
      localStorage.setItem(THEME_STORAGE_KEY, String(next));
      return next;
    });
  };

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: darkMode ? "dark" : "light",
        },
        components: {
          MuiCssBaseline: {
            styleOverrides: {
              body: {
                transition: "background-color 200ms ease, color 200ms ease",
              },
            },
          },
        },
      }),
    [darkMode]
  );

  const value = useMemo<ThemeContextValue>(
    () => ({
      darkMode,
      toggleDarkMode,
      theme,
    }),
    [darkMode, theme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};

export const useThemeContext = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useThemeContext must be used within ThemeProviderContext");
  }
  return context;
};
