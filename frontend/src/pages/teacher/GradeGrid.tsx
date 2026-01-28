import React, { useCallback, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, ValueGetterParams } from "ag-grid-community";
import {
  Box,
  Button,
  Alert,
  Stack,
  Typography,
} from "@mui/material";

import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";

type GradeRow = {
  id: string;
  student: string;
  ueCode: string;
  cc: number;
  tp: number;
  exam: number;
  blocked: boolean;
};

const TEACHER_ROLE = "USER_TEACHER";
const SCOPE_STORAGE_KEY = "teacher_scope";

const averageGetter = (params: ValueGetterParams<GradeRow, number>) => {
  const data = params.data;
  if (!data) {
    return 0;
  }
  const avg = (data.cc + data.tp + data.exam) / 3;
  return Number.isFinite(avg) ? Number(avg.toFixed(2)) : 0;
};

const GradeGrid: React.FC = () => {
  const { activeRole } = useAuth();
  const [rows, setRows] = useState<GradeRow[]>([
    {
      id: "1",
      student: "KONE Salif",
      ueCode: "FSG_UE_MATH",
      cc: 12,
      tp: 9,
      exam: 14,
      blocked: true,
    },
    {
      id: "2",
      student: "DIA Awa",
      ueCode: "FSG_UE_INFO",
      cc: 15,
      tp: 12,
      exam: 13,
      blocked: false,
    },
  ]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const teacherScope = useMemo(() => {
    const raw = localStorage.getItem(SCOPE_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    return raw
      .split(",")
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean);
  }, []);

  const canEditRole = activeRole === TEACHER_ROLE;

  const canEditRow = useCallback(
    (row: GradeRow) => {
      if (!canEditRole) {
        return false;
      }
      if (teacherScope.length === 0) {
        return false;
      }
      return teacherScope.includes(row.ueCode.toUpperCase());
    },
    [canEditRole, teacherScope]
  );

  const columnDefs = useMemo<ColDef<GradeRow>[]>(
    () => [
      { field: "student", headerName: "Étudiant", editable: false, flex: 1 },
      { field: "cc", headerName: "Note CC", editable: true, width: 120 },
      { field: "tp", headerName: "TP", editable: true, width: 120 },
      { field: "exam", headerName: "Exam", editable: true, width: 120 },
      {
        headerName: "Moyenne",
        valueGetter: averageGetter,
        editable: false,
        width: 140,
      },
    ],
    []
  );

  const defaultColDef = useMemo<ColDef<GradeRow>>(
    () => ({
      sortable: true,
      resizable: true,
      editable: (params) => canEditRow(params.data as GradeRow),
    }),
    [canEditRow]
  );

  const onCellValueChanged = useCallback(
    (event: { data: GradeRow }) => {
      const updated = rows.map((row) => {
        if (row.id !== event.data.id) {
          return row;
        }
        const blocked = row.tp < 10;
        return { ...row, blocked };
      });
      setRows(updated);
    },
    [rows]
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    setMessage(null);
    try {
      await api.post(
        "/grades/bulk-update/",
        { rows },
        {
          headers: {
            "X-Teacher-Scope": teacherScope.join(","),
          },
        }
      );
      setMessage("Notes enregistrées avec succès.");
    } catch {
      setMessage("Échec de l’enregistrement des notes.");
    } finally {
      setSaving(false);
    }
  }, [rows, teacherScope]);

  if (!canEditRole) {
    return (
      <Alert severity="warning">
        Accès refusé : seuls les enseignants peuvent saisir des notes.
      </Alert>
    );
  }

  if (teacherScope.length === 0) {
    return (
      <Alert severity="warning">
        Aucun scope disponible. Contactez l’administration.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5">Saisie des notes</Typography>
      {message && <Alert severity="info">{message}</Alert>}
      <Box className="ag-theme-quartz" sx={{ height: 420, width: "100%" }}>
        <AgGridReact
          rowData={rows}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          stopEditingWhenCellsLoseFocus
          singleClickEdit
          onCellValueChanged={onCellValueChanged}
          rowClassRules={{
            "ag-row-blocked": (params) => Boolean(params.data?.blocked),
          }}
        />
      </Box>
      <Button variant="contained" onClick={handleSave} disabled={saving}>
        {saving ? "Enregistrement..." : "Enregistrer"}
      </Button>
    </Stack>
  );
};

export default GradeGrid;
