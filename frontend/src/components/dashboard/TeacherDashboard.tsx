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
import { Book, People, Assignment } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";

import KpiCard from "../KpiCard";

interface Course {
  code: string;
  name: string;
  studentCount: number;
  nextClass: string;
}

interface DashboardData {
  courses: Course[];
  gradedStudents: number;
  totalStudents: number;
}

const TeacherDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // TODO: Remplacer par un vrai appel API : await api.get("/api/dashboard/teacher/")
        await new Promise((resolve) => setTimeout(resolve, 500));
        
        setData({
          courses: [
            { code: "MATH101", name: "Mathématiques Appliquées", studentCount: 45, nextClass: "2026-01-30 08:00" },
            { code: "INFO201", name: "Algorithmique", studentCount: 38, nextClass: "2026-01-29 14:00" },
            { code: "PHYS102", name: "Physique Quantique", studentCount: 32, nextClass: "2026-01-31 10:00" },
            { code: "STAT301", name: "Statistiques", studentCount: 28, nextClass: "2026-02-01 16:00" },
          ],
          gradedStudents: 85,
          totalStudents: 120,
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

  const progressPercentage = Math.round((data.gradedStudents / data.totalStudents) * 100);

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Mes cours
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="Cours assignés"
            value={data.courses.length}
            subtitle="Semestre en cours"
            color="primary"
            icon={<Book />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="Étudiants notés"
            value={`${data.gradedStudents}/${data.totalStudents}`}
            subtitle={`${progressPercentage}% complété`}
            trend={progressPercentage >= 80 ? "up" : "neutral"}
            trendValue={progressPercentage >= 80 ? "Bien avancé" : "En cours"}
            color={progressPercentage >= 80 ? "success" : "warning"}
            icon={<People />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <KpiCard
            title="Total étudiants"
            value={data.totalStudents}
            subtitle="Tous cours confondus"
            color="info"
            icon={<Assignment />}
          />
        </Grid>
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h6">Mes cours actuels</Typography>
            <Button
              variant="contained"
              startIcon={<Assignment />}
              onClick={() => navigate("/notes")}
            >
              Saisie notes
            </Button>
          </Box>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>Code</strong></TableCell>
                  <TableCell><strong>Nom du cours</strong></TableCell>
                  <TableCell align="right"><strong>Nb étudiants</strong></TableCell>
                  <TableCell><strong>Prochain cours</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.courses.map((course) => (
                  <TableRow key={course.code} hover>
                    <TableCell>
                      <Chip label={course.code} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell>{course.name}</TableCell>
                    <TableCell align="right">{course.studentCount}</TableCell>
                    <TableCell>{new Date(course.nextClass).toLocaleString("fr-FR")}</TableCell>
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

export default TeacherDashboard;
