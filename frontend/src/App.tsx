import React from "react";
import { BrowserRouter } from "react-router-dom";
import { AppBar, Box, Container, Toolbar, Typography } from "@mui/material";

import AppRoutes from "./AppRoutes";
import RoleSwitcher from "./components/RoleSwitcher";

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppBar position="sticky" color="primary">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            IUEC ERP
          </Typography>
          <RoleSwitcher />
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Box sx={{ minHeight: "70vh" }}>
          <AppRoutes />
        </Box>
      </Container>
    </BrowserRouter>
  );
};

export default App;
