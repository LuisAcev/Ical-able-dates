import Button from "@mui/material/Button";
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
        <Button
          variant="contained"
          size="large"
          disabled
          startIcon={<ListingCircularProgress size={20} color="inherit" />}
          endIcon={
            <Tooltip title={t.updateAll.cancelButton} arrow>
              <CancelIcon
                sx={{ width: 18, height: 18, color: "#ffcdd2", cursor: "pointer", pointerEvents: "auto" }}
                onClick={(e) => { e.stopPropagation(); handleCancelUpdate(); }}
              />
            </Tooltip>
          }
          sx={{ ...primaryIconButton, minWidth: "auto" }}
        >
          {counter}
        </Button>
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
