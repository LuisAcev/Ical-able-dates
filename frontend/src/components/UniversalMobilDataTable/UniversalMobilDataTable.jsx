import { useState, useMemo, useCallback, useEffect } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  TablePagination,
  Typography,
  IconButton,
  Box,
  Paper,
  Collapse,
  Stack,
} from "@mui/material";
import {
  KeyboardArrowDown as KeyboardArrowDownIcon,
  KeyboardArrowUp as KeyboardArrowUpIcon,
} from "@mui/icons-material";
import PropTypes from "prop-types";
import { AlertInline } from "../AlertInline/AlertInline";
import { ListingCircularProgress } from "../ListingCircularProgress/ListingCircularProgress";
import { t } from "../../i18n";
import { tableColors as C } from "../../styles/styles";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const safeRender = (fn, params, fallback = null) => {
  if (typeof fn !== "function") return fallback;
  try {
    return fn(params) ?? fallback;
  } catch {
    return fallback;
  }
};

const safeGetValue = (obj, field, defaultValue = null) => {
  if (!obj) return defaultValue;
  try {
    if (typeof field === "function") return field(obj) ?? defaultValue;
    return obj[field] ?? defaultValue;
  } catch {
    return defaultValue;
  }
};

const isValidColumn = (col) =>
  col && typeof col === "object" && typeof col.field === "string" && col.field.length > 0;

// ─── AccordionRow ─────────────────────────────────────────────────────────────

const AccordionRow = ({
  row,
  columns,
  primaryField,
  primaryIcon,
  secondaryField,
  showTitle,
  titleField,
  renderActions,
  actionsLabel,
  onRowClick,
  defaultExpanded,
  labelWidth,
  renderExpandedFooter,
}) => {
  const [open, setOpen] = useState(defaultExpanded);

  const handleToggle = useCallback((e) => {
    e.stopPropagation();
    setOpen((prev) => !prev);
  }, []);

  const handleRowClick = useCallback(() => {
    if (typeof onRowClick === "function") onRowClick(row);
  }, [onRowClick, row]);

  const primaryValue = useMemo(() => safeGetValue(row, primaryField, "N/A"), [row, primaryField]);
  const secondaryValue = useMemo(() => secondaryField ? safeGetValue(row, secondaryField) : null, [row, secondaryField]);
  const titleValue = useMemo(() => {
    if (!showTitle) return null;
    if (titleField) return safeGetValue(row, titleField);
    return typeof primaryValue === "string" ? primaryValue : null;
  }, [showTitle, titleField, row, primaryValue]);

  const validColumns = useMemo(() => Array.isArray(columns) ? columns.filter(isValidColumn) : [], [columns]);
  const renderedActions = useMemo(() => renderActions ? safeRender(renderActions, row) : null, [renderActions, row]);
  const renderedExpandedFooter = useMemo(() => renderExpandedFooter ? safeRender(renderExpandedFooter, row) : null, [renderExpandedFooter, row]);

  if (!row || typeof row !== "object") return null;

  return (
    <>
      <TableRow
        sx={{
          "& > *": { borderBottom: "unset" },
          cursor: onRowClick ? "pointer" : "default",
          "&:hover": { backgroundColor: C.hover },
        }}
        onClick={handleRowClick}
      >
        <TableCell sx={{ width: 40, p: "6px 8px" }}>
          <IconButton size="small" onClick={handleToggle} sx={{ color: C.textMuted }}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell component="th" scope="row" sx={{ color: C.text, width: "100%" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {typeof primaryIcon === "function" ? primaryIcon(row) : primaryIcon}
            <Box sx={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
              {typeof primaryValue === "string" ? (
                <Typography variant="body2" fontWeight="medium" sx={{ color: C.text, wordBreak: "break-word" }}>
                  {primaryValue}
                </Typography>
              ) : (
                primaryValue
              )}
              {secondaryValue && (
                <Typography variant="caption" sx={{ color: C.textMuted }}>
                  {secondaryValue}
                </Typography>
              )}
            </Box>
          </Box>
        </TableCell>
      </TableRow>

      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={2}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ mx: 1, my: 2 }}>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                {titleValue && (
                  <Typography variant="subtitle2" fontWeight="bold" sx={{ color: C.text }}>
                    {titleValue}
                  </Typography>
                )}

                {validColumns.map((col) => {
                  if (safeRender(col.hide, row, false)) return null;

                  const value = col.valueGetter
                    ? safeRender(col.valueGetter, row)
                    : safeGetValue(row, col.field);

                  const cellContent = col.renderCell
                    ? safeRender(col.renderCell, { row, value }, <Typography variant="body2" sx={{ color: C.text }}>{value ?? "—"}</Typography>)
                    : <Typography variant="body2" sx={{ color: C.text }}>{value ?? "—"}</Typography>;

                  return (
                    <Box key={col.field} sx={{ display: "flex", alignItems: "flex-start", gap: 1, minWidth: 0 }}>
                      <Typography
                        variant="body2"
                        fontWeight="600"
                        sx={{ minWidth: col.labelWidth || labelWidth, flexShrink: 0, color: C.textMuted }}
                      >
                        {col.headerName || col.field}:
                      </Typography>
                      <Box sx={{ minWidth: 0, overflow: "hidden", wordBreak: "break-all" }}>
                        {cellContent}
                      </Box>
                    </Box>
                  );
                })}

                {renderedActions && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 1 }}>
                    <Typography variant="body2" fontWeight="600" sx={{ minWidth: labelWidth, color: C.textMuted }}>
                      {actionsLabel || t.common.actions}:
                    </Typography>
                    <Stack direction="row" spacing={0.5}>
                      {renderedActions}
                    </Stack>
                  </Box>
                )}

                {renderedExpandedFooter}
              </Box>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
};

AccordionRow.propTypes = {
  row: PropTypes.object.isRequired,
  columns: PropTypes.array.isRequired,
  primaryField: PropTypes.oneOfType([PropTypes.string, PropTypes.func]).isRequired,
  primaryIcon: PropTypes.node,
  secondaryField: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
  showTitle: PropTypes.bool,
  titleField: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
  renderActions: PropTypes.func,
  actionsLabel: PropTypes.string,
  onRowClick: PropTypes.func,
  defaultExpanded: PropTypes.bool,
  labelWidth: PropTypes.number,
  renderExpandedFooter: PropTypes.func,
};

AccordionRow.defaultProps = {
  defaultExpanded: false,
  showTitle: true,
  labelWidth: 120,
};

// ─── Main component ───────────────────────────────────────────────────────────

export const UniversalMobilDataTable = ({
  rows = [],
  columns = [],
  primaryField,
  primaryIcon = null,
  secondaryField = null,
  showTitle = true,
  titleField = null,
  labelWidth = 120,
  headerTitle = null,
  headerActions = null,
  hideHeader = false,
  subHeader = null,
  loading = false,
  error = null,
  emptyMessage = null,
  onRowClick = null,
  renderActions = null,
  actionsLabel = null,
  getRowId = (row) => row?.id ?? Math.random().toString(36).slice(2),
  defaultExpanded = false,
  renderExpandedFooter = null,
  enablePagination = true,
  rowsPerPageOptions = [10, 25, 50, 100],
  sx = {},
}) => {
  const processedRows = useMemo(() => {
    if (!Array.isArray(rows)) return [];
    return rows.filter((r) => r && typeof r === "object");
  }, [rows]);

  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(rowsPerPageOptions[0] || 10);

  useEffect(() => { setPage(0); }, [processedRows.length]);

  const paginatedRows = useMemo(() => {
    if (!enablePagination) return processedRows;
    return processedRows.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  }, [processedRows, page, rowsPerPage, enablePagination]);

  const handleChangePage = useCallback((_, newPage) => setPage(newPage), []);
  const handleChangeRowsPerPage = useCallback((e) => {
    setRowsPerPage(parseInt(e.target.value, 10));
    setPage(0);
  }, []);

  const validColumns = useMemo(() => Array.isArray(columns) ? columns.filter(isValidColumn) : [], [columns]);

  const safeGetRowId = useCallback((row) => {
    try {
      return getRowId(row) ?? Math.random().toString(36).slice(2);
    } catch {
      return Math.random().toString(36).slice(2);
    }
  }, [getRowId]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 200, ...sx }}>
        <ListingCircularProgress />
      </Box>
    );
  }

  if (error) {
    const msg = typeof error === "string" ? error : error?.message || t.common.loadError;
    return <AlertInline message={msg} severity="error" sx={sx} />;
  }

  return (
    <Box sx={{ width: "100%", overflowX: "hidden", ...sx }}>
      {!hideHeader && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: headerActions ? "1fr auto 1fr" : "1fr",
            alignItems: "center",
            my: 2,
          }}
        >
          {headerActions && <Box />}
          <Typography
            variant="subtitle1"
            fontWeight="bold"
            sx={{ textAlign: "center", color: C.text, fontFamily: "'Inter', sans-serif" }}
          >
            {headerTitle || t.common.details}
          </Typography>
          {headerActions && (
            <Box sx={{ display: "flex", justifyContent: "flex-end", pr: 1 }}>
              {headerActions}
            </Box>
          )}
        </Box>
      )}

      {subHeader}

      {processedRows.length === 0 ? (
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            minHeight: 200,
            border: `1px solid ${C.border}`,
            borderRadius: "1rem",
            backgroundColor: C.bg,
          }}
        >
          <Typography variant="body1" sx={{ color: C.textMuted }}>
            {emptyMessage || t.common.noData}
          </Typography>
        </Box>
      ) : (
        <>
          <TableContainer
            component={Paper}
            elevation={0}
            sx={{
              border: `1px solid ${C.border}`,
              borderRadius: "1rem",
              overflowX: "hidden",
              backgroundColor: C.bg,
            }}
          >
            <Table sx={{ tableLayout: "fixed", width: "100%" }}>
              <TableBody>
                {paginatedRows.map((row) => (
                  <AccordionRow
                    key={safeGetRowId(row)}
                    row={row}
                    columns={validColumns}
                    primaryField={primaryField}
                    primaryIcon={primaryIcon}
                    secondaryField={secondaryField}
                    showTitle={showTitle}
                    titleField={titleField}
                    renderActions={renderActions}
                    actionsLabel={actionsLabel}
                    onRowClick={onRowClick}
                    defaultExpanded={defaultExpanded}
                    labelWidth={labelWidth}
                    renderExpandedFooter={renderExpandedFooter}
                  />
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {enablePagination && (
            <Paper elevation={0} sx={{ mt: 1, borderRadius: "1rem", backgroundColor: C.headerBg }}>
              <TablePagination
                component="div"
                count={processedRows.length}
                page={page}
                onPageChange={handleChangePage}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={handleChangeRowsPerPage}
                rowsPerPageOptions={rowsPerPageOptions}
                labelRowsPerPage={t.common.rowsPerPage}
                labelDisplayedRows={({ from, to, count }) => t.common.rowsOf(from, to, count)}
                sx={{ color: C.textMuted, "& .MuiIconButton-root": { color: C.textMuted } }}
              />
            </Paper>
          )}
        </>
      )}
    </Box>
  );
};

UniversalMobilDataTable.propTypes = {
  rows: PropTypes.array,
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      field: PropTypes.string.isRequired,
      headerName: PropTypes.string,
      labelWidth: PropTypes.number,
      valueGetter: PropTypes.func,
      renderCell: PropTypes.func,
      hide: PropTypes.func,
    })
  ),
  primaryField: PropTypes.oneOfType([PropTypes.string, PropTypes.func]).isRequired,
  primaryIcon: PropTypes.node,
  secondaryField: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
  showTitle: PropTypes.bool,
  titleField: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
  headerTitle: PropTypes.string,
  headerActions: PropTypes.node,
  hideHeader: PropTypes.bool,
  subHeader: PropTypes.node,
  loading: PropTypes.bool,
  error: PropTypes.oneOfType([PropTypes.object, PropTypes.string]),
  emptyMessage: PropTypes.string,
  onRowClick: PropTypes.func,
  renderActions: PropTypes.func,
  actionsLabel: PropTypes.string,
  getRowId: PropTypes.func,
  defaultExpanded: PropTypes.bool,
  labelWidth: PropTypes.number,
  renderExpandedFooter: PropTypes.func,
  enablePagination: PropTypes.bool,
  rowsPerPageOptions: PropTypes.arrayOf(PropTypes.number),
  sx: PropTypes.object,
};
