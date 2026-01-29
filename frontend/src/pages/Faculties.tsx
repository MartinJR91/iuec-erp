import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";

import api from "../services/api";
import { useAuth } from "../context/AuthContext";

interface Program {
  id: number;
  code: string;
  name: string;
  academic_rules_json: Record<string, unknown>;
  is_active: boolean;
  faculty: number;
}

interface Faculty {
  id: number;
  code: string;
  name: string;
  tutelle: string;
  is_active: boolean;
  doyen_uuid: string | null;
  programs?: Program[];
}

const Faculties: React.FC = () => {
  const { activeRole } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [faculties, setFaculties] = useState<Faculty[]>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<number | null>(null);
  const [rulesJson, setRulesJson] = useState<string>("{}");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const isRecteur = activeRole === "RECTEUR";
  const isAcademicAdmin = activeRole === "VALIDATOR_ACAD" || activeRole === "DOYEN";

  useEffect(() => {
    const fetchFaculties = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.get<Faculty[]>("/api/faculties/");
        setFaculties(response.data);
        const initialProgram = response.data[0]?.programs?.[0];
        if (initialProgram) {
          setSelectedProgramId(initialProgram.id);
          setRulesJson(JSON.stringify(initialProgram.academic_rules_json, null, 2));
        }
      } catch (err) {
        setError("Impossible de charger les facultés.");
      } finally {
        setLoading(false);
      }
    };

    if (activeRole) {
      fetchFaculties();
    } else {
      setLoading(false);
    }
  }, [activeRole]);

  const selectedProgram = useMemo(() => {
    for (const faculty of faculties) {
      const program = faculty.programs?.find((item) => item.id === selectedProgramId);
      if (program) {
        return program;
      }
    }
    return null;
  }, [faculties, selectedProgramId]);

  useEffect(() => {
    if (selectedProgram) {
      setRulesJson(JSON.stringify(selectedProgram.academic_rules_json, null, 2));
    }
  }, [selectedProgram]);

  const columns = useMemo<GridColDef[]>(
    () => [
      { field: "code", headerName: "Code", minWidth: 120 },
      { field: "name", headerName: "Faculté", flex: 1, minWidth: 220 },
      { field: "tutelle", headerName: "Tutelle", minWidth: 180 },
      { field: "programsCount", headerName: "Programmes", type: "number", minWidth: 140 },
      { field: "students", headerName: "Étudiants (est.)", type: "number", minWidth: 160 },
      { field: "budget", headerName: "Budget (est.)", minWidth: 160 },
    ],
    []
  );

  const rows = useMemo(
    () =>
      faculties.map((faculty) => {
        const programsCount = faculty.programs?.length ?? 0;
        const students = programsCount * 120;
        const budget = programsCount > 0 ? `${(students * 50000).toLocaleString("fr-FR")} XAF` : "—";
        return {
          id: faculty.id,
          code: faculty.code,
          name: faculty.name,
          tutelle: faculty.tutelle || "—",
          programsCount,
          students,
          budget,
        };
      }),
    [faculties]
  );

  const handleSave = async () => {
    if (!selectedProgram) {
      return;
    }
    setSaving(true);
    setSuccess(null);
    try {
      const parsed = JSON.parse(rulesJson) as Record<string, unknown>;
      await api.patch(`/api/programs/${selectedProgram.id}/`, {
        academic_rules_json: parsed,
      });
      setSuccess("Règles enregistrées.");
    } catch (err) {
      setError("JSON invalide ou sauvegarde refusée.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!activeRole || (!isRecteur && !isAcademicAdmin)) {
    return <Alert severity="warning">Accès réservé aux rôles académiques.</Alert>;
  }

  return (
    <Box>
      <Stack spacing={1} sx={{ mb: 3 }}>
        <Typography variant="h4">Gestion des facultés</Typography>
        <Typography variant="body2" color="text.secondary">
          Visualisez les facultés et ajustez les règles académiques selon votre scope.
        </Typography>
      </Stack>

      {isRecteur && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {rows.map((row) => (
            <Grid item xs={12} md={6} lg={4} key={row.id}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {row.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Tutelle : {row.tutelle}
                  </Typography>
                  <Divider sx={{ my: 2 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Étudiants (est.)
                      </Typography>
                      <Typography variant="h6">{row.students}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Budget (est.)
                      </Typography>
                      <Typography variant="h6">{row.budget}</Typography>
                    </Grid>
                  </Grid>
                  <Typography variant="caption" color="text.secondary">
                    Estimations calculées par programme (données réelles à connecter).
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {isRecteur && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Liste des facultés
            </Typography>
            <Box sx={{ height: 420 }}>
              <DataGrid rows={rows} columns={columns} disableRowSelectionOnClick />
            </Box>
          </CardContent>
        </Card>
      )}

      {isAcademicAdmin && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Règles académiques de votre faculté
            </Typography>
            <Stack spacing={2}>
              <Select
                value={selectedProgramId ?? ""}
                displayEmpty
                onChange={(event) => setSelectedProgramId(Number(event.target.value))}
              >
                <MenuItem value="" disabled>
                  Sélectionnez un programme
                </MenuItem>
                {faculties.flatMap((faculty) =>
                  (faculty.programs || []).map((program) => (
                    <MenuItem key={program.id} value={program.id}>
                      {faculty.code} - {program.name}
                    </MenuItem>
                  ))
                )}
              </Select>
              <TextField
                label="academic_rules_json"
                value={rulesJson}
                onChange={(event) => setRulesJson(event.target.value)}
                multiline
                minRows={10}
                maxRows={18}
                fullWidth
                inputProps={{ style: { fontFamily: "monospace" } }}
              />
              {success && <Alert severity="success">{success}</Alert>}
              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <Button variant="contained" onClick={handleSave} disabled={saving || !selectedProgramId}>
                  {saving ? "Enregistrement..." : "Enregistrer"}
                </Button>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Faculties;
