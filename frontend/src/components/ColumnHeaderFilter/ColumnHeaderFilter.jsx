import PropTypes from "prop-types";
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  Search as SearchIcon,
  FilterListOff as FilterListOffIcon,
} from "@mui/icons-material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs from "dayjs";
import "dayjs/locale/es";
import "dayjs/locale/en";
import { t } from "../../i18n";
import { useI18n } from "../../i18n/useI18n";
import { tableColors as C } from "../../styles/styles";
import { ListingCircularProgress } from "../ListingCircularProgress/ListingCircularProgress";

const inputSx = {
  "& .MuiOutlinedInput-root": {
    borderRadius: "0.75rem",
    backgroundColor: C.surface,
    color: C.text,
    height: "2rem",
    fontSize: 12,
    "& fieldset": { borderColor: C.border },
    "&:hover fieldset": { borderColor: C.primary },
    "&.Mui-focused fieldset": { borderColor: C.primary },
  },
  "& .MuiInputLabel-root": { color: C.textMuted, fontSize: 12, top: "-4px" },
  "& .MuiInputLabel-root.Mui-focused": { color: C.primary },
  "& .MuiInputLabel-shrink": { top: 0 },
};

const selectSx = {
  borderRadius: "0.75rem",
  backgroundColor: C.surface,
  color: C.text,
  height: "2rem",
  fontSize: 12,
  "& fieldset": { borderColor: C.border },
  "&:hover fieldset": { borderColor: C.primary },
  "&.Mui-focused fieldset": { borderColor: C.primary },
};

const menuProps = {
  PaperProps: {
    sx: {
      backgroundColor: C.headerBg,
      color: C.text,
      borderRadius: "0.75rem",
      border: `1px solid ${C.border}`,
      "& .MuiMenuItem-root:hover": { backgroundColor: C.primaryHover },
    },
  },
};

const calendarPopperSx = {
  "& .MuiPaper-root": {
    borderRadius: "1rem",
    backgroundColor: C.headerBg,
    border: `1px solid ${C.border}`,
    color: C.text,
  },
  "& .MuiPickersCalendarHeader-label": { color: C.primary, fontWeight: 500 },
  "& .MuiPickersArrowSwitcher-button, & .MuiPickersCalendarHeader-switchViewButton": {
    color: C.primary,
  },
  "& .MuiDayCalendar-weekDayLabel": { color: C.textMuted },
  "& .MuiPickersDay-root": {
    color: C.text,
    borderRadius: "0.5rem",
    "&.Mui-selected": { backgroundColor: C.primary, color: "#fff" },
    "&.MuiPickersDay-today": { border: `2px solid ${C.primary}` },
  },
};

const iconBtnSx = {
  width: 28,
  height: 28,
  color: C.textMuted,
  "&:hover": { backgroundColor: C.primaryHover, color: C.primary },
};

export const ColumnHeaderFilter = ({
  headerName,
  filterType = "text",
  filterKey,
  filterValue,
  onFilterChange,
  options = [],
  placeholder = "",
  onOpen,
  labelKey = "name",
  valueKey = "name",
  isOpen = false,
  label = "",
  onSearch,
  onClearFilters,
  loading = false,
  isDebouncing = false,
}) => {
  const { locale } = useI18n();
  const handleChange = (value) => onFilterChange?.(filterKey, value);

  const renderInput = () => {
    switch (filterType) {
      case "none":
        return <Box sx={{ height: "2rem" }} />;

      case "actions":
        return (
          <Box
            sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}
            onClick={(e) => e.stopPropagation()}
          >
            <Tooltip title={loading ? t.common.loading : t.common.search}>
              <span>
                <IconButton
                  onClick={() => onSearch?.()}
                  disabled={loading || isDebouncing}
                  sx={iconBtnSx}
                >
                  {loading ? (
                    <ListingCircularProgress size={16} />
                  ) : (
                    <SearchIcon sx={{ fontSize: 16 }} />
                  )}
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={t.common.clearFilters}>
              <IconButton onClick={onClearFilters} sx={{ ...iconBtnSx, color: C.primary }}>
                <FilterListOffIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </Box>
        );

      case "select":
        return (
          <FormControl fullWidth size="small">
            <InputLabel
              id={`${filterKey}-label`}
              sx={{
                color: C.textMuted, fontSize: 12, top: "-4px",
                "&.Mui-focused": { color: C.primary },
                "&.MuiInputLabel-shrink": { top: 0 },
              }}
            >
              {label || headerName}
            </InputLabel>
            <Select
              labelId={`${filterKey}-label`}
              value={filterValue || ""}
              onChange={(e) => handleChange(e.target.value)}
              label={label || headerName}
              onOpen={onOpen}
              MenuProps={menuProps}
              sx={selectSx}
            >
              <MenuItem value=""><em>{t.common.all}</em></MenuItem>
              {options.map((opt, i) => (
                <MenuItem key={opt[valueKey] ?? i} value={opt[valueKey] ?? opt}>
                  {opt[labelKey] ?? opt}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );

      case "date":
        return (
          <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale={locale}>
            <DatePicker
              label={label || headerName}
              value={filterValue ? dayjs(filterValue) : null}
              onChange={(v) => handleChange(v ? v.format("YYYY-MM-DD") : "")}
              slotProps={{
                textField: { size: "small", fullWidth: true, sx: inputSx },
                popper: { sx: calendarPopperSx },
                toolbar: { hidden: true },
              }}
            />
          </LocalizationProvider>
        );

      case "text":
      default:
        return (
          <TextField
            fullWidth
            size="small"
            label={label || headerName}
            placeholder={placeholder || headerName}
            value={filterValue || ""}
            onChange={(e) => handleChange(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            sx={inputSx}
          />
        );
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: isOpen ? "flex-end" : "center",
        gap: 0.5,
        width: "100%",
        height: "100%",
        py: isOpen ? 0.5 : 0,
      }}
    >
      {isOpen && (
        <Box sx={{ width: "100%" }} onClick={(e) => e.stopPropagation()}>
          {renderInput()}
        </Box>
      )}
      <Typography
        sx={{
          fontWeight: 700,
          textTransform: "uppercase",
          fontSize: 12,
          color: C.textMuted,
          letterSpacing: "0.05em",
          fontFamily: "'Inter', sans-serif",
        }}
      >
        {headerName}
      </Typography>
    </Box>
  );
};

ColumnHeaderFilter.propTypes = {
  headerName: PropTypes.string.isRequired,
  filterType: PropTypes.oneOf(["text", "select", "date", "actions", "none"]),
  filterKey: PropTypes.string,
  filterValue: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  onFilterChange: PropTypes.func,
  options: PropTypes.array,
  placeholder: PropTypes.string,
  onOpen: PropTypes.func,
  labelKey: PropTypes.string,
  valueKey: PropTypes.string,
  isOpen: PropTypes.bool,
  label: PropTypes.string,
  onSearch: PropTypes.func,
  onClearFilters: PropTypes.func,
  loading: PropTypes.bool,
  isDebouncing: PropTypes.bool,
};
