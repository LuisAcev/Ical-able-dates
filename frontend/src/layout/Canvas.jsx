import { useRef } from "react";
import Box from "@mui/material/Box";
import { ListingTable } from "../components/Listing tables/ListingTable";
import { useListingTable } from "../components/Listing tables/hook/useListingTable";
import { UpdateIcalButton } from "../components/UpdateIcalButton/UpdateIcalButton";
import { AlertInline } from "../components/AlertInline/AlertInline";
import { IcalBaseUrlInput } from "../components/IcalBaseUrlInput/IcalBaseUrlInput";
import { AddListing } from "../components/AddListing/AddListing";
import { LanguageToggle } from "../components/LanguageToggle/LanguageToggle";
import { useI18n } from "../i18n/useI18n";

export const Canvas = () => {
  const { locale } = useI18n();
  const alertRef = useRef();
  const {
    listings, loading, error, updatingIds, isUpdating,
    status, handleUpdateOne, handleUpdateAll, handleToggleIcal,
  } = useListingTable(alertRef);

  return (
    <Box key={locale} sx={{ p: 3, maxWidth: 1400, mx: "auto", color: "#515151" }}>
      <AlertInline ref={alertRef} asSnackbar />
      <Box sx={{ display: "flex", flexDirection: "row", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <UpdateIcalButton
          isUpdating={isUpdating}
          handleUpdateAll={handleUpdateAll}
          status={status}
        />
        <IcalBaseUrlInput alertRef={alertRef} />
        <AddListing alertRef={alertRef} />
        <LanguageToggle />
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
