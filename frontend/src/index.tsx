import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CssBaseline } from "@mui/material";
import { ThemeProvider } from "@mui/material/styles";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProviderContext, useThemeContext } from "./context/ThemeContext";
import { register } from "./serviceWorkerRegistration";

const container = document.getElementById("root");

if (!container) {
  throw new Error("Root element not found");
}

const root = createRoot(container);

const AppWithTheme: React.FC = () => {
  const { theme } = useThemeContext();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline enableColorScheme />
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
};

root.render(
  <React.StrictMode>
    <ThemeProviderContext>
      <AppWithTheme />
    </ThemeProviderContext>
  </React.StrictMode>
);

register();
