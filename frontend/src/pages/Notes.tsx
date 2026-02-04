import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, CellValueChangedEvent } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import toast from "react-hot-toast";

import api from "../services/api";
import { useAuth } from "../context/AuthContext";

// Interfaces
interface Course {
  evaluation_id: number;
  course_element_code: string;
  course_element_name: string;
  teaching_unit_code: string;
  teaching_unit_name: string;
  evaluation_type: string;
  session_date: string | null;
  is_closed: boolean;
}

interface Grade {
  id: number;
  evaluation: number;
  evaluation_type: string;
  evaluation_course_element: string;
  student: number;
  student_matricule: string;
  student_email: string;
  value: number | null;
  is_absent: boolean;
  teacher: number | null;
  teacher_email: string | null;
  created_by_role: string;
  created_at: string;
}

interface GradeRow {
  id: string;
  student_id: number;
  student_matricule: string;
  student_name: string;
  evaluation_cc_id?: number;
  evaluation_tp_id?: number;
  evaluation_exam_id?: number;
  cc?: number | null;
  tp?: number | null;
  exam?: number | null;
  average?: number;
  status?: string;
}

interface RegistrationPedagogical {
  id: number;
  registration_admin: number;
  teaching_unit: number;
  teaching_unit_code?: string;
  teaching_unit_name?: string;
  status: string;
}

const Notes: React.FC = () => {
  const { activeRole, token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<GradeRow[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [registrations, setRegistrations] = useState<RegistrationPedagogical[]>([]);
  const [closingJury, setClosingJury] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const isTeacher = activeRole === "USER_TEACHER" || activeRole === "ENSEIGNANT";
  const isValidator = activeRole === "VALIDATOR_ACAD" || activeRole === "DOYEN";
  const isStudent = activeRole === "USER_STUDENT";

  // Charger les cours pour USER_TEACHER
  useEffect(() => {
    if (isTeacher) {
      const fetchCourses = async () => {
        setCoursesLoading(true);
        try {
          const response = await api.get("/api/courses/my-courses/");
          const results = response.data.results || [];
          setCourses(results);
          // Sélectionner le premier cours seulement si aucun n'est sélectionné
          if (results.length > 0 && !selectedCourse) {
            setSelectedCourse(results[0]);
          }
        } catch (err: any) {
          console.error("Erreur chargement cours", err);
          toast.error("Erreur lors du chargement des cours");
          setError(err.response?.data?.detail || "Impossible de charger les cours");
        } finally {
          setCoursesLoading(false);
        }
      };
      fetchCourses();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTeacher]); // Retirer selectedCourse des dépendances pour éviter la boucle infinie

  // Charger les notes selon le rôle
  useEffect(() => {
    const fetchGrades = async () => {
      if (!activeRole || !token) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        let response;
        
        if (isStudent) {
          // Pour étudiant : charger ses notes
          response = await api.get("/api/grades/");
        } else if (isValidator) {
          // Pour validateur : charger les inscriptions pédagogiques pour PV jury
          response = await api.get("/api/registrations/pedagogical/");
          if (response.data) {
            const regs = Array.isArray(response.data) ? response.data : response.data.results || [];
            setRegistrations(regs);
            setLoading(false);
            return;
          }
        } else if (isTeacher && selectedCourse) {
          // Pour enseignant : charger les notes de l'UE du cours sélectionné
          // Récupérer toutes les notes pour cette UE (toutes les évaluations)
          response = await api.get("/api/grades/", {
            params: {
              evaluation__course_element__teaching_unit__code: selectedCourse.teaching_unit_code,
            },
          });
        } else {
          setLoading(false);
          return;
        }

        const payload = response.data;
        let grades: Grade[] = [];

        if (Array.isArray(payload?.results)) {
          grades = payload.results;
        } else if (Array.isArray(payload)) {
          grades = payload;
        }

        // Grouper les notes par étudiant et par type d'évaluation
        if (isTeacher && selectedCourse) {
          const studentsMap = new Map<number, GradeRow>();

          // Récupérer les étudiants inscrits à l'UE
          try {
            const regResponse = await api.get("/api/registrations/pedagogical/", {
              params: {
                teaching_unit__code: selectedCourse.teaching_unit_code,
              },
            });
            const regs = Array.isArray(regResponse.data) 
              ? regResponse.data 
              : regResponse.data?.results || [];
            
            regs.forEach((reg: any) => {
              const studentId = reg.registration_admin?.student || reg.student;
              if (studentId && !studentsMap.has(studentId)) {
                studentsMap.set(studentId, {
                  id: `student-${studentId}`,
                  student_id: studentId,
                  student_matricule: reg.registration_admin?.student?.matricule_permanent || "",
                  student_name: reg.registration_admin?.student?.identity?.email || "",
                  cc: null,
                  tp: null,
                  exam: null,
                  average: 0,
                  status: reg.status || "En cours",
                });
              }
            });
          } catch (err) {
            console.error("Erreur chargement inscriptions", err);
          }

          // Récupérer toutes les évaluations pour cette UE (CC, TP, Exam)
          // On utilise les IDs d'évaluations depuis les notes existantes
          const evaluationsMap = new Map<string, number>();
          grades.forEach((grade: Grade) => {
            const evalType = grade.evaluation_type;
            if (!evaluationsMap.has(evalType)) {
              evaluationsMap.set(evalType, grade.evaluation);
            }
          });
          
          // Si aucune note n'existe, on doit créer les évaluations ou les récupérer
          // Pour l'instant, on utilise les IDs depuis selectedCourse si disponible
          if (evaluationsMap.size === 0 && selectedCourse) {
            // On pourrait récupérer les évaluations depuis l'API, mais pour l'instant
            // on laisse l'utilisateur créer les notes et les IDs seront générés
          }

          // Mapper les notes aux étudiants
          grades.forEach((grade: Grade) => {
            const studentId = grade.student;
            let row = studentsMap.get(studentId);
            
            if (!row) {
              row = {
                id: `student-${studentId}`,
                student_id: studentId,
                student_matricule: grade.student_matricule,
                student_name: grade.student_email,
                cc: null,
                tp: null,
                exam: null,
                average: 0,
                status: "En cours",
              };
              studentsMap.set(studentId, row);
            }

            // Assigner la note selon le type d'évaluation
            if (grade.evaluation_type === "CC") {
              row.cc = grade.value;
              row.evaluation_cc_id = grade.evaluation;
            } else if (grade.evaluation_type === "TP") {
              row.tp = grade.value;
              row.evaluation_tp_id = grade.evaluation;
            } else if (grade.evaluation_type === "Exam") {
              row.exam = grade.value;
              row.evaluation_exam_id = grade.evaluation;
            }
          });

          // S'assurer que tous les étudiants ont les IDs d'évaluations même sans notes
          const finalRows = Array.from(studentsMap.values()).map((row) => {
            // Assigner les IDs d'évaluations si manquants
            if (!row.evaluation_cc_id && evaluationsMap.has("CC")) {
              row.evaluation_cc_id = evaluationsMap.get("CC");
            }
            if (!row.evaluation_tp_id && evaluationsMap.has("TP")) {
              row.evaluation_tp_id = evaluationsMap.get("TP");
            }
            if (!row.evaluation_exam_id && evaluationsMap.has("Exam")) {
              row.evaluation_exam_id = evaluationsMap.get("Exam");
            }

            // Calculer la moyenne pondérée (simplifié : moyenne arithmétique pour l'instant)
            const cc = Number(row.cc || 0);
            const tp = Number(row.tp || 0);
            const exam = Number(row.exam || 0);
            const count = (cc > 0 ? 1 : 0) + (tp > 0 ? 1 : 0) + (exam > 0 ? 1 : 0);
            const avg = count > 0 ? (cc + tp + exam) / count : 0;
            
            return {
              ...row,
              average: Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0,
            };
          });

          setRows(finalRows);
        } else if (isStudent) {
          // Pour étudiant : grouper les notes par UE
          const ueMap = new Map<string, GradeRow>();
          
          grades.forEach((grade: Grade) => {
            const ueCode = grade.evaluation_course_element || "UE-UNKNOWN";
            let row = ueMap.get(ueCode);
            
            if (!row) {
              row = {
                id: `ue-${ueCode}`,
                student_id: grade.student,
                student_matricule: grade.student_matricule,
                student_name: grade.student_email,
                cc: null,
                tp: null,
                exam: null,
                average: 0,
                status: "En cours",
              };
              ueMap.set(ueCode, row);
            }
            
            // Assigner la note selon le type
            if (grade.evaluation_type === "CC") {
              row.cc = grade.value;
            } else if (grade.evaluation_type === "TP") {
              row.tp = grade.value;
            } else if (grade.evaluation_type === "Exam") {
              row.exam = grade.value;
            }
          });
          
          // Calculer les moyennes pour chaque UE
          const studentRows = Array.from(ueMap.values()).map((row) => {
            const cc = Number(row.cc || 0);
            const tp = Number(row.tp || 0);
            const exam = Number(row.exam || 0);
            const count = (cc > 0 ? 1 : 0) + (tp > 0 ? 1 : 0) + (exam > 0 ? 1 : 0);
            const avg = count > 0 ? (cc + tp + exam) / count : 0;
            
            return {
              ...row,
              average: Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0,
            };
          });
          
          setRows(studentRows);
        }
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || "Impossible de charger les notes.";
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    if (activeRole && token && (isStudent || (isTeacher && selectedCourse) || isValidator)) {
      fetchGrades();
    }
  }, [activeRole, token, selectedCourse, isTeacher, isStudent, isValidator, refreshKey]);

  // Colonnes ag-grid pour USER_TEACHER
  const columnDefs = useMemo<ColDef[]>(
    () => [
      {
        field: "student_matricule",
        headerName: "Matricule",
        flex: 0.8,
        minWidth: 120,
        editable: false,
      },
      {
        field: "student_name",
        headerName: "Étudiant",
        flex: 1.5,
        minWidth: 220,
        editable: false,
      },
      {
        field: "cc",
        headerName: "CC",
        width: 110,
        editable: true,
        valueParser: (params) => {
          const value = Number(params.newValue);
          return Number.isFinite(value) && value >= 0 && value <= 20 ? value : null;
        },
        cellEditor: "agNumberCellEditor",
        cellEditorParams: {
          min: 0,
          max: 20,
          precision: 2,
        },
      },
      {
        field: "tp",
        headerName: "TP",
        width: 110,
        editable: true,
        valueParser: (params) => {
          const value = Number(params.newValue);
          return Number.isFinite(value) && value >= 0 && value <= 20 ? value : null;
        },
        cellEditor: "agNumberCellEditor",
        cellEditorParams: {
          min: 0,
          max: 20,
          precision: 2,
        },
      },
      {
        field: "exam",
        headerName: "Exam",
        width: 120,
        editable: true,
        valueParser: (params) => {
          const value = Number(params.newValue);
          return Number.isFinite(value) && value >= 0 && value <= 20 ? value : null;
        },
        cellEditor: "agNumberCellEditor",
        cellEditorParams: {
          min: 0,
          max: 20,
          precision: 2,
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
          const count = (cc > 0 ? 1 : 0) + (tp > 0 ? 1 : 0) + (exam > 0 ? 1 : 0);
          const avg = count > 0 ? (cc + tp + exam) / count : 0;
          return Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0;
        },
        editable: false,
        cellStyle: { fontWeight: "bold" },
        cellRenderer: (params: any) => {
          const value = params.value || 0;
          const color = value >= 10 ? "success" : value >= 8 ? "warning" : "error";
          return (
            <Chip 
              label={value.toFixed(2)} 
              color={color} 
              size="small" 
              sx={{ fontWeight: "bold" }}
            />
          );
        },
      },
      {
        field: "status",
        headerName: "Statut UE",
        width: 140,
        cellRenderer: (params: any) => {
          const status = params.value || "En cours";
          const color =
            status === "Validé" || status === "Validée"
              ? "success"
              : status === "Ajourné"
              ? "error"
              : "default";
          return <Chip label={status} color={color} size="small" />;
        },
        editable: false,
      },
    ],
    []
  );

  // Colonnes DataGrid pour VALIDATOR_ACAD et USER_STUDENT
  const dataGridColumns: GridColDef[] = useMemo(
    () => [
      { field: "teaching_unit_code", headerName: "Code UE", minWidth: 150, flex: 0.8 },
      { field: "teaching_unit_name", headerName: "UE", minWidth: 200, flex: 1.2 },
      {
        field: "status",
        headerName: "Statut",
        minWidth: 120,
        renderCell: (params) => {
          const status = params.value || "En cours";
          const color =
            status === "Validé" || status === "Validée"
              ? "success"
              : status === "Ajourné"
              ? "error"
              : "default";
          return <Chip label={status} color={color} size="small" />;
        },
      },
    ],
    []
  );

  const studentDataGridColumns: GridColDef[] = useMemo(
    () => [
      { field: "student_matricule", headerName: "Matricule", minWidth: 120 },
      { field: "student_name", headerName: "Étudiant", minWidth: 200, flex: 1 },
      {
        field: "cc",
        headerName: "CC",
        minWidth: 100,
        type: "number",
        valueFormatter: (params) => (params.value ? Number(params.value).toFixed(2) : "—"),
      },
      {
        field: "tp",
        headerName: "TP",
        minWidth: 100,
        type: "number",
        valueFormatter: (params) => (params.value ? Number(params.value).toFixed(2) : "—"),
      },
      {
        field: "exam",
        headerName: "Exam",
        minWidth: 100,
        type: "number",
        valueFormatter: (params) => (params.value ? Number(params.value).toFixed(2) : "—"),
      },
      {
        field: "average",
        headerName: "Moyenne",
        minWidth: 120,
        type: "number",
        valueFormatter: (params) => (params.value ? Number(params.value).toFixed(2) : "—"),
        cellStyle: { fontWeight: "bold" },
      },
      {
        field: "status",
        headerName: "Statut",
        minWidth: 120,
        renderCell: (params) => {
          const status = params.value || "En cours";
          const color =
            status === "Validé" || status === "Validée"
              ? "success"
              : status === "Ajourné"
              ? "error"
              : "default";
          return <Chip label={status} color={color} size="small" />;
        },
      },
    ],
    []
  );

  // Gestion du changement de cellule dans ag-grid
  const handleCellValueChanged = useCallback(
    (event: CellValueChangedEvent) => {
      const updated = event.data as GradeRow;
      setRows((prev) =>
        prev.map((row) => {
          if (row.id === updated.id) {
            const cc = Number(updated.cc || 0);
            const tp = Number(updated.tp || 0);
            const exam = Number(updated.exam || 0);
            const count = (cc > 0 ? 1 : 0) + (tp > 0 ? 1 : 0) + (exam > 0 ? 1 : 0);
            const avg = count > 0 ? (cc + tp + exam) / count : 0;
            return {
              ...updated,
              average: Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0,
            };
          }
          return row;
        })
      );
    },
    []
  );

  // Sauvegarder les notes en masse
  const handleSubmitGrades = async () => {
    if (!selectedCourse) {
      toast.error("Veuillez sélectionner un cours");
      return;
    }

    setSaving(true);
    try {
      // Préparer les données pour bulk-update
      const gradesPayload: any[] = [];

      rows.forEach((row) => {
        // Note CC
        if (row.evaluation_cc_id !== undefined && row.cc !== null && row.cc !== undefined) {
          gradesPayload.push({
            evaluation_id: row.evaluation_cc_id,
            student_id: row.student_id,
            value: row.cc,
            is_absent: false,
          });
        }
        // Note TP
        if (row.evaluation_tp_id !== undefined && row.tp !== null && row.tp !== undefined) {
          gradesPayload.push({
            evaluation_id: row.evaluation_tp_id,
            student_id: row.student_id,
            value: row.tp,
            is_absent: false,
          });
        }
        // Note Exam
        if (row.evaluation_exam_id !== undefined && row.exam !== null && row.exam !== undefined) {
          gradesPayload.push({
            evaluation_id: row.evaluation_exam_id,
            student_id: row.student_id,
            value: row.exam,
            is_absent: false,
          });
        }
      });

      if (gradesPayload.length === 0) {
        toast.error("Aucune note à sauvegarder");
        setSaving(false);
        return;
      }

      const response = await api.post("/api/grades/bulk-update/", gradesPayload);

      const created = response.data.created || 0;
      const updated = response.data.updated || 0;
      const errors = response.data.errors || [];

      if (errors.length > 0) {
        toast.error(`Erreurs lors de l'enregistrement : ${errors.length} note(s) non enregistrée(s)`);
        console.error("Erreurs détaillées:", errors);
      } else {
        toast.success(
          `Notes enregistrées avec succès : ${created} créée(s), ${updated} mise(s) à jour`
        );
      }

      // Recharger les données en déclenchant un nouveau fetch
      setRefreshKey((prev) => prev + 1);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Enregistrement impossible.";
      toast.error(errorMsg);
      if (err.response?.data?.errors) {
        console.error("Erreurs détaillées:", err.response.data.errors);
        toast.error(`${errorMsg} - Voir la console pour plus de détails`);
      }
    } finally {
      setSaving(false);
    }
  };

  // Clôturer le PV jury
  const handleCloseJury = async (registrationId: number) => {
    setClosingJury(true);
    try {
      await api.post("/api/jury/close/", {
        registration_id: registrationId,
      });

      toast.success("PV clôturé avec succès");
      
      // Recharger les inscriptions
      const response = await api.get("/api/registrations/pedagogical/");
      const regs = Array.isArray(response.data) ? response.data : response.data?.results || [];
      setRegistrations(regs);
      setRefreshKey((prev) => prev + 1);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Clôture impossible.";
      toast.error(errorMsg);
    } finally {
      setClosingJury(false);
    }
  };

  if (loading || coursesLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && rows.length === 0 && registrations.length === 0) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack spacing={2} sx={{ mb: 3 }}>
        <Typography variant="h4">Gestion des notes</Typography>
        <Typography variant="body2" color="text.secondary">
          {isTeacher && "Saisie des notes pour vos cours"}
          {isValidator && "PV Jury - Validation et clôture"}
          {isStudent && "Consultation de vos notes"}
        </Typography>
      </Stack>

      {/* Sélecteur de cours pour USER_TEACHER */}
      {isTeacher && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <FormControl fullWidth>
              <InputLabel id="course-select-label">Cours</InputLabel>
              <Select
                labelId="course-select-label"
                label="Cours"
                value={selectedCourse?.evaluation_id || ""}
                onChange={(e) => {
                  const course = courses.find((c) => c.evaluation_id === Number(e.target.value));
                  setSelectedCourse(course || null);
                }}
                disabled={coursesLoading}
              >
                {courses.map((course) => (
                  <MenuItem key={course.evaluation_id} value={course.evaluation_id}>
                    {course.course_element_code} - {course.course_element_name} ({course.evaluation_type})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </CardContent>
        </Card>
      )}

      {/* Vue USER_TEACHER : ag-grid éditable */}
      {isTeacher && selectedCourse && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Saisie des notes - {selectedCourse.course_element_name}
              </Typography>
              <div 
                className="ag-theme-alpine" 
                style={{ 
                  height: 500, 
                  width: "100%",
                  minHeight: 400,
                }}
              >
                <AgGridReact
                  rowData={rows}
                  columnDefs={columnDefs}
                  getRowId={(params) => params.data.id}
                  onCellValueChanged={handleCellValueChanged}
                  defaultColDef={{
                    resizable: true,
                    sortable: true,
                    filter: true,
                  }}
                  stopEditingWhenCellsLoseFocus
                  singleClickEdit
                  animateRows
                  rowSelection="multiple"
                  suppressRowClickSelection
                />
              </div>
            </CardContent>
          </Card>
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            <Button
              variant="contained"
              onClick={handleSubmitGrades}
              disabled={saving || !selectedCourse || rows.length === 0}
              size="large"
              sx={{ minWidth: 200 }}
            >
              {saving ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Enregistrement...
                </>
              ) : (
                "Sauvegarder les notes"
              )}
            </Button>
            {rows.length > 0 && (
              <Chip 
                label={`${rows.length} étudiant(s)`}
                color="info"
                variant="outlined"
              />
            )}
          </Stack>
        </>
      )}

      {/* Vue VALIDATOR_ACAD : PV Jury */}
      {isValidator && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="h6">
                  PV Jury - Unités d'enseignement
                </Typography>
                <Chip 
                  label={`Total: ${registrations.length}`}
                  color="primary"
                  variant="outlined"
                />
              </Stack>
              {registrations.length === 0 ? (
                <Alert severity="info">Aucune inscription pédagogique disponible.</Alert>
              ) : (
                <Box sx={{ height: 500, width: "100%" }}>
                  <DataGrid
                    rows={registrations.map((reg) => ({
                      id: reg.id,
                      teaching_unit_code: reg.teaching_unit_code || `UE-${reg.teaching_unit}`,
                      teaching_unit_name: reg.teaching_unit_name || `Unité ${reg.teaching_unit}`,
                      status: reg.status,
                      registration_id: reg.id,
                    }))}
                    columns={[
                      ...dataGridColumns,
                      {
                        field: "actions",
                        headerName: "Actions",
                        width: 180,
                        renderCell: (params) => {
                          const registrationId = params.row.registration_id;
                          const status = params.row.status;
                          const isClosed = status === "Validé" || status === "Ajourné";
                          
                          return (
                            <Button
                              variant="contained"
                              color={isClosed ? "success" : "error"}
                              size="small"
                              onClick={() => handleCloseJury(registrationId)}
                              disabled={isClosed || closingJury}
                              sx={{ minWidth: 120 }}
                            >
                              {closingJury ? (
                                <CircularProgress size={16} sx={{ mr: 1 }} />
                              ) : null}
                              {isClosed ? "Clôturé" : "Clôturer PV"}
                            </Button>
                          );
                        },
                      },
                    ]}
                    pageSizeOptions={[10, 25, 50]}
                    initialState={{
                      pagination: {
                        paginationModel: { pageSize: 10 },
                      },
                    }}
                    sx={{
                      "& .MuiDataGrid-cell:focus": {
                        outline: "none",
                      },
                    }}
                  />
                </Box>
              )}
            </CardContent>
          </Card>
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
              <Box sx={{ height: 500, width: "100%" }}>
                <DataGrid
                  rows={rows}
                  columns={studentDataGridColumns}
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
