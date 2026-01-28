import React, { useState } from "react";
import { Box, Button, Link, Paper, TextField, Typography, Alert, CircularProgress } from "@mui/material";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const Login: React.FC = () => {
  const { login, token } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Rediriger si déjà connecté
  React.useEffect(() => {
    if (token) {
      navigate("/dashboard");
    }
  }, [token, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login({ email, password });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        bgcolor: "background.default",
      }}
    >
      <Paper sx={{ p: 4, width: "100%", maxWidth: 420 }}>
        <Typography variant="h5" component="h1" gutterBottom align="center" sx={{ mb: 3 }}>
          Connexion
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} noValidate>
          <TextField
            label="Email"
            type="email"
            fullWidth
            required
            margin="normal"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            autoComplete="email"
            autoFocus
          />
          <TextField
            label="Mot de passe"
            type="password"
            fullWidth
            required
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            autoComplete="current-password"
          />
          <Button
            type="submit"
            variant="contained"
            fullWidth
            sx={{ mt: 3, mb: 2 }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : "Se connecter"}
          </Button>
          <Box sx={{ textAlign: "center", mt: 2 }}>
            <Link
              href="#"
              onClick={(e) => {
                e.preventDefault();
                // TODO: Implémenter mot de passe oublié
                alert("Fonctionnalité à venir");
              }}
              variant="body2"
              sx={{ cursor: "pointer" }}
            >
              Mot de passe oublié ?
            </Link>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default Login;
