import React from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline } from "@mui/material";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { RoleProvider } from "./context/RoleContext";
import { register } from "./serviceWorkerRegistration";

const container = document.getElementById("root");

if (!container) {
  throw new Error("Root element not found");
}

const root = createRoot(container);

root.render(
  <React.StrictMode>
    <CssBaseline />
    <AuthProvider>
      <RoleProvider>
        <App />
      </RoleProvider>
    </AuthProvider>
  </React.StrictMode>
);

register();
