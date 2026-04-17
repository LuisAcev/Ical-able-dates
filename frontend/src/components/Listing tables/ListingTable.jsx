import { useState, useRef, useEffect } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import { ListingCircularProgress } from "../ListingCircularProgress/ListingCircularProgress";
import Chip from "@mui/material/Chip";
import { AlertInline } from "../AlertInline/AlertInline";
import Tooltip from "@mui/material/Tooltip";
import RotateLeftIcon from "@mui/icons-material/RotateLeft";
import LockIcon from "@mui/icons-material/Lock";
import LockOpenIcon from "@mui/icons-material/LockOpen";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import VisibilityIcon from "@mui/icons-material/Visibility";
import CheckIcon from "@mui/icons-material/Check";
import EditIcon from "@mui/icons-material/Edit";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { IcalDatesModal } from "../IcalDatesModal/IcalDatesModal";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import { DataGrid } from "@mui/x-data-grid";
import {
  dataGridTable,
  actionIconButton,
  resortCodes,
} from "../../styles/styles";
import {
  useUpdateListingDataMutation,
  useDeleteListingMutation,
} from "../../store/api/api";
import { t, dateLocale } from "../../i18n";

const RESORT_CODE_RE = /^[A-Z0-9]{2,10}$/i;
const validateResortCodes = (value) =>
  value.trim() === "" ||
  value.split(",").map((c) => c.trim()).filter(Boolean).every((c) => RESORT_CODE_RE.test(c));

const extractErrorMessage = (err, fallback) => {
  const detail = err?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((d) => d.msg || d.message || JSON.stringify(d))
      .join(", ");
  return fallback;
};

const dialogPaperSx = {
  backgroundColor: "#424242",
  color: "#E0E0E0",
  borderRadius: "1.5rem",
};

const greenButtonSx = {
  borderRadius: "1rem",
  textTransform: "none",
  backgroundColor: "#16A34A",
  "&:hover": { backgroundColor: "#15803d" },
};

const cancelButtonSx = { color: "#BDBDBD", borderRadius: "1rem" };

const deleteButtonSx = {
  borderRadius: "1rem",
  textTransform: "none",
  backgroundColor: "#ef5350",
  "&:hover": { backgroundColor: "#c62828" },
};

const textFieldSx = {
  mt: 1.5,
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

const formatDate = (iso) => {
  if (!iso) return t.listingTable.never;
  const d = new Date(iso);
  return d.toLocaleString(dateLocale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const bedroomLabel = (val) => {
  const n = parseInt(val, 10);
  if (isNaN(n) || n === 0) return t.listingTable.studio;
  return t.listingTable.bedroomCount(n);
};

export const ListingTable = ({
  listings,
  loading,
  error,
  updatingIds,
  handleUpdateOne,
  handleToggleIcal,
  alertRef,
}) => {
  const [confirmDialog, setConfirmDialog] = useState({
    open: false,
    listingId: null,
    currentEnabled: true,
  });

  const [calendarDialog, setCalendarDialog] = useState({ open: false, listingId: null });
  const [urlDialog, setUrlDialog] = useState({ open: false, url: "" });
  const [copiedId, setCopiedId] = useState(null);
  const [urlDialogCopied, setUrlDialogCopied] = useState(false);
  const copyTimerRef = useRef(null);
  const dialogCopyTimerRef = useRef(null);

  // Edit modal state
  const [editDialog, setEditDialog] = useState({ open: false, listing: null });
  const [editForm, setEditForm] = useState({
    title: "",
    resort_codes: "",
    bedrooms: "",
    address: "",
    state: "",
  });
  const [confirmUpdate, setConfirmUpdate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const [updateListingData] = useUpdateListingDataMutation();
  const [deleteListing] = useDeleteListingMutation();

  useEffect(() => {
    const copyTimer = copyTimerRef;
    const dialogCopyTimer = dialogCopyTimerRef;
    return () => {
      clearTimeout(copyTimer.current);
      clearTimeout(dialogCopyTimer.current);
    };
  }, []);

  // --- Toggle iCal handlers ---
  const handleOpenConfirm = (listingId, currentEnabled) => {
    setConfirmDialog({ open: true, listingId, currentEnabled });
  };

  const handleCloseConfirm = () => {
    setConfirmDialog({ open: false, listingId: null, currentEnabled: true });
  };

  const handleConfirmToggle = () => {
    handleToggleIcal(confirmDialog.listingId, !confirmDialog.currentEnabled);
    handleCloseConfirm();
  };

  // --- Copy URL handlers ---
  const handleCopyUrl = async (url, listingId) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(listingId);
      clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => setCopiedId(null), 2000);
    } catch {
      alertRef?.current?.showError(t.alert.copyError);
    }
  };

  const handleOpenUrlDialog = (url) => {
    setUrlDialog({ open: true, url });
    setUrlDialogCopied(false);
  };

  const handleCloseUrlDialog = () => {
    setUrlDialog({ open: false, url: "" });
  };

  const handleCopyFromDialog = async () => {
    try {
      await navigator.clipboard.writeText(urlDialog.url);
      setUrlDialogCopied(true);
      clearTimeout(dialogCopyTimerRef.current);
      dialogCopyTimerRef.current = setTimeout(
        () => setUrlDialogCopied(false),
        2000,
      );
    } catch {
      alertRef?.current?.showError(t.alert.copyError);
    }
  };

  // --- Edit handlers ---
  const handleOpenEdit = (row) => {
    setEditDialog({ open: true, listing: row });
    setEditForm({
      title: row.title || "",
      resort_codes: (row.resort_codes || []).join(", "),
      bedrooms: row.bedrooms || "0",
      address: row.address || "",
      state: row.state || "",
    });
  };

  const handleCloseEdit = () => {
    setEditDialog({ open: false, listing: null });
    setConfirmUpdate(false);
    setConfirmDelete(false);
  };

  const handleRequestUpdate = () => {
    setEditDialog((prev) => ({ ...prev, open: false }));
    setConfirmUpdate(true);
  };

  const handleCancelUpdate = () => {
    setConfirmUpdate(false);
    setEditDialog((prev) => ({ ...prev, open: true }));
  };

  const handleConfirmUpdate = async () => {
    setConfirmUpdate(false);
    const lid = editDialog.listing.listing_id;
    try {
      await updateListingData({
        listingId: lid,
        title: editForm.title.trim(),
        resort_codes: editForm.resort_codes
          .split(",")
          .map((c) => c.trim().toUpperCase())
          .filter(Boolean),
        bedrooms: editForm.bedrooms,
        address: editForm.address.trim(),
        state: editForm.state.trim(),
      }).unwrap();
      alertRef?.current?.showSuccess(t.editListing.updateSuccess);
      handleCloseEdit();
    } catch (err) {
      alertRef?.current?.showError(
        extractErrorMessage(err, t.editListing.updateError),
      );
    }
  };

  const handleRequestDelete = () => {
    setEditDialog((prev) => ({ ...prev, open: false }));
    setConfirmDelete(true);
  };

  const handleCancelDelete = () => {
    setConfirmDelete(false);
    setEditDialog((prev) => ({ ...prev, open: true }));
  };

  const handleConfirmDelete = async () => {
    setConfirmDelete(false);
    const lid = editDialog.listing.listing_id;
    try {
      await deleteListing(lid).unwrap();
      alertRef?.current?.showSuccess(t.editListing.deleteSuccess);
      handleCloseEdit();
    } catch (err) {
      alertRef?.current?.showError(
        extractErrorMessage(err, t.editListing.deleteError),
      );
    }
  };

  const columns = [
    {
      field: "listing_id",
      headerName: t.listingTable.listingId,
      flex: 1,
      align: "center",
      headerAlign: "center",
    },
    {
      field: "title",
      headerName: t.listingTable.resortName,
      flex: 1,
      minWidth: 200,
      align: "left",
      headerAlign: "center",
      renderCell: (params) =>
        params.value || (
          <em style={{ color: "#999" }}>{t.listingTable.noTitle}</em>
        ),
    },
    {
      field: "resort_codes",
      headerName: t.listingTable.resortCodes,
      width: 180,
      align: "center",
      headerAlign: "center",
      renderCell: (params) =>
        (params.value || []).map((code) => (
          <Chip
            key={code}
            label={code}
            size="small"
            variant="outlined"
            sx={resortCodes}
          />
        )),
    },
    {
      field: "bedrooms",
      headerName: t.listingTable.bedrooms,
      width: 150,
      align: "center",
      headerAlign: "center",
      renderCell: (params) => bedroomLabel(params.value),
    },
    {
      field: "state",
      headerName: t.listingTable.state,
      width: 150,
      align: "center",
      headerAlign: "center",
      renderCell: (params) =>
        params.value || <em style={{ color: "#999" }}>—</em>,
    },
    {
      field: "last_updated",
      headerName: t.listingTable.lastUpdated,
      align: "Left",
      headerAlign: "center",
      width: 200,
      renderCell: (params) => {
        const lastError = params.row.last_error;
        return (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box sx={{ width: 22, display: "flex", alignItems: "center", flexShrink: 0 }}>
              {lastError && (
                <Tooltip title={t.listingTable.lastErrorTooltip} arrow>
                  <WarningAmberIcon sx={{ color: "#ffa726", fontSize: 18 }} />
                </Tooltip>
              )}
            </Box>
            {formatDate(params.value)}
          </Box>
        );
      },
    },
    {
      field: "ical_url",
      headerName: t.listingTable.icalUrlHeader,
      width: 130,
      align: "center",
      headerAlign: "center",
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const url = params.value;
        const lid = params.row.listing_id;
        if (!url) {
          return (
            <Box sx={{ color: "#777", fontSize: 12 }}>
              {t.listingTable.noUrlConfigured}
            </Box>
          );
        }
        const isCopied = copiedId === lid;
        return (
          <Box
            sx={{
              display: "flex",
              gap: 0.5,
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
              paddingTop: "0.5rem",
            }}
          >
            <Tooltip
              title={
                isCopied ? t.listingTable.copied : t.listingTable.copyTooltip
              }
              arrow
            >
              <IconButton
                aria-label={t.listingTable.copyTooltip}
                onClick={() => handleCopyUrl(url, lid)}
                size="small"
                sx={{
                  color: isCopied ? "#66bb6a" : "#90caf9",
                  "&:hover": { backgroundColor: "rgba(144, 202, 249, 0.15)" },
                }}
              >
                {isCopied ? (
                  <CheckIcon fontSize="small" />
                ) : (
                  <ContentCopyIcon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
            <Tooltip title={t.listingTable.viewUrlTooltip} arrow>
              <IconButton
                aria-label={t.listingTable.viewUrlTooltip}
                onClick={() => handleOpenUrlDialog(url)}
                size="small"
                sx={{
                  color: "#ce93d8",
                  "&:hover": { backgroundColor: "rgba(206, 147, 216, 0.15)" },
                }}
              >
                <VisibilityIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        );
      },
    },
    {
      field: "ical_dates",
      headerName: t.icalDates.columnHeader,
      width: 100,
      align: "center",
      headerAlign: "center",
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Tooltip title={t.icalDates.openTooltip} arrow>
          <IconButton
            aria-label={t.icalDates.openTooltip}
            onClick={() => setCalendarDialog({ open: true, listingId: params.row.listing_id })}
            sx={{
              color: "#ce93d8",
              "&:hover": { backgroundColor: "rgba(206, 147, 216, 0.15)" },
            }}
          >
            <CalendarMonthIcon />
          </IconButton>
        </Tooltip>
      ),
    },
    {
      field: "actions",
      headerName: t.listingTable.actions,
      width: 170,
      align: "center",
      headerAlign: "center",
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const lid = params.row.listing_id;
        const busy = updatingIds.has(lid);
        const icalEnabled = params.row.ical_enabled !== false;
        return (
          <Box
            sx={{
              display: "flex",
              gap: 1,
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
            }}
          >
            <Tooltip title={t.listingTable.updateTooltip} arrow>
              <span>
                <IconButton
                  aria-label={t.listingTable.updateTooltip}
                  disabled={busy || !icalEnabled}
                  onClick={() => handleUpdateOne(lid)}
                  sx={actionIconButton}
                >
                  {busy ? (
                    <ListingCircularProgress size={20} />
                  ) : (
                    <RotateLeftIcon />
                  )}
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip
              title={
                icalEnabled
                  ? t.icalToggle.lockTooltip
                  : t.icalToggle.unlockTooltip
              }
              arrow
            >
              <IconButton
                aria-label={
                  icalEnabled
                    ? t.icalToggle.lockTooltip
                    : t.icalToggle.unlockTooltip
                }
                onClick={() => handleOpenConfirm(lid, icalEnabled)}
                sx={{
                  width: 40,
                  height: 40,
                  color: icalEnabled ? "#ef5350" : "#66bb6a",
                  backgroundColor: icalEnabled
                    ? "rgba(239, 83, 80, 0.15)"
                    : "rgba(102, 187, 106, 0.15)",
                  "&:hover": {
                    backgroundColor: icalEnabled
                      ? "rgba(239, 83, 80, 0.74)"
                      : "rgba(102, 187, 106, 0.3)",
                  },
                }}
              >
                {icalEnabled ? <LockIcon /> : <LockOpenIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title={t.editListing.editTooltip} arrow>
              <IconButton
                aria-label={t.editListing.editTooltip}
                onClick={() => handleOpenEdit(params.row)}
                sx={{
                  width: 40,
                  height: 40,
                  color: "#90caf9",
                  backgroundColor: "rgba(144, 202, 249, 0.15)",
                  "&:hover": { backgroundColor: "rgba(144, 202, 249, 0.3)" },
                }}
              >
                <EditIcon />
              </IconButton>
            </Tooltip>
          </Box>
        );
      },
    },
  ];

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <ListingCircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <AlertInline
        severity="error"
        message={error.error || error.message || t.listingTable.loadError}
        sx={{ m: 2 }}
      />
    );
  }

  return (
    <Box sx={{ width: "100%" }}>
      <DataGrid
        rows={listings}
        columns={columns}
        getRowId={(row) => row.listing_id}
        initialState={{
          pagination: { paginationModel: { pageSize: 10 } },
        }}
        pageSizeOptions={[10, 25, 50, 100]}
        disableRowSelectionOnClick
        density="standard"
        autoHeight
        sx={dataGridTable}
      />

      {/* Dialog: toggle ical */}
      <Dialog
        open={confirmDialog.open}
        onClose={handleCloseConfirm}
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>
          {confirmDialog.currentEnabled
            ? t.icalToggle.lockTitle
            : t.icalToggle.unlockTitle}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: "#BDBDBD" }}>
            {confirmDialog.currentEnabled
              ? t.icalToggle.lockMessage(confirmDialog.listingId)
              : t.icalToggle.unlockMessage(confirmDialog.listingId)}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleConfirmToggle}
            variant="contained"
            sx={{
              borderRadius: "1rem",
              backgroundColor: confirmDialog.currentEnabled
                ? "#ef5350"
                : "#66bb6a",
              "&:hover": {
                backgroundColor: confirmDialog.currentEnabled
                  ? "#c62828"
                  : "#388e3c",
              },
            }}
          >
            {confirmDialog.currentEnabled
              ? t.icalToggle.lockButton
              : t.icalToggle.unlockButton}
          </Button>
          <Button onClick={handleCloseConfirm} sx={cancelButtonSx}>
            {t.icalToggle.cancelButton}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: ver iCal URL */}
      <Dialog
        open={urlDialog.open}
        onClose={handleCloseUrlDialog}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.listingTable.icalUrlDialogTitle}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            value={urlDialog.url}
            slotProps={{ input: { readOnly: true } }}
            variant="outlined"
            size="small"
            sx={{
              mt: 1,
              "& .MuiOutlinedInput-root": {
                borderRadius: "1rem",
                color: "#E0E0E0",
                fontFamily: "monospace",
                fontSize: 13,
                "& fieldset": { borderColor: "#626262" },
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleCopyFromDialog}
            variant="contained"
            startIcon={urlDialogCopied ? <CheckIcon /> : <ContentCopyIcon />}
            sx={{
              ...greenButtonSx,
              backgroundColor: urlDialogCopied ? "#66bb6a" : "#16A34A",
              "&:hover": {
                backgroundColor: urlDialogCopied ? "#388e3c" : "#15803d",
              },
            }}
          >
            {urlDialogCopied
              ? t.listingTable.copied
              : t.listingTable.copyButton}
          </Button>
          <Button onClick={handleCloseUrlDialog} sx={cancelButtonSx}>
            {t.listingTable.closeButton}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: editar listing */}
      <Dialog
        open={editDialog.open}
        onClose={handleCloseEdit}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.editListing.dialogTitle}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            size="small"
            label={t.editListing.listingIdLabel}
            value={editDialog.listing?.listing_id || ""}
            slotProps={{ input: { readOnly: true } }}
            sx={{
              ...textFieldSx,
              "& .MuiOutlinedInput-root": {
                ...textFieldSx["& .MuiOutlinedInput-root"],
                color: "#999",
              },
            }}
          />
          <TextField
            fullWidth
            size="small"
            label={t.editListing.titleLabel}
            value={editForm.title}
            onChange={(e) =>
              setEditForm((p) => ({ ...p, title: e.target.value }))
            }
            sx={textFieldSx}
          />
          <Box sx={{ display: "flex", gap: 3 }}>
            <TextField
              fullWidth
              size="small"
              label={t.editListing.resortCodesLabel}
              value={editForm.resort_codes}
              onChange={(e) =>
                setEditForm((p) => ({ ...p, resort_codes: e.target.value }))
              }
              error={!validateResortCodes(editForm.resort_codes)}
              helperText={!validateResortCodes(editForm.resort_codes) ? t.editListing.resortCodesError : ""}
              sx={textFieldSx}
            />
            <TextField
              fullWidth
              size="small"
              label={t.editListing.bedroomsLabel}
              type="number"
              value={editForm.bedrooms}
              onChange={(e) =>
                setEditForm((p) => ({ ...p, bedrooms: e.target.value }))
              }
              slotProps={{ input: { inputProps: { min: 0 } } }}
              sx={textFieldSx}
            />
          </Box>
          <Box sx={{ display: "flex", gap: 3 }}>
            <TextField
              fullWidth
              size="small"
              label={t.editListing.addressLabel}
              placeholder={t.editListing.addressPlaceholder}
              value={editForm.address}
              onChange={(e) =>
                setEditForm((p) => ({ ...p, address: e.target.value }))
              }
              sx={textFieldSx}
            />
            <TextField
              fullWidth
              size="small"
              label={t.editListing.stateLabel}
              placeholder={t.editListing.statePlaceholder}
              value={editForm.state}
              onChange={(e) =>
                setEditForm((p) => ({ ...p, state: e.target.value }))
              }
              sx={textFieldSx}
            />
          </Box>
          <Button
            onClick={handleRequestDelete}
            variant="contained"
            fullWidth
            sx={{ ...deleteButtonSx, mt: 3, py: 1.2, fontSize: "0.95rem" }}
          >
            {t.editListing.deleteButton}
          </Button>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleRequestUpdate}
            variant="contained"
            disabled={!validateResortCodes(editForm.resort_codes)}
            sx={greenButtonSx}
          >
            {t.editListing.updateButton}
          </Button>
          <Button onClick={handleCloseEdit} sx={cancelButtonSx}>
            {t.editListing.cancelButton}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: confirmar actualización */}
      <Dialog
        open={confirmUpdate}
        onClose={handleCancelUpdate}
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.editListing.confirmUpdateTitle}</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: "#BDBDBD" }}>
            {t.editListing.confirmUpdateMessage(editDialog.listing?.listing_id)}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleConfirmUpdate}
            variant="contained"
            sx={greenButtonSx}
          >
            {t.editListing.confirmUpdateButton}
          </Button>
          <Button onClick={handleCancelUpdate} sx={cancelButtonSx}>
            {t.editListing.confirmUpdateCancel}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: confirmar eliminación */}
      <Dialog
        open={confirmDelete}
        onClose={handleCancelDelete}
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.editListing.confirmDeleteTitle}</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: "#BDBDBD" }}>
            {t.editListing.confirmDeleteMessage(editDialog.listing?.listing_id)}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button
            onClick={handleConfirmDelete}
            variant="contained"
            sx={deleteButtonSx}
          >
            {t.editListing.confirmDeleteButton}
          </Button>
          <Button onClick={handleCancelDelete} sx={cancelButtonSx}>
            {t.editListing.confirmDeleteCancel}
          </Button>
        </DialogActions>
      </Dialog>

      <IcalDatesModal
        open={calendarDialog.open}
        onClose={() => setCalendarDialog({ open: false, listingId: null })}
        listingId={calendarDialog.listingId}
        alertRef={alertRef}
      />
    </Box>
  );
};
