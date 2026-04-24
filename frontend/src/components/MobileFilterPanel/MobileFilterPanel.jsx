import PropTypes from "prop-types";
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  Collapse,
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
    fontSize: 13,
    "& fieldset": { borderColor: C.border },
    "&:hover fieldset": { borderColor: C.primary },
    "&.Mui-focused fieldset": { borderColor: C.primary },
  },
  "& .MuiInputLabel-root": { color: C.textMuted, fontSize: 13 },
  "& .MuiInputLabel-root.Mui-focused": { color: C.primary },
};

const selectSx = {
  borderRadius: "0.75rem",
  backgroundColor: C.surface,
  color: C.text,
  fontSize: 13,
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

const calendarStyles = {
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
  width: 36,
  height: 36,
  color: C.textMuted,
  "&:hover": { backgroundColor: C.primaryHover, color: C.primary },
};

export const MobileFilterPanel = ({
  isOpen,
  filters,
  onFilterChange,
  onSearch,
  onClear,
  loading = false,
  isDebouncing = false,
}) => {
  const { locale } = useI18n();

  const datePickerSlotProps = {
    textField: { size: "small", fullWidth: true, sx: inputSx },
    popper: { sx: calendarStyles },
    dialog: { sx: calendarStyles },
    toolbar: { hidden: true },
  };

  const renderFilter = ({ key, label, type, value, placeholder, options = [] }) => {
    switch (type) {
      case "text":
        return (
          <TextField
            fullWidth
            size="small"
            label={label}
            placeholder={placeholder || label}
            value={value || ""}
            onChange={(e) => onFilterChange(key, e.target.value)}
            sx={inputSx}
          />
        );

      case "select":
        return (
          <FormControl fullWidth size="small">
            <InputLabel sx={{ color: C.textMuted, fontSize: 13, "&.Mui-focused": { color: C.primary } }}>
              {label}
            </InputLabel>
            <Select
              value={value || ""}
              onChange={(e) => onFilterChange(key, e.target.value)}
              label={label}
              MenuProps={menuProps}
              sx={selectSx}
            >
              <MenuItem value=""><em>{t.common.all}</em></MenuItem>
              {options.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );

      case "date":
        return (
          <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale={locale}>
            <DatePicker
              label={label}
              value={value ? dayjs(value) : null}
              onChange={(v) => onFilterChange(key, v ? v.format("YYYY-MM-DD") : "")}
              slotProps={datePickerSlotProps}
            />
          </LocalizationProvider>
        );

      default:
        return null;
    }
  };

  return (
    <Collapse in={isOpen} timeout={300} unmountOnExit>
      <Box sx={{ pb: 2 }}>
        <Box
          sx={{
            px: 2,
            py: 1.5,
            backgroundColor: C.headerBg,
            borderRadius: "1rem",
            border: `1px solid ${C.border}`,
          }}
        >
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
            {filters.map((filterConfig) => (
              <Box key={filterConfig.key} sx={{ width: "100%", minWidth: 0 }}>
                {renderFilter(filterConfig)}
              </Box>
            ))}
          </Box>

          <Box sx={{ display: "flex", justifyContent: "center", gap: 1, mt: 2 }}>
            <Tooltip title={t.common.search}>
              <span>
                <IconButton onClick={onSearch} disabled={loading || isDebouncing} sx={iconBtnSx}>
                  {loading ? <ListingCircularProgress size={18} /> : <SearchIcon fontSize="small" />}
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={t.common.clearFilters}>
              <IconButton onClick={onClear} sx={{ ...iconBtnSx, color: C.primary }}>
                <FilterListOffIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
      </Box>
    </Collapse>
  );
};

MobileFilterPanel.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  filters: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      type: PropTypes.oneOf(["text", "select", "date"]).isRequired,
      value: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
      placeholder: PropTypes.string,
      options: PropTypes.arrayOf(
        PropTypes.shape({
          value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
          label: PropTypes.string.isRequired,
        })
      ),
    })
  ).isRequired,
  onFilterChange: PropTypes.func.isRequired,
  onSearch: PropTypes.func.isRequired,
  onClear: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  isDebouncing: PropTypes.bool,
};
