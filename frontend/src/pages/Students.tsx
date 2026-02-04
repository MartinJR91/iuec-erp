import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  InputAdornment,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { DataGrid, GridColDef, GridPaginationModel, GridActionsCellItem, GridToolbar } from "@mui/x-data-grid";
import { Visibility, Edit, Add, Search, CheckCircle, Block } from "@mui/icons-material";
import toast from "react-hot-toast";
import axios from "axios";

import { useAuth } from "../context/AuthContext";
import StudentDetailModal from "../components/StudentDetailModal";
import StudentEnrollModal from "../components/StudentEnrollModal";
import StudentStatusModal from "../components/StudentStatusModal";

interface StudentRow {
  id: string;
  identity_uuid: string;
  identity_nested?: {
    first_name: string;
    last_name: string;
    email: string;
  };
  email: string;
  matricule_permanent: string;
  date_entree: string;
  program_code?: string;
  program_name?: string;
  faculty_code?: string;
  finance_status: string;
  finance_status_effective?: string;
  academic_status?: string;
  balance: number;
  current_level?: string;
  moratoires_actifs?: number;
  moratoires_actifs_data?: Array<{ statut: string; date_fin: string }>;
  bourses_actives?: number;
  bourses_actives_data?: Array<{ id: string; montant: number; statut: string }>;
  registrations_admin?: Array<{
    id: number;
    academic_year: { code: string; label: string } | string;
    level: string;
    finance_status: string;
    registration_date: string;
  }>;
}

const Students: React.FC = () => {
  const { activeRole, token } = useAuth();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<StudentRow[]>([]);
  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [enrollModalOpen, setEnrollModalOpen] = useState(false);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [selectedStudentStatus, setSelectedStudentStatus] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState("");
  const [facultyFilter, setFacultyFilter] = useState<string>("");
  const [moratoireFilter, setMoratoireFilter] = useState<boolean | null>(
    searchParams.get("moratoire_actif") === "true" ? true : null
  );
  const [bourseFilter, setBourseFilter] = useState<boolean | null>(
    searchParams.get("boursier") === "true" ? true : null
  );
  const [studentBourses, setStudentBourses] = useState<Record<string, Array<{ id: string; montant: number; statut: string; type_bourse: string; date_fin_validite: string | null }>>>({});
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  });

  const isRecteur = activeRole === "RECTEUR";
  const isDoyen = activeRole === "DOYEN" || activeRole === "VALIDATOR_ACAD";
  const isStudent = activeRole === "USER_STUDENT";
  const isFinance = activeRole === "OPERATOR_FINANCE";
  const isScolarite = activeRole === "SCOLARITE";

  useEffect(() => {
    const fetchStudents = async () => {
      if (!activeRole || !token) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await axios.get("/api/students/", {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Role-Active": activeRole,
          },
        });
        const payload = response.data;
        const results: StudentRow[] = Array.isArray(payload) ? payload : payload.results || [];
        const data = results.map((item: any) => ({
          id: String(item.id),
          identity_uuid: item.identity_uuid || item.identity,
          identity_nested: item.identity_nested,
          email: item.email || item.identity_nested?.email || "",
          matricule_permanent: item.matricule_permanent || item.matricule || "",
          date_entree: item.date_entree || "",
          program_code: item.program_code || "",
          program_name: item.program_name || "",
          faculty_code: item.faculty_code || "",
          finance_status: item.finance_status || "OK",
          finance_status_effective: item.finance_status_effective || item.finance_status,
          academic_status: item.academic_status || "Actif",
          balance: Number(item.balance || 0),
          current_level: item.registrations_admin?.[0]?.level || "",
          registrations_admin: item.registrations_admin || [],
          bourses_actives: 0,
          bourses_actives_data: [],
        }));
        
        // Charger les bourses actives pour chaque étudiant
        if (!isStudent) {
          const boursesPromises = data.map(async (student) => {
            try {
              const boursesResponse = await axios.get(`/api/students/${student.id}/bourses-actives/`, {
                headers: {
                  Authorization: `Bearer ${token}`,
                  "X-Role-Active": activeRole,
                },
              });
              const bourses = boursesResponse.data.bourses || [];
              return {
                ...student,
                bourses_actives: bourses.length,
                bourses_actives_data: bourses.map((b: any) => ({
                  id: b.id,
                  montant: b.montant,
                  statut: b.statut,
                })),
              };
            } catch {
              return student;
            }
          });
          const studentsWithBourses = await Promise.all(boursesPromises);
          setRows(studentsWithBourses);
        } else {
          setRows(data);
        }
      } catch (err: any) {
        const errorMsg = err.response?.data?.detail || "Impossible de charger les étudiants.";
        setError(errorMsg);
        toast.error(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchStudents();
  }, [activeRole, token]);

  const filteredRows = useMemo(() => {
    let filtered = rows;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (row) =>
          row.matricule_permanent.toLowerCase().includes(term) ||
          row.identity_nested?.first_name?.toLowerCase().includes(term) ||
          row.identity_nested?.last_name?.toLowerCase().includes(term) ||
          row.email.toLowerCase().includes(term) ||
          `${row.identity_nested?.first_name || ""} ${row.identity_nested?.last_name || ""}`.toLowerCase().includes(term)
      );
    }
    if (facultyFilter && isRecteur) {
      filtered = filtered.filter((row) => row.faculty_code === facultyFilter);
    }
    if (moratoireFilter !== null) {
      if (moratoireFilter) {
        filtered = filtered.filter((row) => (row.moratoires_actifs || 0) > 0);
      } else {
        filtered = filtered.filter((row) => (row.moratoires_actifs || 0) === 0);
      }
    }
    if (bourseFilter !== null) {
      if (bourseFilter) {
        filtered = filtered.filter((row) => (row.bourses_actives || 0) > 0);
      } else {
        filtered = filtered.filter((row) => (row.bourses_actives || 0) === 0);
      }
    }
    return filtered;
  }, [rows, searchTerm, facultyFilter, moratoireFilter, bourseFilter, isRecteur]);

  const uniqueFaculties = useMemo(() => {
    const faculties = new Set<string>();
    rows.forEach((row) => {
      if (row.faculty_code) {
        faculties.add(row.faculty_code);
      }
    });
    return Array.from(faculties).sort();
  }, [rows]);

  const totalStudents = filteredRows.length;
  const blockedCount = filteredRows.filter(
    (row) =>
      row.finance_status_effective === "Bloqué" ||
      row.finance_status === "Bloqué" ||
      row.finance_status_effective === "BLOQUE" ||
      row.finance_status === "BLOQUE"
  ).length;
  const blockedPercentage = totalStudents > 0 ? Math.round((blockedCount / totalStudents) * 100) : 0;

  const columns = useMemo<GridColDef[]>(() => {
    const baseColumns: GridColDef[] = [
      {
        field: "matricule_permanent",
        headerName: "Matricule",
        minWidth: 140,
        flex: 0.8,
      },
      {
        field: "nom_complet",
        headerName: "Nom",
        minWidth: 200,
        flex: 1.2,
        valueGetter: (params) => {
          const first = params.row.identity_nested?.first_name || "";
          const last = params.row.identity_nested?.last_name || "";
          return `${last} ${first}`.trim() || params.row.email || "—";
        },
      },
      {
        field: "program_name",
        headerName: "Programme",
        minWidth: 180,
        flex: 1,
        valueGetter: (params) => params.row.program_name || params.row.program_code || "—",
      },
      {
        field: "current_level",
        headerName: "Niveau",
        minWidth: 100,
        flex: 0.8,
        valueGetter: (params) => params.row.current_level || "—",
      },
      {
        field: "academic_status",
        headerName: "Statut Académique",
        minWidth: 150,
        flex: 1,
        renderCell: (params) => {
          const status = params.row.academic_status || "Actif";
          const color =
            status === "Actif"
              ? "success"
              : status === "Ajourné"
                ? "warning"
                : status === "Exclu"
                  ? "error"
                  : "default";
          return <Chip label={status} color={color} size="small" />;
        },
      },
      {
        field: "finance_status_effective",
        headerName: "Statut Finance",
        minWidth: 150,
        flex: 1,
        renderCell: (params) => {
          const status = params.row.finance_status_effective || params.row.finance_status;
          const normalizedStatus = status === "BLOQUE" ? "Bloqué" : status === "MORATOIRE" ? "Moratoire" : status;
          const color =
            normalizedStatus === "OK"
              ? "success"
              : normalizedStatus === "Bloqué"
                ? "error"
                : normalizedStatus === "Moratoire"
                  ? "warning"
                  : "default";
          return <Chip label={normalizedStatus} color={color} size="small" />;
        },
      },
      {
        field: "balance",
        headerName: "Solde",
        minWidth: 140,
        flex: 1,
        valueFormatter: (params) => `${Number(params.value || 0).toLocaleString("fr-FR")} XAF`,
        renderCell: (params) => {
          const balance = Number(params.value || 0);
          const hasBourse = (params.row.bourses_actives || 0) > 0;
          return (
            <Typography
              variant="body2"
              sx={{ color: balance > 0 ? "error.main" : "success.main", fontWeight: balance > 0 ? "bold" : "normal" }}
            >
              {hasBourse ? "Couvert par bourse" : `${Math.abs(balance).toLocaleString("fr-FR")} XAF`}
            </Typography>
          );
        },
      },
      {
        field: "bourses_actives",
        headerName: "Bourses actives",
        minWidth: 150,
        flex: 0.8,
        renderCell: (params) => {
          const count = params.row.bourses_actives || 0;
          if (count === 0) {
            return <Typography variant="body2" color="text.secondary">—</Typography>;
          }
          const hasActive = params.row.bourses_actives_data?.some((b: any) => b.statut === "Active");
          const hasSuspended = params.row.bourses_actives_data?.some((b: any) => b.statut === "Suspendue");
          const color = hasActive ? "success" : hasSuspended ? "warning" : "default";
          return <Chip label={`${count} bourse(s)`} color={color} size="small" />;
        },
      },
    ];

    if (!isStudent) {
      baseColumns.push({
        field: "actions",
        type: "actions",
        headerName: "Actions",
        width: 120,
        getActions: (params) => [
          <GridActionsCellItem
            key="view"
            icon={<Visibility />}
            label="Voir détails"
            onClick={() => {
              setSelectedStudentId(params.id as string);
              setDetailModalOpen(true);
            }}
          />,
          ...(isScolarite
            ? [
                <GridActionsCellItem
                  key="edit"
                  icon={<Edit />}
                  label="Modifier statut"
                  onClick={() => {
                    setSelectedStudentId(params.id as string);
                    const student = rows.find((r) => r.id === params.id);
                    setSelectedStudentStatus(student?.finance_status_effective || student?.finance_status || "OK");
                    setStatusModalOpen(true);
                  }}
                />,
              ]
            : []),
        ],
      });
    }

    return baseColumns;
  }, [isStudent, isScolarite, rows]);

  const handleValidateRegistrations = async () => {
    if (selectedRows.length === 0) {
      toast.error("Aucun étudiant sélectionné.");
      return;
    }

    const toastId = toast.loading(`Validation de ${selectedRows.length} inscription(s)...`);
    try {
      // Récupérer les registration_ids pour chaque étudiant sélectionné
      const registrationIds: number[] = [];
      for (const studentId of selectedRows) {
        const student = rows.find((r) => r.id === studentId);
        if (student?.registrations_admin && student.registrations_admin.length > 0) {
          const regId = student.registrations_admin[0].id;
          if (typeof regId === "number") {
            registrationIds.push(regId);
          }
        }
      }

      if (registrationIds.length === 0) {
        toast.error("Aucune inscription trouvée pour les étudiants sélectionnés.", { id: toastId });
        return;
      }

      // Appel à l'endpoint /api/registrations/validate/ avec les IDs
      await axios.post(
        "/api/registrations/validate/",
        { registration_ids: registrationIds },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Role-Active": activeRole,
          },
        }
      );
      toast.success("Inscriptions validées avec succès.", { id: toastId });
      setSelectedRows([]);
      // Recharger les données
      const response = await axios.get("/api/students/", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Role-Active": activeRole,
        },
      });
      const payload = response.data;
      const results: StudentRow[] = Array.isArray(payload) ? payload : payload.results || [];
      setRows(
        results.map((item: any) => ({
          id: String(item.id),
          identity_uuid: item.identity_uuid || item.identity,
          identity_nested: item.identity_nested,
          email: item.email || item.identity_nested?.email || "",
          matricule_permanent: item.matricule_permanent || item.matricule || "",
          date_entree: item.date_entree || "",
          program_code: item.program_code || "",
          program_name: item.program_name || "",
          faculty_code: item.faculty_code || "",
          finance_status: item.finance_status || "OK",
          finance_status_effective: item.finance_status_effective || item.finance_status,
          academic_status: item.academic_status || "Actif",
          balance: Number(item.balance || 0),
          current_level: item.registrations_admin?.[0]?.level || "",
          registrations_admin: item.registrations_admin || [],
        }))
      );
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Validation impossible.";
      toast.error(errorMsg, { id: toastId });
    }
  };

  const handleUpdateFinanceStatus = async (studentId: string, newStatus: string) => {
    const toastId = toast.loading("Mise à jour du statut financier...");
    try {
      await axios.put(
        `/api/students/${studentId}/finance-status/`,
        { finance_status: newStatus },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Role-Active": activeRole,
          },
        }
      );
      toast.success("Statut financier mis à jour.", { id: toastId });
      // Recharger les données
      const response = await axios.get("/api/students/", {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Role-Active": activeRole,
        },
      });
      const payload = response.data;
      const results: StudentRow[] = Array.isArray(payload) ? payload : payload.results || [];
      setRows(
        results.map((item: any) => ({
          id: String(item.id),
          identity_uuid: item.identity_uuid || item.identity,
          identity_nested: item.identity_nested,
          email: item.email || item.identity_nested?.email || "",
          matricule_permanent: item.matricule_permanent || item.matricule || "",
          date_entree: item.date_entree || "",
          program_code: item.program_code || "",
          program_name: item.program_name || "",
          faculty_code: item.faculty_code || "",
          finance_status: item.finance_status || "OK",
          finance_status_effective: item.finance_status_effective || item.finance_status,
          academic_status: item.academic_status || "Actif",
          balance: Number(item.balance || 0),
          current_level: item.registrations_admin?.[0]?.level || "",
          registrations_admin: item.registrations_admin || [],
        }))
      );
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Mise à jour impossible.";
      toast.error(errorMsg, { id: toastId });
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", mt: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && rows.length === 0) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      </Box>
    );
  }

  if (!activeRole || (!isRecteur && !isDoyen && !isStudent && !isFinance && !isScolarite)) {
    return (
      <Box>
        <Alert severity="warning">Accès réservé.</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Stack spacing={1} sx={{ mb: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Box>
            <Typography variant="h4">Gestion des étudiants</Typography>
            <Typography variant="body2" color="text.secondary">
              Suivi des inscriptions et de l'état financier par rôle.
            </Typography>
          </Box>
          {isScolarite && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setEnrollModalOpen(true)}
            >
              Inscrire un étudiant
            </Button>
          )}
        </Box>
      </Stack>

      {isRecteur && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">Effectif total</Typography>
                <Typography variant="h3">{totalStudents}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">Étudiants bloqués</Typography>
                <Typography variant="h3" color="error">
                  {blockedCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {blockedPercentage}% du total
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">Facultés</Typography>
                <Typography variant="h3">{uniqueFaculties.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6">Statut OK</Typography>
                <Typography variant="h3" color="success.main">
                  {totalStudents - blockedCount}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {(isRecteur || isDoyen || isScolarite || isFinance) && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
              <TextField
                placeholder="Rechercher (matricule, nom, prénom, email)"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                size="small"
                sx={{ flexGrow: 1, minWidth: 250 }}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
              {isRecteur && uniqueFaculties.length > 0 && (
                <Select
                  value={facultyFilter}
                  onChange={(e) => setFacultyFilter(e.target.value)}
                  displayEmpty
                  size="small"
                  sx={{ minWidth: 180 }}
                >
                  <MenuItem value="">Toutes les facultés</MenuItem>
                  {uniqueFaculties.map((faculty) => (
                    <MenuItem key={faculty} value={faculty}>
                      {faculty}
                    </MenuItem>
                  ))}
                </Select>
              )}
              <Select
                value={moratoireFilter === null ? "" : moratoireFilter ? "avec" : "sans"}
                onChange={(e) => {
                  const value = e.target.value;
                  setMoratoireFilter(value === "" ? null : value === "avec");
                }}
                displayEmpty
                size="small"
                sx={{ minWidth: 200 }}
              >
                <MenuItem value="">Tous les étudiants</MenuItem>
                <MenuItem value="avec">Avec moratoire actif</MenuItem>
                <MenuItem value="sans">Sans moratoire actif</MenuItem>
              </Select>
              <Select
                value={bourseFilter === null ? "" : bourseFilter ? "avec" : "sans"}
                onChange={(e) => {
                  const value = e.target.value;
                  setBourseFilter(value === "" ? null : value === "avec");
                }}
                displayEmpty
                size="small"
                sx={{ minWidth: 200 }}
              >
                <MenuItem value="">Tous les étudiants</MenuItem>
                <MenuItem value="avec">Avec bourse active</MenuItem>
                <MenuItem value="sans">Sans bourse active</MenuItem>
              </Select>
            </Box>
            <Box sx={{ height: 600 }}>
              <DataGrid
                rows={filteredRows}
                columns={columns}
                checkboxSelection={isDoyen || isScolarite}
                onRowSelectionModelChange={(selection) => setSelectedRows(selection.map(String))}
                paginationModel={paginationModel}
                onPaginationModelChange={setPaginationModel}
                pageSizeOptions={[10, 25, 50, 100]}
                onRowClick={(params) => {
                  if (!isStudent) {
                    setSelectedStudentId(params.id as string);
                    setDetailModalOpen(true);
                  }
                }}
                slots={{ toolbar: GridToolbar }}
                slotProps={{
                  toolbar: {
                    showQuickFilter: true,
                    quickFilterProps: { debounceMs: 500 },
                  },
                }}
                initialState={{
                  pagination: {
                    paginationModel: { pageSize: 10 },
                  },
                }}
              />
            </Box>
          </CardContent>
        </Card>
      )}

      {isDoyen && selectedRows.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Validation des inscriptions
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {selectedRows.length} inscription(s) sélectionnée(s) pour validation.
            </Typography>
            <Button variant="contained" startIcon={<CheckCircle />} onClick={handleValidateRegistrations}>
              Valider les inscriptions sélectionnées
            </Button>
          </CardContent>
        </Card>
      )}

      {isFinance && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Étudiants bloqués
            </Typography>
            {filteredRows.filter(
              (row) =>
                row.finance_status_effective === "Bloqué" ||
                row.finance_status === "Bloqué" ||
                row.finance_status_effective === "BLOQUE" ||
                row.finance_status === "BLOQUE"
            ).length === 0 ? (
              <Alert severity="info">Aucun étudiant bloqué.</Alert>
            ) : (
              <Box>
                {filteredRows
                  .filter(
                    (row) =>
                      row.finance_status_effective === "Bloqué" ||
                      row.finance_status === "Bloqué" ||
                      row.finance_status_effective === "BLOQUE" ||
                      row.finance_status === "BLOQUE"
                  )
                  .map((row) => (
                    <Box
                      key={row.id}
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        mb: 2,
                        p: 2,
                        border: "1px solid",
                        borderColor: "divider",
                        borderRadius: 1,
                      }}
                    >
                      <Box>
                        <Typography variant="subtitle1">
                          {row.identity_nested
                            ? `${row.identity_nested.last_name} ${row.identity_nested.first_name}`
                            : row.email}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {row.matricule_permanent} • Solde : {Math.abs(row.balance).toLocaleString("fr-FR")} XAF
                        </Typography>
                      </Box>
                      <Button
                        variant="outlined"
                        startIcon={<Block />}
                        onClick={() => handleUpdateFinanceStatus(row.id, "Moratoire")}
                      >
                        Débloquer (Moratoire)
                      </Button>
                    </Box>
                  ))}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {isStudent && (
        <Grid container spacing={3}>
          {filteredRows.length === 0 ? (
            <Grid item xs={12}>
              <Alert severity="info">Aucune inscription trouvée.</Alert>
            </Grid>
          ) : (
            filteredRows.map((row) => (
              <Grid item xs={12} key={row.id}>
                <Card
                  sx={{
                    bgcolor: row.balance > 0 ? "error.light" : "success.light",
                    color: row.balance > 0 ? "error.contrastText" : "success.contrastText",
                  }}
                >
                  <CardContent>
                    <Typography variant="h5" gutterBottom>
                      Mon dossier étudiant
                    </Typography>
                    <Divider sx={{ my: 2, bgcolor: "rgba(255,255,255,0.3)" }} />
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                          Nom complet
                        </Typography>
                        <Typography variant="h6">
                          {row.identity_nested
                            ? `${row.identity_nested.first_name} ${row.identity_nested.last_name}`
                            : row.email}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                          Matricule
                        </Typography>
                        <Typography variant="h6">{row.matricule_permanent}</Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                          Programme
                        </Typography>
                        <Typography variant="body1">{row.program_name || row.program_code || "—"}</Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                          Niveau
                        </Typography>
                        <Typography variant="body1">{row.current_level || "—"}</Typography>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                          Statut financier
                        </Typography>
                        <Chip
                          label={row.finance_status_effective || row.finance_status}
                          color={
                            row.finance_status_effective === "OK" || row.finance_status === "OK"
                              ? "success"
                              : row.finance_status_effective === "Bloqué" ||
                                  row.finance_status === "Bloqué" ||
                                  row.finance_status_effective === "BLOQUE" ||
                                  row.finance_status === "BLOQUE"
                                ? "error"
                                : "warning"
                          }
                          size="small"
                          sx={{ bgcolor: "rgba(255,255,255,0.2)" }}
                        />
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>
                          Solde
                        </Typography>
                        <Typography variant="h4" sx={{ fontWeight: "bold", mt: 1 }}>
                          {Math.abs(row.balance).toLocaleString("fr-FR")} XAF
                        </Typography>
                      </Grid>
                      {row.balance > 0 && (
                        <Grid item xs={12}>
                          <Button
                            variant="contained"
                            fullWidth
                            size="large"
                            sx={{
                              bgcolor: "rgba(255,255,255,0.9)",
                              color: "error.main",
                              "&:hover": { bgcolor: "rgba(255,255,255,1)" },
                            }}
                            onClick={() => toast("Fonctionnalité de paiement à venir", { icon: "💳" })}
                          >
                            Payer maintenant
                          </Button>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
            ))
          )}
        </Grid>
      )}

      {isStudent && filteredRows.length > 0 && (
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {filteredRows.map((row) => {
            const boursesData = studentBourses[row.id] || [];
            const totalBourses = boursesData.reduce((sum, b) => sum + b.montant, 0);
            const hasActiveBourse = boursesData.some((b) => b.statut === "Active");
            
            return (
              <Grid item xs={12} key={`bourses-${row.id}`}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Mes bourses
                    </Typography>
                    {boursesData.length > 0 ? (
                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                          Total des bourses actives: {totalBourses.toLocaleString("fr-FR")} XAF
                        </Typography>
                        {hasActiveBourse && row.balance <= 0 && (
                          <Alert severity="success" sx={{ mb: 2 }}>
                            Votre solde est couvert par une bourse active.
                          </Alert>
                        )}
                        <TableContainer component={Paper} variant="outlined">
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Type</TableCell>
                                <TableCell align="right">Montant</TableCell>
                                <TableCell>Statut</TableCell>
                                <TableCell>Date fin</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {boursesData.map((bourse) => (
                                <TableRow key={bourse.id}>
                                  <TableCell>
                                    <Chip
                                      label={bourse.type_bourse}
                                      size="small"
                                      color={bourse.statut === "Active" ? "success" : bourse.statut === "Suspendue" ? "warning" : "default"}
                                    />
                                  </TableCell>
                                  <TableCell align="right">
                                    {bourse.montant.toLocaleString("fr-FR")} XAF
                                  </TableCell>
                                  <TableCell>
                                    <Chip
                                      label={bourse.statut}
                                      size="small"
                                      color={bourse.statut === "Active" ? "success" : bourse.statut === "Suspendue" ? "warning" : "error"}
                                    />
                                  </TableCell>
                                  <TableCell>
                                    {bourse.date_fin_validite
                                      ? new Date(bourse.date_fin_validite).toLocaleDateString("fr-FR")
                                      : "—"}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Aucune bourse active.
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      <StudentDetailModal
        open={detailModalOpen}
        onClose={() => {
          setDetailModalOpen(false);
          setSelectedStudentId(null);
        }}
        studentId={selectedStudentId}
      />
      
      <StudentEnrollModal
        open={enrollModalOpen}
        onClose={() => {
          setEnrollModalOpen(false);
        }}
        onSuccess={() => {
          setEnrollModalOpen(false);
          // Rafraîchir la liste
          window.location.reload();
        }}
      />
      
      <StudentStatusModal
        open={statusModalOpen}
        onClose={() => {
          setStatusModalOpen(false);
          setSelectedStudentId(null);
        }}
        studentId={selectedStudentId}
        currentStatus={selectedStudentStatus}
        onSuccess={() => {
          setStatusModalOpen(false);
          setSelectedStudentId(null);
          // Rafraîchir la liste
          window.location.reload();
        }}
      />
    </Box>
  );
};

export default Students;
