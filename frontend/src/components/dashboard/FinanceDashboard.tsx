import React, { useState, useEffect } from "react";
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Chip,
} from "@mui/material";
import { Receipt, AttachMoney, Warning } from "@mui/icons-material";

import KpiCard from "../KpiCard";

interface Invoice {
  studentName: string;
  invoiceNumber: string;
  amount: number;
  dueDate: string;
  daysOverdue: number;
}

interface DashboardData {
  unpaidInvoices: Invoice[];
  totalPending: number;
}

const FinanceDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // TODO: Remplacer par un vrai appel API : await api.get("/api/dashboard/finance/")
        await new Promise((resolve) => setTimeout(resolve, 500));
        
        setData({
          unpaidInvoices: [
            {
              studentName: "KONE Salif",
              invoiceNumber: "2026_FACT_SCOL_0001",
              amount: 250000,
              dueDate: "2026-01-15",
              daysOverdue: 13,
            },
            {
              studentName: "DIOUF Amadou",
              invoiceNumber: "2026_FACT_SCOL_0002",
              amount: 300000,
              dueDate: "2026-01-20",
              daysOverdue: 8,
            },
            {
              studentName: "NDIAYE Fatou",
              invoiceNumber: "2026_FACT_SCOL_0003",
              amount: 200000,
              dueDate: "2026-01-25",
              daysOverdue: 3,
            },
            {
              studentName: "BAH Mamadou",
              invoiceNumber: "2026_FACT_SCOL_0004",
              amount: 180000,
              dueDate: "2026-02-01",
              daysOverdue: 0,
            },
            {
              studentName: "TOURE Aissatou",
              invoiceNumber: "2026_FACT_SCOL_0005",
              amount: 270000,
              dueDate: "2026-02-05",
              daysOverdue: 0,
            },
          ],
          totalPending: 1200000,
        });
        setLoading(false);
      } catch (err) {
        setError("Erreur lors du chargement des données");
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error || "Données non disponibles"}
      </Alert>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("fr-CM", {
      style: "currency",
      currency: "XAF",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const overdueCount = data.unpaidInvoices.filter((inv) => inv.daysOverdue > 0).length;

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Gestion financière
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="Factures impayées"
            value={data.unpaidInvoices.length}
            subtitle="En attente"
            trend={overdueCount > 0 ? "down" : "neutral"}
            trendValue={overdueCount > 0 ? `${overdueCount} en retard` : "À jour"}
            color={overdueCount > 0 ? "error" : "warning"}
            icon={<Receipt />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="Total en attente"
            value={formatCurrency(data.totalPending)}
            subtitle="Montant total"
            trend="neutral"
            color="info"
            icon={<AttachMoney />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="Factures en retard"
            value={overdueCount}
            subtitle="Action requise"
            trend={overdueCount > 0 ? "down" : "neutral"}
            trendValue={overdueCount > 0 ? "Relance nécessaire" : "Aucune"}
            color={overdueCount > 0 ? "error" : "success"}
            icon={<Warning />}
          />
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">Factures impayées</Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={() => alert("Fonctionnalité d'encaissement (à implémenter)")}
            >
              Encaisser
            </Button>
          </Box>
          <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Étudiant</strong></TableCell>
                  <TableCell><strong>N° Facture</strong></TableCell>
                  <TableCell align="right"><strong>Montant</strong></TableCell>
                  <TableCell><strong>Échéance</strong></TableCell>
                  <TableCell align="center"><strong>Statut</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.unpaidInvoices.map((invoice) => (
                  <TableRow key={invoice.invoiceNumber} hover>
                    <TableCell>{invoice.studentName}</TableCell>
                    <TableCell>
                      <Chip label={invoice.invoiceNumber} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body1" sx={{ fontWeight: "bold" }}>
                        {formatCurrency(invoice.amount)}
                      </Typography>
                    </TableCell>
                    <TableCell>{new Date(invoice.dueDate).toLocaleDateString("fr-FR")}</TableCell>
                    <TableCell align="center">
                      <Chip
                        label={invoice.daysOverdue > 0 ? `${invoice.daysOverdue}j de retard` : "À échéance"}
                        color={invoice.daysOverdue > 0 ? "error" : "warning"}
                        size="small"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default FinanceDashboard;
