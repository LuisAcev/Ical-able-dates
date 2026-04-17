import { useState, useEffect, useMemo } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import { DateCalendar } from "@mui/x-date-pickers/DateCalendar";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { PickersDay } from "@mui/x-date-pickers/PickersDay";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import dayjs from "dayjs";

const greenPickerTheme = createTheme({
  palette: { primary: { main: "#16A34A" } },
  shape: { borderRadius: 24 },
  components: {
    MuiOutlinedInput: {
      styleOverrides: {
        root: { color: "#000000" },
      },
    },
    MuiInputLabel: {
      styleOverrides: { root: { color: "#555" } },
    },
    MuiSvgIcon: {
      styleOverrides: { root: { color: "#555" } },
    },
  },
});
import { ListingCircularProgress } from "../ListingCircularProgress/ListingCircularProgress";
import {
  useGetListingDatesQuery,
  useSaveManualDatesMutation,
} from "../../store/api/api";
import { t } from "../../i18n";

const dialogPaperSx = {
  backgroundColor: "#424242",
  color: "#E0E0E0",
  borderRadius: "1.5rem",
  maxHeight: "90vh",
};

const greenButtonSx = {
  borderRadius: "1rem",
  textTransform: "none",
  backgroundColor: "#16A34A",
  "&:hover": { backgroundColor: "#15803d" },
};

const cancelButtonSx = { color: "#BDBDBD", borderRadius: "1rem" };

function CustomDay({ day, blockedSet, availableSet, manualSet, overrideSet, pendingDate, pendingOverrideDate, ...other }) {
  const dateStr = day.format("YYYY-MM-DD");
  const isBlocked = blockedSet.has(dateStr);
  const isAvailable = availableSet.has(dateStr);
  const isManual = manualSet.has(dateStr);
  const isOverride = overrideSet.has(dateStr);
  const isPending = pendingDate && day.isSame(pendingDate, "day");
  const isPendingOverride = pendingOverrideDate && day.isSame(pendingOverrideDate, "day");

  const TEXT_COLOR = "#E0E0E0";
  let bgColor = "transparent";
  let color = TEXT_COLOR;

  if (isPending) {
    bgColor = "rgba(255, 167, 38, 0.6)";
    color = TEXT_COLOR;
  } else if (isPendingOverride) {
    bgColor = "rgba(38, 198, 218, 0.7)";
    color = TEXT_COLOR;
  } else if (isOverride) {
    bgColor = "rgba(38, 198, 218, 0.5)";
    color = TEXT_COLOR;
  } else if (isManual) {
    bgColor = "rgba(66, 165, 245, 0.5)";
    color = TEXT_COLOR;
  } else if (isAvailable) {
    bgColor = "rgba(102, 187, 106, 0.4)";
    color = TEXT_COLOR;
  } else if (isBlocked) {
    bgColor = "rgba(239, 83, 80, 0.3)";
    color = TEXT_COLOR;
  }

  return (
    <PickersDay
      {...other}
      day={day}
      sx={{
        backgroundColor: bgColor,
        color,
        "&:hover": { backgroundColor: bgColor, filter: "brightness(1.2)" },
        "&.Mui-selected": { backgroundColor: bgColor, color },
      }}
    />
  );
}

export const IcalDatesModal = ({ open, onClose, listingId, alertRef, onUpdateStarted }) => {
  const { data, isLoading, isError } = useGetListingDatesQuery(listingId, {
    skip: !open || !listingId,
  });
  const [saveManualDates] = useSaveManualDatesMutation();

  const [localManual, setLocalManual] = useState([]);
  const [localOverride, setLocalOverride] = useState([]);
  const [localStartDate, setLocalStartDate] = useState(null);
  const [pendingDate, setPendingDate] = useState(null);
  const [pendingOverrideDate, setPendingOverrideDate] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null);

  useEffect(() => {
    if (data) {
      setLocalManual(data.manual_dates ?? []);
      setLocalOverride(data.available_override_dates ?? []);
      setLocalStartDate(data.start_date ? dayjs(data.start_date) : null);
    }
  }, [data]);

  useEffect(() => {
    if (!open) {
      setPendingDate(null);
      setPendingOverrideDate(null);
    }
  }, [open]);

  const blockedSet = useMemo(() => new Set(data?.blocked_dates || []), [data?.blocked_dates]);
  const availableSet = useMemo(() => new Set(data?.available_dates || []), [data?.available_dates]);

  const manualSet = useMemo(() => {
    const s = new Set();
    for (const [start, end] of localManual) {
      let cur = dayjs(start);
      const endD = dayjs(end);
      while (cur.isBefore(endD)) {
        s.add(cur.format("YYYY-MM-DD"));
        cur = cur.add(1, "day");
      }
    }
    return s;
  }, [localManual]);

  const overrideSet = useMemo(() => {
    const s = new Set();
    for (const [start, end] of localOverride) {
      let cur = dayjs(start);
      const endD = dayjs(end);
      while (cur.isBefore(endD)) {
        s.add(cur.format("YYYY-MM-DD"));
        cur = cur.add(1, "day");
      }
    }
    return s;
  }, [localOverride]);

  const handleDayClick = (day) => {
    const dateStr = day.format("YYYY-MM-DD");

    // Click en fecha override existente → eliminar ese rango override
    for (let i = 0; i < localOverride.length; i++) {
      const [start, end] = localOverride[i];
      let cur = dayjs(start);
      const endD = dayjs(end);
      while (cur.isBefore(endD)) {
        if (cur.format("YYYY-MM-DD") === dateStr) {
          setLocalOverride((prev) => prev.filter((_, idx) => idx !== i));
          setPendingOverrideDate(null);
          return;
        }
        cur = cur.add(1, "day");
      }
    }

    // Click en fecha manual existente → eliminar ese rango manual
    for (let i = 0; i < localManual.length; i++) {
      const [start, end] = localManual[i];
      let cur = dayjs(start);
      const endD = dayjs(end);
      while (cur.isBefore(endD)) {
        if (cur.format("YYYY-MM-DD") === dateStr) {
          setLocalManual((prev) => prev.filter((_, idx) => idx !== i));
          setPendingDate(null);
          return;
        }
        cur = cur.add(1, "day");
      }
    }

    // Click en fecha bloqueada (roja) → crear rango de disponibilidad forzada
    if (blockedSet.has(dateStr)) {
      if (!pendingOverrideDate) {
        setPendingDate(null);
        setPendingOverrideDate(day);
      } else {
        const start = pendingOverrideDate.isBefore(day) ? pendingOverrideDate : day;
        const end = pendingOverrideDate.isBefore(day) ? day : pendingOverrideDate;
        const endExclusive = end.add(1, "day");
        setLocalOverride((prev) => [
          ...prev,
          [start.format("YYYY-MM-DD"), endExclusive.format("YYYY-MM-DD")],
        ]);
        setPendingOverrideDate(null);
      }
      return;
    }

    // Click en fecha disponible (verde) → crear rango de bloqueo manual
    setPendingOverrideDate(null);
    if (!pendingDate) {
      setPendingDate(day);
    } else {
      const start = pendingDate.isBefore(day) ? pendingDate : day;
      const end = pendingDate.isBefore(day) ? day : pendingDate;
      const endExclusive = end.add(1, "day");
      setLocalManual((prev) => [
        ...prev,
        [start.format("YYYY-MM-DD"), endExclusive.format("YYYY-MM-DD")],
      ]);
      setPendingDate(null);
    }
  };

  const handleRemoveRange = (idx) => {
    setLocalManual((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleConfirmAction = async () => {
    setConfirmAction(null);
    try {
      await saveManualDates({
        listingId,
        manual_dates: localManual,
        available_override_dates: localOverride,
        start_date: localStartDate ? localStartDate.format("YYYY-MM-DD") : null,
      }).unwrap();
      await onUpdateStarted(listingId);
      alertRef?.current?.showSuccess(t.icalDates.saveSuccess);
      onClose();
    } catch {
      alertRef?.current?.showError(t.icalDates.saveError);
    }
  };

  const minDate = data?.range_start ? dayjs(data.range_start) : undefined;
  const maxDate = data?.range_end ? dayjs(data.range_end) : undefined;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: dialogPaperSx }}
    >
      <DialogTitle>{t.icalDates.dialogTitle(listingId || "")}</DialogTitle>
      <DialogContent>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <ListingCircularProgress />
          </Box>
        )}

        {isError && (
          <Typography sx={{ color: "#ef9a9a", textAlign: "center", py: 2 }}>
            {t.icalDates.noIcsFile}
          </Typography>
        )}

        {data && !isLoading && (
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <>
              <Box sx={{ display: "flex", justifyContent: "center" }}>
                <DateCalendar
                  minDate={minDate}
                  maxDate={maxDate}
                  onChange={handleDayClick}
                  slots={{
                    day: (props) => (
                      <CustomDay
                        {...props}
                        blockedSet={blockedSet}
                        availableSet={availableSet}
                        manualSet={manualSet}
                        overrideSet={overrideSet}
                        pendingDate={pendingDate}
                        pendingOverrideDate={pendingOverrideDate}
                      />
                    ),
                  }}
                  sx={{
                    "& .MuiPickersCalendarHeader-root": { color: "#E0E0E0" },
                    "& .MuiDayCalendar-weekDayLabel": { color: "#E0E0E0" },
                    "& .MuiPickersArrowSwitcher-button": { color: "#E0E0E0" },
                    "& .MuiPickersCalendarHeader-label": { color: "#E0E0E0" },
                  }}
                />
              </Box>

            {/* Leyenda */}
            <Box sx={{ display: "flex", gap: 2, justifyContent: "center", mt: 1, flexWrap: "wrap" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Box sx={{ width: 14, height: 14, borderRadius: "50%", backgroundColor: "rgba(239, 83, 80, 0.5)" }} />
                <Typography variant="caption" sx={{ color: "#BDBDBD" }}>{t.icalDates.legendBlocked}</Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Box sx={{ width: 14, height: 14, borderRadius: "50%", backgroundColor: "rgba(102, 187, 106, 0.6)" }} />
                <Typography variant="caption" sx={{ color: "#BDBDBD" }}>{t.icalDates.legendAvailable}</Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Box sx={{ width: 14, height: 14, borderRadius: "50%", backgroundColor: "rgba(66, 165, 245, 0.6)" }} />
                <Typography variant="caption" sx={{ color: "#BDBDBD" }}>{t.icalDates.legendManual}</Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                <Box sx={{ width: 14, height: 14, borderRadius: "50%", backgroundColor: "rgba(38, 198, 218, 0.6)" }} />
                <Typography variant="caption" sx={{ color: "#BDBDBD" }}>{t.icalDates.legendOverride}</Typography>
              </Box>
              {(pendingDate || pendingOverrideDate) && (
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <Box sx={{ width: 14, height: 14, borderRadius: "50%", backgroundColor: "rgba(255, 167, 38, 0.7)" }} />
                  <Typography variant="caption" sx={{ color: "#ffa726" }}>{t.icalDates.legendPending}</Typography>
                </Box>
              )}
            </Box>

            {/* Fecha de inicio del iCal */}
            <Box sx={{ mt: 2, mb: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
              <Typography variant="subtitle2" sx={{ color: "#E0E0E0", mb: 1, marginLeft:'-5rem' }}>
                {t.icalDates.startDateTitle}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                  <ThemeProvider theme={greenPickerTheme}>
                    <DatePicker
                      label={t.icalDates.startDateLabel}
                      value={localStartDate}
                      onChange={(val) => setLocalStartDate(val)}
                      minDate={minDate}
                      maxDate={maxDate}
                      slotProps={{
                        textField: {
                          size: "small",
                          sx: {
                            width: 180,
                            backgroundColor: "#E0E0E0",
                            borderRadius: "24px",
                            "& .MuiInputLabel-root.Mui-focused": {
                              color: "#16A34A",
                              fontWeight: 600,
                            },
                          },
                        },
                        desktopPaper: {
                          sx: {
                            borderRadius: "1rem",
                            "& .MuiPickersDay-root:not(.Mui-selected)": { color: "#000" },
                            "& .MuiPickersCalendarHeader-label": { color: "#000" },
                            "& .MuiPickersArrowSwitcher-button": { color: "#000" },
                            "& .MuiDayCalendar-weekDayLabel": { color: "#555" },
                          },
                        },
                      }}
                    />
                  </ThemeProvider>
                <Button
                  size="small"
                  onClick={() => setLocalStartDate(null)}
                  sx={{
                    color: "#ef9a9a",
                    borderRadius: "1rem",
                    textTransform: "none",
                    whiteSpace: "nowrap",
                    visibility: localStartDate ? "visible" : "hidden",
                  }}
                >
                  {t.icalDates.startDateClear}
                </Button>
              </Box>
              <Typography variant="caption" sx={{ color: "#777", mt: 0.5 }}>
                {t.icalDates.startDateHelper}
              </Typography>
            </Box>

            {/* Rangos manuales */}
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1, color: "#E0E0E0" }}>
              {t.icalDates.manualRangesTitle}
            </Typography>
            {localManual.length === 0 ? (
              <Typography variant="body2" sx={{ color: "#777" }}>
                {t.icalDates.noManualRanges}
              </Typography>
            ) : (
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                {localManual.map(([start, end], idx) => (
                  <Chip
                    key={`${start}-${end}`}
                    label={`${start} → ${dayjs(end).subtract(1, "day").format("YYYY-MM-DD")}`}
                    onDelete={() => handleRemoveRange(idx)}
                    deleteIcon={<DeleteIcon sx={{ color: "#ef9a9a !important" }} />}
                    sx={{
                      backgroundColor: "rgba(66, 165, 245, 0.2)",
                      color: "#90caf9",
                      borderColor: "#42a5f5",
                      border: "1px solid",
                    }}
                  />
                ))}
              </Box>
            )}
            {/* Rangos de disponibilidad forzada */}
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1, color: "#E0E0E0" }}>
              {t.icalDates.overrideRangesTitle}
            </Typography>
            {localOverride.length === 0 ? (
              <Typography variant="body2" sx={{ color: "#777" }}>
                {t.icalDates.noOverrideRanges}
              </Typography>
            ) : (
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                {localOverride.map(([start, end], idx) => (
                  <Chip
                    key={`ov-${start}-${end}`}
                    label={`${start} → ${dayjs(end).subtract(1, "day").format("YYYY-MM-DD")}`}
                    onDelete={() => setLocalOverride((prev) => prev.filter((_, i) => i !== idx))}
                    deleteIcon={<DeleteIcon sx={{ color: "#ef9a9a !important" }} />}
                    sx={{
                      backgroundColor: "rgba(38, 198, 218, 0.15)",
                      color: "#80deea",
                      borderColor: "#26c6da",
                      border: "1px solid",
                    }}
                  />
                ))}
              </Box>
            )}
            </>
          </LocalizationProvider>
        )}
      </DialogContent>
      <DialogActions sx={{ justifyContent: "center", pb: 2 }}>
        <Button onClick={() => setConfirmAction("save")} variant="contained" sx={greenButtonSx}>
          {t.icalDates.saveButton}
        </Button>
        <Button onClick={onClose} sx={cancelButtonSx}>
          {t.icalDates.cancelButton}
        </Button>
      </DialogActions>

      {/* Modal confirmación */}
      <Dialog
        open={confirmAction !== null}
        onClose={() => setConfirmAction(null)}
        PaperProps={{ sx: dialogPaperSx }}
      >
        <DialogTitle>{t.icalDates.confirmSaveTitle}</DialogTitle>
        <DialogContent>
          <Typography sx={{ color: "#BDBDBD" }}>
            {t.icalDates.confirmSaveMessage}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ justifyContent: "center" }}>
          <Button onClick={handleConfirmAction} variant="contained" sx={greenButtonSx}>
            {t.icalDates.confirmSaveButton}
          </Button>
          <Button onClick={() => setConfirmAction(null)} sx={cancelButtonSx}>
            {t.icalDates.confirmCancel}
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
};
