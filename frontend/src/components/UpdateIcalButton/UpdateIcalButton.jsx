import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import SyncIcon from "@mui/icons-material/Sync";
import CancelIcon from "@mui/icons-material/Cancel";
import { ListingCircularProgress } from "../ListingCircularProgress/ListingCircularProgress";
import { primaryIconButton } from "../../styles/styles";
import { t } from "../../i18n";

export const UpdateIcalButton = ({ isUpdating, handleUpdateAll, handleCancelUpdate, status }) => {
  const counter = isUpdating
    ? status?.total
      ? t.updateAll.updating(status.progress, status.total)
      : t.updateAll.starting
    : null;

  return (
    <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
      {isUpdating ? (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            background: "linear-gradient(135deg, #16A34A, #15803d)",
            borderRadius: "1.5rem",
            height: 40,
            pl: 2,
            pr: 0.5,
            gap: 1,
          }}
        >
          <ListingCircularProgress size={18} color="inherit" sx={{ color: "#fff" }} />
          <Box sx={{ color: "#fff", fontSize: 14, fontFamily: "inherit", whiteSpace: "nowrap" }}>
            {counter}
          </Box>
          <Tooltip title={t.updateAll.cancelButton} arrow>
            <IconButton
              size="small"
              onClick={handleCancelUpdate}
              sx={{ color: "#ffcdd2", "&:hover": { color: "#fff", backgroundColor: "rgba(255,255,255,0.15)" } }}
            >
              <CancelIcon sx={{ width: 18, height: 18 }} />
            </IconButton>
          </Tooltip>
        </Box>
      ) : (
        <Tooltip title={t.updateAll.button} arrow>
          <span>
            <Button
              variant="contained"
              size="large"
              onClick={handleUpdateAll}
              sx={{ ...primaryIconButton, minWidth: "auto", padding: "8px 14px" }}
            >
              <SyncIcon sx={{ width: 20, height: 20 }} />
            </Button>
          </span>
        </Tooltip>
      )}
    </Box>
  );
};
