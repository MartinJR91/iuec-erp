import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import type { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import toast from "react-hot-toast";

import api from "../services/api";
import { useAuth } from "../context/AuthContext";

interface GradeRow {
  id: string;
  student_uuid: string;
  student: string;
  matricule?: string;
  cc?: number;
  tp?: number;
  exam?: number;
  average?: number;
  status?: string;
}

interface Course {
  id: string;
  code: string;
  name: string;
  program_code?: string;
}

const Notes: React.FC = () => {
  const { activeRole, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<GradeRow[]>([]);
  const [courseId, setCourseId] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [programCode, setProgramCode] = useState("FASE");
  const [saving, setSaving] = useState(false);

  const isTeacher = activeRole === "USER_TEACHER" || activeRole === "ENSEIGNANT";
  const isValidator = activeRole === "VALIDATOR_ACAD" || activeRole === "DOYEN";
  const isStudent = activeRole === "USER_STUDENT";

  // Charger les cours pour USER_TEACHER
  useEffect(() => {
    if (isTeacher) {
      const fetchCourses = async () => {
        setCoursesLoading(true);
        try {
          const response = await api.get("/api/courses/", {
            params: { teacher: "me" },
          });
          const results = Array.isArray(response.data) ? response.data : response.data.results || [];
          setCourses(results);
          if (results.length > 0 && !courseId) {
            setCourseId(results[0].id);
          }
        } catch (err: any) {
          console.error("Erreur chargement cours", err);
          toast.error("Erreur lors du chargement des cours");
        } finally {
          setCoursesLoading(false);
        }
      };
      fetchCourses();
    }
  }, [isTeacher, courseId]);

  // Charger les notes
  useEffect(() => {
    const fetchData = async () => {
      if (!activeRole || !token) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const params: any = {
          role: activeRole,
        };
        if (courseId) {
          params.course_id = courseId;
        } else if (programCode) {
          params.program = programCode;
        }

        const response = await api.get("/api/grades/", { params });
        const payload = response.data;

        if (Array.isArray(payload?.results)) {
          const mapped: GradeRow[] = payload.results.map((item: any) => ({
            id: item.student_id || item.id,
            student_uuid: item.student_id || item.id,
            student: item.email || `${item.matricule_permanent || ""} · ${item.email || ""}`,
            matricule: item.matricule_permanent,
            cc: item.cc,
            tp: item.tp,
            exam: item.exam,
            average: item.average,
            status: item.status,
          }));
          setRows(mapped);
        } else if (Array.isArray(payload)) {
          setRows(payload);
        } else {
          setRows([]);
        }
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || "Impossible de charger les notes.";
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    if (activeRole && token) {
      fetchData();
    }
  }, [activeRole, courseId, programCode, token]);

  // Calcul automatique de la moyenne pour ag-grid
  useEffect(() => {
    if (isTeacher && rows.length > 0) {
      setRows((prevRows) =>
        prevRows.map((row) => {
          const cc = Number(row.cc || 0);
          const tp = Number(row.tp || 0);
          const exam = Number(row.exam || 0);
          const avg = (cc + tp + exam) / 3;
          return {
            ...row,
            average: Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0,
          };
        })
      );
    }
  }, [rows.map((r) => `${r.cc}-${r.tp}-${r.exam}`).join(","), isTeacher]);

  const columnDefs = useMemo<ColDef[]>(
    () => [
      { field: "student", headerName: "Étudiant", flex: 1, minWidth: 220, editable: false },
      {
        field: "cc",
        headerName: "CC",
        width: 110,
        editable: isTeacher,
        valueParser: (params) => {
          const value = Number(params.newValue);
          return Number.isFinite(value) ? value : 0;
        },
      },
      {
        field: "tp",
        headerName: "TP",
        width: 110,
        editable: isTeacher,
        valueParser: (params) => {
          const value = Number(params.newValue);
          return Number.isFinite(value) ? value : 0;
        },
      },
      {
        field: "exam",
        headerName: "Exam",
        width: 120,
        editable: isTeacher,
        valueParser: (params) => {
          const value = Number(params.newValue);
          return Number.isFinite(value) ? value : 0;
        },
      },
      {
        field: "average",
        headerName: "Moyenne",
        width: 140,
        valueGetter: (params) => {
          const cc = Number(params.data?.cc || 0);
          const tp = Number(params.data?.tp || 0);
          const exam = Number(params.data?.exam || 0);
          const avg = (cc + tp + exam) / 3;
          return Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0;
        },
        editable: false,
      },
      {
        field: "status",
        headerName: "Statut",
        width: 140,
        cellRenderer: (params: any) => {
          const status = params.value || "N/A";
          const color = status === "VALIDÉ" ? "success" : status === "AJOURNÉ" ? "error" : "default";
          return <Chip label={status} color={color} size="small" />;
        },
      },
    ],
    [isTeacher]
  );

  const dataGridColumns: GridColDef[] = useMemo(
    () => [
      { field: "student", headerName: "Étudiant", minWidth: 200, flex: 1 },
      { field: "matricule", headerName: "Matricule", minWidth: 120 },
      {
        field: "cc",
        headerName: "CC",
        minWidth: 100,
        type: "number",
      },
      {
        field: "tp",
        headerName: "TP",
        minWidth: 100,
        type: "number",
      },
      {
        field: "exam",
        headerName: "Exam",
        minWidth: 100,
        type: "number",
      },
      {
        field: "average",
        headerName: "Moyenne",
        minWidth: 120,
        type: "number",
        valueFormatter: (params) => (params.value ? Number(params.value).toFixed(2) : "—"),
      },
      {
        field: "status",
        headerName: "Statut",
        minWidth: 120,
        renderCell: (params) => {
          const status = params.value || "N/A";
          const color = status === "VALIDÉ" ? "success" : status === "AJOURNÉ" ? "error" : "default";
          return <Chip label={status} color={color} size="small" />;
        },
      },
    ],
    []
  );

  const handleSubmitGrades = async () => {
    if (!courseId) {
      toast.error("Veuillez sélectionner un cours");
      return;
    }

    setSaving(true);
    try {
      const gradesPayload = rows.map((row) => ({
        student_uuid: row.student_uuid,
        cc: row.cc,
        tp: row.tp,
        exam: row.exam,
      }));

      await api.post("/api/grades/bulk-update/", {
        course_id: courseId,
        grades: gradesPayload,
      });

      toast.success("Notes enregistrées avec succès");
      // Recharger les données
      const response = await api.get("/api/grades/", {
        params: { role: activeRole, course_id: courseId },
      });
      const payload = response.data;
      if (Array.isArray(payload?.results)) {
        const mapped: GradeRow[] = payload.results.map((item: any) => ({
          id: item.student_id || item.id,
          student_uuid: item.student_id || item.id,
          student: item.email || `${item.matricule_permanent || ""} · ${item.email || ""}`,
          matricule: item.matricule_permanent,
          cc: item.cc,
          tp: item.tp,
          exam: item.exam,
          average: item.average,
          status: item.status,
        }));
        setRows(mapped);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Enregistrement impossible.";
      toast.error(errorMsg);
    } finally {
      setSaving(false);
    }
  };

  const handleCloseJury = async () => {
    if (!courseId) {
      toast.error("course_id requis.");
      return;
    }

    try {
      await api.post("/api/jury/close/", { course_id: courseId });
      toast.success("PV clôturé avec succès");
      // Recharger les données
      const response = await api.get("/api/grades/", {
        params: { role: activeRole, course_id: courseId },
      });
      const payload = response.data;
      if (Array.isArray(payload?.results)) {
        const mapped: GradeRow[] = payload.results.map((item: any) => ({
          id: item.student_id || item.id,
          student_uuid: item.student_id || item.id,
          student: item.email || `${item.matricule_permanent || ""} · ${item.email || ""}`,
          matricule: item.matricule_permanent,
          cc: item.cc,
          tp: item.tp,
          exam: item.exam,
          average: item.average,
          status: item.status,
        }));
        setRows(mapped);
      }
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Clôture impossible.";
      toast.error(errorMsg);
    }
  };

  if (loading || coursesLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && rows.length === 0) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Stack spacing={1} sx={{ mb: 3 }}>
        <Typography variant="h4">Gestion des notes</Typography>
        <Typography variant="body2" color="text.secondary">
          Saisie, PV jury et suivi étudiant selon votre rôle.
        </Typography>
      </Stack>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        {isTeacher && (
          <Grid item xs={12} md={6}>
            <Select
              label="Cours"
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              fullWidth
              displayEmpty
            >
              <MenuItem value="" disabled>
                Sélectionnez un cours
              </MenuItem>
              {courses.map((course) => (
                <MenuItem key={course.id} value={course.id}>
                  {course.code} - {course.name}
                </MenuItem>
              ))}
            </Select>
          </Grid>
        )}
        {!isTeacher && (
          <Grid item xs={12} md={4}>
            <TextField
              label="Programme"
              value={programCode}
              onChange={(event) => setProgramCode(event.target.value.toUpperCase())}
              fullWidth
            />
          </Grid>
        )}
        {!isTeacher && (
          <Grid item xs={12} md={4}>
            <TextField
              label="Course ID"
              value={courseId}
              onChange={(event) => setCourseId(event.target.value)}
              fullWidth
              helperText="Saisissez l'identifiant du cours"
            />
          </Grid>
        )}
      </Grid>

      {/* Vue USER_TEACHER : ag-grid éditable */}
      {isTeacher && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Saisie tableur
              </Typography>
              <div className="ag-theme-alpine" style={{ height: 460, width: "100%" }}>
                <AgGridReact
                  rowData={rows}
                  columnDefs={columnDefs}
                  getRowId={(params) => params.data.id}
                  onCellValueChanged={(event) => {
                    const updated = event.data as GradeRow;
                    setRows((prev) =>
                      prev.map((row) => {
                        if (row.id === updated.id) {
                          const cc = Number(updated.cc || 0);
                          const tp = Number(updated.tp || 0);
                          const exam = Number(updated.exam || 0);
                          const avg = (cc + tp + exam) / 3;
                          return {
                            ...updated,
                            average: Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0,
                          };
                        }
                        return row;
                      })
                    );
                  }}
                />
              </div>
            </CardContent>
          </Card>
          <Button variant="contained" onClick={handleSubmitGrades} disabled={saving || !courseId}>
            {saving ? <CircularProgress size={20} sx={{ mr: 1 }} /> : null}
            Sauvegarder les notes
          </Button>
        </>
      )}

      {/* Vue VALIDATOR_ACAD : PV Jury */}
      {isValidator && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                PV Jury
              </Typography>
              {rows.length === 0 ? (
                <Alert severity="info">Aucune note disponible pour ce cours.</Alert>
              ) : (
                <Box sx={{ height: 400, width: "100%" }}>
                  <DataGrid
                    rows={rows}
                    columns={dataGridColumns}
                    pageSizeOptions={[10, 25, 50]}
                    initialState={{
                      pagination: {
                        paginationModel: { pageSize: 10 },
                      },
                    }}
                  />
                </Box>
              )}
            </CardContent>
          </Card>
          <Button variant="contained" color="error" onClick={handleCloseJury} disabled={!courseId}>
            Clôturer le PV
          </Button>
        </>
      )}

      {/* Vue USER_STUDENT : read-only DataGrid */}
      {isStudent && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Mes notes
            </Typography>
            {rows.length === 0 ? (
              <Alert severity="info">Aucune note disponible.</Alert>
            ) : (
              <Box sx={{ height: 400, width: "100%" }}>
                <DataGrid
                  rows={rows}
                  columns={dataGridColumns}
                  pageSizeOptions={[10, 25, 50]}
                  initialState={{
                    pagination: {
                      paginationModel: { pageSize: 10 },
                    },
                  }}
                />
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Notes;
