import { useState, useRef, useEffect, useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import useMediaQuery from "@mui/material/useMediaQuery";
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
  dialogPaperSx,
  greenButtonSx,
  cancelButtonSx,
  dialogTextFieldSx,
} from "../../styles/styles";
import {
  useUpdateListingDataMutation,
  useDeleteListingMutation,
} from "../../store/api/api";
import { t, dateLocale } from "../../i18n";
import { ColumnHeaderFilter } from "../ColumnHeaderFilter/ColumnHeaderFilter";
import { UniversalMobilDataTable } from "../UniversalMobilDataTable/UniversalMobilDataTable";
import { MobileFilterPanel } from "../MobileFilterPanel/MobileFilterPanel";
import { validateResortCodes, extractErrorMessage } from "../../utils/listingUtils";

const deleteButtonSx = {
  borderRadius: "1rem",
  textTransform: "none",
  backgroundColor: "#ef5350",
  "&:hover": { backgroundColor: "#c62828" },
};

const textFieldSx = { mt: 1.5, ...dialogTextFieldSx };

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

const EMPTY_FILTERS = {
  listing_id: "",
  title: "",
  resort_codes: "",
  bedrooms: "",
  state: "",
};

export const ListingTable = ({
  listings,
  loading,
  error,
  updatingIds,
  handleUpdateOne,
  handleToggleIcal,
  alertRef,
  filtersOpen = false,
}) => {
  const isMobile = useMediaQuery("(max-width:768px)");

  const [filters, setFilters] = useState(EMPTY_FILTERS);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleClearFilters = () => setFilters(EMPTY_FILTERS);

  const filteredListings = useMemo(() => {
    if (!Array.isArray(listings)) return [];
    return listings.filter((row) => {
      if (filters.listing_id && !String(row.listing_id).toLowerCase().includes(filters.listing_id.toLowerCase())) return false;
      if (filters.title && !(row.title || "").toLowerCase().includes(filters.title.toLowerCase())) return false;
      if (filters.resort_codes && !(row.resort_codes || []).join(" ").toLowerCase().includes(filters.resort_codes.toLowerCase())) return false;
      if (filters.bedrooms && String(row.bedrooms) !== filters.bedrooms) return false;
      if (filters.state && !(row.state || "").toLowerCase().includes(filters.state.toLowerCase())) return false;
      return true;
    });
  }, [listings, filters]);
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

  const bedroomOptions = [
    { value: "0", label: t.listingTable.studio },
    { value: "1", label: "1 hab" },
    { value: "2", label: "2 hab" },
    { value: "3", label: "3 hab" },
  ];

  const mkHeader = (headerName, filterType, filterKey, extra = {}) => ({
    renderHeader: () => (
      <ColumnHeaderFilter
        headerName={headerName}
        filterType={filterType}
        filterKey={filterKey}
        filterValue={filters[filterKey]}
        onFilterChange={handleFilterChange}
        isOpen={filtersOpen}
        onClearFilters={handleClearFilters}
        {...extra}
      />
    ),
  });

  const columns = [
    {
      field: "listing_id",
      headerName: t.listingTable.listingId,
      flex: 1,
      align: "center",
      headerAlign: "center",
      ...mkHeader(t.listingTable.listingId, "text", "listing_id"),
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
      ...mkHeader(t.listingTable.resortName, "text", "title"),
    },
    {
      field: "resort_codes",
      headerName: t.listingTable.resortCodes,
      width: 180,
      align: "center",
      headerAlign: "center",
      renderCell: (params) =>
        (params.value || []).map((code) => (
          <Chip key={code} label={code} size="small" variant="outlined" sx={resortCodes} />
        )),
      ...mkHeader(t.listingTable.resortCodes, "text", "resort_codes"),
    },
    {
      field: "bedrooms",
      headerName: t.listingTable.bedrooms,
      width: 150,
      align: "center",
      headerAlign: "center",
      renderCell: (params) => bedroomLabel(params.value),
      ...mkHeader(t.listingTable.bedrooms, "select", "bedrooms", { options: bedroomOptions, labelKey: "label", valueKey: "value" }),
    },
    {
      field: "state",
      headerName: t.listingTable.state,
      width: 150,
      align: "center",
      headerAlign: "center",
      renderCell: (params) =>
        params.value || <em style={{ color: "#999" }}>—</em>,
      ...mkHeader(t.listingTable.state, "text", "state"),
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
                <Tooltip title={typeof lastError === "string" ? lastError : t.listingTable.lastErrorTooltip} arrow>
                  <WarningAmberIcon sx={{ color: "#ffa726", fontSize: 18 }} />
                </Tooltip>
              )}
            </Box>
            {formatDate(params.value)}
          </Box>
        );
      },
      renderHeader: () => (
        <ColumnHeaderFilter
          headerName={t.listingTable.lastUpdated}
          filterType="none"
          isOpen={filtersOpen}
        />
      ),
    },
    {
      field: "ical_url",
      headerName: t.listingTable.icalUrlHeader,
      width: 130,
      align: "center",
      headerAlign: "center",
      sortable: false,
      filterable: false,
      renderHeader: () => (
        <ColumnHeaderFilter headerName={t.listingTable.icalUrlHeader} filterType="none" isOpen={filtersOpen} />
      ),
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
      renderHeader: () => (
        <ColumnHeaderFilter headerName={t.icalDates.columnHeader} filterType="none" isOpen={filtersOpen} />
      ),
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
      renderHeader: () => (
        <ColumnHeaderFilter
          headerName={t.listingTable.actions}
          filterType="actions"
          isOpen={filtersOpen}
          onClearFilters={handleClearFilters}
        />
      ),
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

  // ─── Mobile config ──────────────────────────────────────────────────────────

  const mobileColumns = [
    { field: "listing_id", headerName: t.listingTable.listingId },
    {
      field: "resort_codes",
      headerName: t.listingTable.resortCodes,
      renderCell: ({ row }) =>
        (row.resort_codes || []).map((code) => (
          <Chip key={code} label={code} size="small" variant="outlined" sx={{ ...resortCodes, mr: 0.5 }} />
        )),
    },
    {
      field: "bedrooms",
      headerName: t.listingTable.bedrooms,
      renderCell: ({ row }) => (
        <Typography variant="body2" sx={{ color: "#E0E0E0" }}>
          {bedroomLabel(row.bedrooms)}
        </Typography>
      ),
    },
    { field: "state", headerName: t.listingTable.state },
    {
      field: "last_updated",
      headerName: t.listingTable.lastUpdated,
      renderCell: ({ row }) => (
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {row.last_error && (
            <Tooltip title={typeof row.last_error === "string" ? row.last_error : t.listingTable.lastErrorTooltip} arrow>
              <WarningAmberIcon sx={{ color: "#ffa726", fontSize: 16 }} />
            </Tooltip>
          )}
          <Typography variant="body2" sx={{ color: "#E0E0E0" }}>
            {formatDate(row.last_updated)}
          </Typography>
        </Box>
      ),
    },
    {
      field: "ical_url",
      headerName: t.listingTable.icalUrlHeader,
      renderCell: ({ row }) => {
        const url = row.ical_url;
        if (!url) return <Box sx={{ color: "#777", fontSize: 12 }}>{t.listingTable.noUrlConfigured}</Box>;
        const isCopied = copiedId === row.listing_id;
        return (
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <Tooltip title={isCopied ? t.listingTable.copied : t.listingTable.copyTooltip} arrow>
              <IconButton size="small" onClick={() => handleCopyUrl(url, row.listing_id)}
                sx={{ color: isCopied ? "#66bb6a" : "#90caf9" }}>
                {isCopied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
            <Tooltip title={t.listingTable.viewUrlTooltip} arrow>
              <IconButton size="small" onClick={() => handleOpenUrlDialog(url)}
                sx={{ color: "#ce93d8" }}>
                <VisibilityIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        );
      },
    },
  ];

  const mobileRenderActions = (row) => {
    const lid = row.listing_id;
    const busy = updatingIds.has(lid);
    const icalEnabled = row.ical_enabled !== false;
    return (
      <>
        <Tooltip title={t.listingTable.updateTooltip} arrow>
          <span>
            <IconButton disabled={busy || !icalEnabled} onClick={() => handleUpdateOne(lid)} sx={actionIconButton} size="small">
              {busy ? <ListingCircularProgress size={18} /> : <RotateLeftIcon fontSize="small" />}
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={icalEnabled ? t.icalToggle.lockTooltip : t.icalToggle.unlockTooltip} arrow>
          <IconButton onClick={() => handleOpenConfirm(lid, icalEnabled)} size="small"
            sx={{ color: icalEnabled ? "#ef5350" : "#66bb6a", backgroundColor: icalEnabled ? "rgba(239,83,80,0.15)" : "rgba(102,187,106,0.15)" }}>
            {icalEnabled ? <LockIcon fontSize="small" /> : <LockOpenIcon fontSize="small" />}
          </IconButton>
        </Tooltip>
        <Tooltip title={t.icalDates.openTooltip} arrow>
          <IconButton onClick={() => setCalendarDialog({ open: true, listingId: lid })} size="small"
            sx={{ color: "#ce93d8" }}>
            <CalendarMonthIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title={t.editListing.editTooltip} arrow>
          <IconButton onClick={() => handleOpenEdit(row)} size="small"
            sx={{ color: "#90caf9", backgroundColor: "rgba(144,202,249,0.15)" }}>
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </>
    );
  };

  const mobileFilters = [
    { key: "title", label: t.listingTable.resortName, type: "text", value: filters.title },
    { key: "resort_codes", label: t.listingTable.resortCodes, type: "text", value: filters.resort_codes },
    {
      key: "bedrooms", label: t.listingTable.bedrooms, type: "select", value: filters.bedrooms,
      options: [
        { value: "0", label: t.listingTable.studio },
        { value: "1", label: "1 hab" },
        { value: "2", label: "2 hab" },
        { value: "3", label: "3 hab" },
      ],
    },
    { key: "state", label: t.listingTable.state, type: "text", value: filters.state },
  ];

  // ─── Loading / Error ─────────────────────────────────────────────────────────

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
      {isMobile ? (
        <UniversalMobilDataTable
          rows={filteredListings}
          columns={mobileColumns}
          hideHeader
          primaryField={(row) => row.title || row.listing_id}
          getRowId={(row) => row.listing_id}
          renderActions={mobileRenderActions}
          actionsLabel={t.listingTable.actions}
          loading={loading}
          error={error ? (error.error || error.message || t.listingTable.loadError) : null}
          emptyMessage={t.listingTable.loadError}
          showTitle={false}
          labelWidth={140}
          rowsPerPageOptions={[8, 16, 100]}
          subHeader={
            <MobileFilterPanel
              isOpen={filtersOpen}
              filters={mobileFilters}
              onFilterChange={handleFilterChange}
              onSearch={() => {}}
              onClear={handleClearFilters}
            />
          }
        />
      ) : (
        <DataGrid
          rows={filteredListings}
          columns={columns}
          getRowId={(row) => row.listing_id}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          disableRowSelectionOnClick
          density="standard"
          autoHeight
          columnHeaderHeight={filtersOpen ? 82 : 56}
          sx={dataGridTable}
        />
      )}

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
        onUpdateStarted={handleUpdateOne}
      />
    </Box>
  );
};
