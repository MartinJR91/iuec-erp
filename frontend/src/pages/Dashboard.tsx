import React from "react";
import { Container } from "@mui/material";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import DashboardContent from "../components/DashboardContent";

const Dashboard: React.FC = () => {
  const { activeRole, user } = useAuth();
  const navigate = useNavigate();

  // Rediriger vers login si non connecté
  React.useEffect(() => {
    if (!user || !activeRole) {
      navigate("/login");
    }
  }, [user, activeRole, navigate]);

  if (!user || !activeRole) {
    return null;
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <DashboardContent />
    </Container>
  );
};

export default Dashboard;
