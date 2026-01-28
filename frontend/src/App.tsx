import React from "react";
import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";

import AppRoutes from "./AppRoutes";
import RoleSwitcher from "./components/RoleSwitcher";
import ThemeToggle from "./components/ThemeToggle";
import { useAuth } from "./context/AuthContext";

const App: React.FC = () => {
  const { token, logout, user } = useAuth();

  return (
    <>
      {token && (
        <AppBar position="sticky" color="primary">
          <Toolbar>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              IUEC ERP
            </Typography>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {user && (
                <Typography variant="body2" sx={{ mr: 1 }}>
                  {user.email}
                </Typography>
              )}
              <ThemeToggle />
              <RoleSwitcher />
              <Button color="inherit" onClick={logout} sx={{ ml: 1 }}>
                Déconnexion
              </Button>
            </Box>
          </Toolbar>
        </AppBar>
      )}
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box sx={{ minHeight: "70vh" }}>
          <AppRoutes />
        </Box>
      </Container>
    </>
  );
};

export default App;
