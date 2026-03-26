import Button from "@mui/material/Button";
import { ListingCircularProgress } from "../ListingCircularProgress/ListingCircularProgress";
import { primaryIconButton } from "../../styles/styles";
import { t } from "../../i18n";

export const UpdateIcalButton = ({ isUpdating, handleUpdateAll, status }) => {
  const label = isUpdating
    ? status?.total
      ? t.updateAll.updating(status.progress, status.total)
      : t.updateAll.starting
    : t.updateAll.button;

  return (
    <Button
      variant="contained"
      size="large"
      disabled={isUpdating}
      onClick={handleUpdateAll}
      startIcon={
        isUpdating ? <ListingCircularProgress size={20} color="inherit" /> : null
      }
      sx={primaryIconButton}
    >
      {label}
    </Button>
  );
};
