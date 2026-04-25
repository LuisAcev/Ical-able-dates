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
import { primaryIconButton, dialogPaperSx, greenButtonSx, cancelButtonSx, dialogTextFieldSx } from "../../styles/styles";
import { t } from "../../i18n";
import { validateResortCodes } from "../../utils/listingUtils";
import { Box } from "@mui/material";

const textFieldSx = { mt: 2, ...dialogTextFieldSx };

const BEDROOM_OPTIONS = ["0", "1", "2", "3"];

const initialForm = {
  listing_id: "",
  title: "",
  resort_codes: "",
  bedrooms: "0",
  address: "",
  state: "",
};

export const AddListing = ({ alertRef }) => {
  const [createListing] = useCreateListingManualMutation();

  const [form, setForm] = useState(initialForm);
  const [formOpen, setFormOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const updateField = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const resortCodesInvalid =
    form.resort_codes.trim() !== "" && !validateResortCodes(form.resort_codes);

  const isFormValid =
    form.listing_id.trim() !== "" &&
    form.title.trim() !== "" &&
    form.resort_codes.trim() !== "" &&
    !resortCodesInvalid;

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
        address: form.address.trim(),
        state: form.state.trim(),
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
        startIcon={<AddIcon sx={{ width: 20, height: 20 }} />}
        sx={{
          ...primaryIconButton,
          minWidth: "auto",
          "& svg": { width: 20, height: 20 },
          "& .MuiButton-startIcon": { mx: { xs: 0, md: "inherit" } },
          px: { xs: "10px", md: "16px" },
        }}
      >
        <Box component="span" sx={{ display: { xs: "none", md: "inline" } }}>
          {t.addListing.openButton}
        </Box>
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
          <Box sx={{ display: "flex", gap: 3 }}>
            <TextField
              fullWidth
              size="small"
              label={t.addListing.resortCodesLabel}
              placeholder={t.addListing.resortCodesPlaceholder}
              value={form.resort_codes}
              onChange={updateField("resort_codes")}
              error={resortCodesInvalid}
              helperText={resortCodesInvalid ? t.addListing.resortCodesError : ""}
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
          <Box sx={{ display: "flex", gap: 3 }}>
            <TextField
              fullWidth
              size="small"
              label={t.addListing.addressLabel}
              placeholder={t.addListing.addressPlaceholder}
              value={form.address}
              onChange={updateField("address")}
              sx={textFieldSx}
            />
            <TextField
              fullWidth
              size="small"
              label={t.addListing.stateLabel}
              placeholder={t.addListing.statePlaceholder}
              value={form.state}
              onChange={updateField("state")}
              sx={textFieldSx}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button onClick={handleAccept} variant="contained" disabled={!isFormValid} sx={greenButtonSx}>
            {t.addListing.submitButton}
          </Button>
          <Button onClick={handleCloseForm} sx={cancelButtonSx}>
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
          <Button onClick={handleConfirmCreate} variant="contained" sx={greenButtonSx}>
            {t.addListing.confirmButton}
          </Button>
          <Button onClick={handleCancelConfirm} sx={cancelButtonSx}>
            {t.addListing.confirmCancel}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
