import React from "react";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";

const Login: React.FC = () => {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", mt: 8 }}>
      <Paper sx={{ p: 4, width: "100%", maxWidth: 420 }}>
        <Typography variant="h6" gutterBottom>
          Connexion
        </Typography>
        <Box component="form" noValidate autoComplete="off">
          <TextField label="Email" type="email" fullWidth margin="normal" />
          <TextField
            label="Mot de passe"
            type="password"
            fullWidth
            margin="normal"
          />
          <Button variant="contained" fullWidth sx={{ mt: 2 }}>
            Se connecter
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default Login;
