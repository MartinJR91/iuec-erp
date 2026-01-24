import React from "react";
import { Grid, Paper, Typography } from "@mui/material";

import { RoleDashboardHint } from "../components/RoleSwitcher";

const Dashboard: React.FC = () => {
  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <Paper sx={{ p: 3 }}>
          <RoleDashboardHint />
        </Paper>
      </Grid>
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Alertes
          </Typography>
          <Typography variant="body2">
            Aucun incident critique pour le moment.
          </Typography>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default Dashboard;
