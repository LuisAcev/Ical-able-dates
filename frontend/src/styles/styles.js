// ================== COLORS ==================
const colors = {
  primary: "#16A34A",
  primaryHover: "#15803c8c",
  gradient: "linear-gradient(90deg, #1fb467c7, #0a6a38bb)",
  gradientHover: "#0f8d4cbb",
  white: "#FFFFFF",
  disabled: "#F3F4F6",
  disabledText: "#4B5563",
  // Table dark theme
  tableBg: "#515151",
  tableHeaderBg: "#3D3D3D",
  tableSortedBg: "#4A4A4A",
  tableHoverBg: "#5E5E5E",
  tableBorder: "#626262",
  tableText: "#E0E0E0",
  tableTextMuted: "#BDBDBD",
};

// ================== FONT ==================
const font = {
  family: "'Inter', sans-serif",
  sizeBody: "14px",
  sizeSmall: "12px",
  bold: 700,
};

// ================== BUTTON ==================
export const primaryIconButton = {
  height: 40,
  fontSize: 14,
  fontFamily: font.family,
  textTransform: "none",
  border: "none",
  borderRadius: "1.5rem",
  background: colors.gradient,
  color: colors.white,
  minWidth: "16vh",
  //gap: "2px",
  padding: "8px 16px",
  "& svg": { width: 14, height: 14 },
  "&:hover": {
    background: colors.gradientHover,
    boxShadow: `0 4px 10px ${colors.primaryHover}`,
  },
  "&:disabled": {
    background: colors.disabled,
    color: colors.disabledText,
  },
};

// ================== RESORT CODES ==================
export const resortCodes = {
  backgroundColor: colors.tableSortedBg,
  color: colors.tableText,
  borderColor: colors.tableBorder,
  mr: 0.5,
};

// ================== ACTION ICON BUTTON ==================
export const actionIconButton = {
  color: colors.primary,
  backgroundColor: "rgba(22, 163, 74, 0.57)",
  "&:hover": {
    backgroundColor: "rgb(15, 175, 74)",
  },
  "&:disabled": {
    color: colors.disabledText,
  },
};

// ================== DATA GRID ==================
export const dataGridTable = {
  borderRadius: "1rem",
  height: "auto",
  boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.2)",
  border: "none",
  backgroundColor: colors.tableBg,
  padding: 0,
  "& .MuiDataGrid-columnHeaders, & .MuiDataGrid-columnHeader": {
    backgroundColor: `${colors.tableHeaderBg} !important`,
  },
  "& .MuiDataGrid-columnHeaders": {
    borderBottom: `2px solid ${colors.tableBorder}`,
  },
  "& .MuiDataGrid-columnHeaderTitle": {
    fontWeight: font.bold,
    textTransform: "uppercase",
    fontSize: font.sizeSmall,
    fontFamily: font.family,
    color: colors.tableTextMuted,
    letterSpacing: "0.05em",
  },
  "& .MuiDataGrid-sortIcon": {
    color: colors.primary,
  },
  "& .MuiDataGrid-iconButtonContainer": {
    position: "absolute",
    bottom: 4,
    right: 0,
  },
  "& .MuiDataGrid-menuIcon": {
    position: "absolute",
    bottom: 4,
    right: 24,
  },
  "& .MuiDataGrid-columnHeader--sorted": {
    backgroundColor: `${colors.tableSortedBg} !important`,
  },
  "& .MuiDataGrid-filler": {
    backgroundColor: `${colors.tableBg} !important`,
    width: "0 !important",
    minWidth: "0 !important",
    maxWidth: "0 !important",
  },
  "& .MuiDataGrid-scrollbarFiller": {
    display: "none !important",
  },
  "& .MuiDataGrid-scrollbar--vertical": {
    position: "absolute",
    right: 0,
  },
  // Row text Style
  "& .MuiDataGrid-cell": {
    borderBottom: `1px solid ${colors.tableBorder}`,
    fontSize: 14,
    fontFamily: font.family,
    color: colors.white,
  },
  "& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within, & .MuiDataGrid-columnHeader:focus, & .MuiDataGrid-columnHeader:focus-within":
    {
      outline: "none",
    },
  "& .MuiDataGrid-row:hover": {
    backgroundColor: `${colors.tableHoverBg} !important`,
  },
  "& .MuiDataGrid-footerContainer": {
    borderTop: `1px solid ${colors.tableBorder}`,
    color: colors.tableTextMuted,
  },
  "& .MuiTablePagination-root, & .MuiIconButton-root": {
    color: colors.tableTextMuted,
  },
};
