import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  CircularProgress,
  Box,
} from "@mui/material";
import toast from "react-hot-toast";
import axios from "axios";

import { useAuth } from "../context/AuthContext";

interface StudentStatusModalProps {
  open: boolean;
  onClose: () => void;
  studentId: string | null;
  currentStatus: string;
  onSuccess?: () => void;
}

const StudentStatusModal: React.FC<StudentStatusModalProps> = ({
  open,
  onClose,
  studentId,
  currentStatus,
  onSuccess,
}) => {
  const { token, activeRole } = useAuth();
  const [loading, setLoading] = useState(false);
  const [newStatus, setNewStatus] = useState(currentStatus);

  React.useEffect(() => {
    if (open) {
      setNewStatus(currentStatus);
    }
  }, [open, currentStatus]);

  const handleSubmit = async () => {
    if (!studentId || !newStatus || newStatus === currentStatus) {
      onClose();
      return;
    }

    setLoading(true);
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
      toast.success("Statut financier mis à jour");
      onSuccess?.();
      onClose();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Erreur lors de la mise à jour";
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Modifier le statut financier</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <TextField
            select
            label="Nouveau statut"
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value)}
            fullWidth
            required
          >
            <MenuItem value="OK">OK</MenuItem>
            <MenuItem value="Bloqué">Bloqué</MenuItem>
            <MenuItem value="Moratoire">Moratoire</MenuItem>
          </TextField>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Annuler
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading || newStatus === currentStatus}>
          {loading ? <CircularProgress size={20} /> : "Enregistrer"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default StudentStatusModal;
