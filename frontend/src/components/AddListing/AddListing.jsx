import { useState } from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import AddIcon from "@mui/icons-material/Add";
import { useCreateListingManualMutation } from "../../store/api/api";
import { primaryIconButton } from "../../styles/styles";
import { t } from "../../i18n";
import { Box } from "@mui/material";

const dialogPaperSx = {
  backgroundColor: "#424242",
  color: "#E0E0E0",
  borderRadius: "1.5rem",
};

const textFieldSx = {
  mt: 2,
  "& .MuiOutlinedInput-root": {
    borderRadius: "1rem",
    color: "#E0E0E0",
    "& fieldset": { borderColor: "#626262" },
    "&:hover fieldset": { borderColor: "#16A34A" },
    "&.Mui-focused fieldset": { borderColor: "#16A34A" },
  },
  "& .MuiInputLabel-root": { color: "#BDBDBD" },
  "& .MuiInputLabel-root.Mui-focused": { color: "#16A34A" },
};

const BEDROOM_OPTIONS = ["0", "1", "2", "3"];

const initialForm = {
  listing_id: "",
  title: "",
  resort_codes: "",
  bedrooms: "0",
};

export const AddListing = ({ alertRef }) => {
  const [createListing] = useCreateListingManualMutation();

  const [form, setForm] = useState(initialForm);
  const [formOpen, setFormOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const isFormValid =
    form.listing_id.trim() !== "" &&
    form.title.trim() !== "" &&
    form.resort_codes.trim() !== "";

  const handleOpen = () => {
    setForm(initialForm);
    setFormOpen(true);
  };

  const handleCloseForm = () => {
    setFormOpen(false);
  };

  const handleAccept = () => {
    if (!isFormValid) return;
    setFormOpen(false);
    setConfirmOpen(true);
  };

  const handleCancelConfirm = () => {
    setConfirmOpen(false);
    setFormOpen(true);
  };

  const handleConfirmCreate = async () => {
    setConfirmOpen(false);
    const resortCodes = form.resort_codes
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);

    try {
      await createListing({
        listing_id: form.listing_id.trim(),
        title: form.title.trim(),
        resort_codes: resortCodes,
        bedrooms: form.bedrooms,
      }).unwrap();
      alertRef?.current?.showSuccess(t.addListing.createSuccess);
    } catch (err) {
      alertRef?.current?.showError(
        err?.data?.detail || t.addListing.createError,
      );
    }
  };

  return (
    <>
      <Button
        variant="contained"
        onClick={handleOpen}
        startIcon={<AddIcon />}
        sx={{ ...primaryIconButton, "& svg": { width: 20, height: 20 } }}
      >
        {t.addListing.openButton}
      </Button>

      {/* Modal 1: formulario */}
      <Dialog
        open={formOpen}
        onClose={handleCloseForm}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.addListing.dialogTitle}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            size="small"
            label={t.addListing.listingIdLabel}
            placeholder={t.addListing.listingIdPlaceholder}
            value={form.listing_id}
            onChange={updateField("listing_id")}
            autoFocus
            sx={textFieldSx}
          />
          <TextField
            fullWidth
            size="small"
            label={t.addListing.titleLabel}
            placeholder={t.addListing.titlePlaceholder}
            value={form.title}
            onChange={updateField("title")}
            sx={textFieldSx}
          />
          <Box
            sx={{
              display: "flex",
              gap: 3,
            }}
          >
            <TextField
              fullWidth
              size="small"
              label={t.addListing.resortCodesLabel}
              placeholder={t.addListing.resortCodesPlaceholder}
              value={form.resort_codes}
              onChange={updateField("resort_codes")}
              sx={textFieldSx}
            />
            <TextField
              fullWidth
              size="small"
              select
              label={t.addListing.bedroomsLabel}
              value={form.bedrooms}
              onChange={updateField("bedrooms")}
              sx={textFieldSx}
            >
              {BEDROOM_OPTIONS.map((opt) => (
                <MenuItem key={opt} value={opt}>
                  {opt === "0"
                    ? t.listingTable.studio
                    : t.listingTable.bedroomCount(opt)}
                </MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleAccept}
            variant="contained"
            disabled={!isFormValid}
            sx={{
              borderRadius: "1rem",
              textTransform: "none",
              backgroundColor: "#16A34A",
              "&:hover": { backgroundColor: "#15803d" },
            }}
          >
            {t.addListing.submitButton}
          </Button>
          <Button
            onClick={handleCloseForm}
            sx={{ color: "#BDBDBD", borderRadius: "1rem" }}
          >
            {t.addListing.cancelButton}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal 2: confirmación */}
      <Dialog
        open={confirmOpen}
        onClose={handleCancelConfirm}
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.addListing.confirmTitle}</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: "#BDBDBD" }}>
            {t.addListing.confirmMessage(form.listing_id.trim())}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleConfirmCreate}
            variant="contained"
            sx={{
              borderRadius: "1rem",
              textTransform: "none",
              backgroundColor: "#16A34A",
              "&:hover": { backgroundColor: "#15803d" },
            }}
          >
            {t.addListing.confirmButton}
          </Button>
          <Button
            onClick={handleCancelConfirm}
            sx={{ color: "#BDBDBD", borderRadius: "1rem" }}
          >
            {t.addListing.confirmCancel}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
