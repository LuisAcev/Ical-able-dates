import { useRef, useEffect } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { ListingTable } from "../components/Listing tables/ListingTable";
import { useListingTable } from "../components/Listing tables/hook/useListingTable";
import { UpdateIcalButton } from "../components/UpdateIcalButton/UpdateIcalButton";
import { AlertInline } from "../components/AlertInline/AlertInline";
import { IcalBaseUrlInput } from "../components/IcalBaseUrlInput/IcalBaseUrlInput";
import { AddListing } from "../components/AddListing/AddListing";
import { t } from "../i18n";

export const Canvas = () => {
  const alertRef = useRef();
  const {
    listings, loading, error, updatingIds, isUpdating,
    status, handleUpdateOne, handleUpdateAll, handleToggleIcal,
  } = useListingTable(alertRef);

  useEffect(() => {
    if (error) {
      alertRef.current?.showError(
        error.error || error.message || t.listingTable.loadError
      );
    }
  }, [error]);

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: "auto", color: "#515151" }}>
      <AlertInline ref={alertRef} asSnackbar />
      {/* <Typography variant="h4" sx={{ mb: 3 }}>
        {t.canvas.title}
      </Typography> */}
      <Box sx={{ display: "flex", flexDirection: "row", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <UpdateIcalButton
          isUpdating={isUpdating}
          handleUpdateAll={handleUpdateAll}
          status={status}
        />
        <IcalBaseUrlInput alertRef={alertRef} />
        <AddListing alertRef={alertRef} />
      </Box>
      <ListingTable
        listings={listings}
        loading={loading}
        error={error}
        updatingIds={updatingIds}
        handleUpdateOne={handleUpdateOne}
        handleToggleIcal={handleToggleIcal}
        alertRef={alertRef}
      />
    </Box>
  );
};
