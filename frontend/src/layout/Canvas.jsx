import { useRef, useState } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import SearchIcon from "@mui/icons-material/Search";
import { ListingTable } from "../components/Listing tables/ListingTable";
import { useListingTable } from "../components/Listing tables/hook/useListingTable";
import { UpdateIcalButton } from "../components/UpdateIcalButton/UpdateIcalButton";
import { AlertInline } from "../components/AlertInline/AlertInline";
import { IcalBaseUrlInput } from "../components/IcalBaseUrlInput/IcalBaseUrlInput";
import { AddListing } from "../components/AddListing/AddListing";
import { LanguageToggle } from "../components/LanguageToggle/LanguageToggle";
import { useI18n } from "../i18n/useI18n";
import { t } from "../i18n";

export const Canvas = () => {
  const { locale } = useI18n();
  const alertRef = useRef();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const {
    listings, loading, error, updatingIds, isUpdating,
    status, handleUpdateOne, handleUpdateAll, handleCancelUpdate, handleToggleIcal,
  } = useListingTable(alertRef);

  return (
    <Box key={locale} sx={{ p: 3, maxWidth: "90vw", mx: "auto", color: "#515151" }}>
      <AlertInline ref={alertRef} asSnackbar />
      <Box sx={{ display: "flex", flexDirection: "row", gap: 2, mb: 3, flexWrap: "wrap", alignItems: "center" }}>
        <UpdateIcalButton
          isUpdating={isUpdating}
          handleUpdateAll={handleUpdateAll}
          handleCancelUpdate={handleCancelUpdate}
          status={status}
        />
        <Box sx={{ display: { xs: "none", md: "block" } }}>
          <IcalBaseUrlInput alertRef={alertRef} />
        </Box>
        <AddListing alertRef={alertRef} />
        <Tooltip title={filtersOpen ? t.common.hideFilters : t.common.showFilters}>
          <IconButton
            onClick={() => setFiltersOpen((v) => !v)}
            sx={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              color: "#fff",
              backgroundColor: filtersOpen ? "#15803d" : "#16A34A",
              boxShadow: filtersOpen ? "0 0 0 3px rgba(22,163,74,0.35)" : "none",
              "&:hover": { backgroundColor: "#15803d" },
            }}
          >
            <SearchIcon sx={{ fontSize: 20 }} />
          </IconButton>
        </Tooltip>
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
        filtersOpen={filtersOpen}
      />
    </Box>
  );
};
