import React from "react";
import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";

import AppRoutes from "./AppRoutes";
import RoleSwitcher from "./components/RoleSwitcher";
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
            {user && (
              <Typography variant="body2" sx={{ mr: 2 }}>
                {user.email}
              </Typography>
            )}
            <RoleSwitcher />
            <Button color="inherit" onClick={logout} sx={{ ml: 2 }}>
              Déconnexion
            </Button>
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
