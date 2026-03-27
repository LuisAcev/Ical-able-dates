import { useState, useEffect } from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  useGetIcalBaseUrlQuery,
  useSetIcalBaseUrlMutation,
} from "../../store/api/api";
import { primaryIconButton } from "../../styles/styles";
import { t } from "../../i18n";

const dialogPaperSx = {
  backgroundColor: "#424242",
  color: "#E0E0E0",
  borderRadius: "12px",
};

export const IcalBaseUrlInput = ({ alertRef }) => {
  const { data } = useGetIcalBaseUrlQuery();
  const [setBaseUrl] = useSetIcalBaseUrlMutation();

  const [value, setValue] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    if (data?.base_url !== undefined) {
      setValue(data.base_url);
    }
  }, [data?.base_url]);

  const handleOpenEdit = () => {
    setValue(data?.base_url ?? "");
    setEditOpen(true);
  };

  const handleCloseEdit = () => {
    setEditOpen(false);
  };

  const handleAccept = () => {
    setEditOpen(false);
    setConfirmOpen(true);
  };

  const handleCancelConfirm = () => {
    setConfirmOpen(false);
    setEditOpen(true);
  };

  const handleConfirmSave = async () => {
    setConfirmOpen(false);
    try {
      await setBaseUrl(value.trim()).unwrap();
      alertRef?.current?.showSuccess(t.icalBaseUrl.saveSuccess);
    } catch {
      alertRef?.current?.showError(t.icalBaseUrl.saveError);
    }
  };

  return (
    <>
      <Button
        variant="contained"
        onClick={handleOpenEdit}
        startIcon={<SettingsIcon />}
        sx={{ ...primaryIconButton, "& svg": { width: 20, height: 20 } }}
      >
        {t.icalBaseUrl.editButton}
      </Button>

      {/* Modal 1: editar URL */}
      <Dialog
        open={editOpen}
        onClose={handleCloseEdit}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.icalBaseUrl.dialogTitle}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            size="small"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAccept()}
            placeholder={t.icalBaseUrl.placeholder}
            label={t.icalBaseUrl.label}
            autoFocus
            sx={{
              mt: 1,
              "& .MuiOutlinedInput-root": {
                color: "#E0E0E0",
                "& fieldset": { borderColor: "#626262" },
                "&:hover fieldset": { borderColor: "#16A34A" },
                "&.Mui-focused fieldset": { borderColor: "#16A34A" },
              },
              "& .MuiInputLabel-root": { color: "#BDBDBD" },
              "& .MuiInputLabel-root.Mui-focused": { color: "#16A34A" },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleAccept}
            variant="contained"
            sx={{
              borderRadius: "1rem",
              textTransform: "none",
              backgroundColor: "#16A34A",
              "&:hover": { backgroundColor: "#15803d" },
            }}
          >
            {t.icalBaseUrl.saveButton}
          </Button>
          <Button onClick={handleCloseEdit} sx={{ color: "#BDBDBD", borderRadius: "1rem" }}>
            {t.icalBaseUrl.cancelButton}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal 2: confirmación */}
      <Dialog
        open={confirmOpen}
        onClose={handleCancelConfirm}
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.icalBaseUrl.confirmTitle}</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: "#BDBDBD" }}>
            {t.icalBaseUrl.confirmMessage}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleConfirmSave}
            variant="contained"
            sx={{
              borderRadius: "1rem",
              textTransform: "none",
              backgroundColor: "#ef5350",
              "&:hover": { backgroundColor: "#c62828" },
            }}
          >
            {t.icalBaseUrl.confirmButton}
          </Button>
          <Button onClick={handleCancelConfirm} sx={{ color: "#BDBDBD", borderRadius: "1rem" }}>
            {t.icalBaseUrl.confirmCancel}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
