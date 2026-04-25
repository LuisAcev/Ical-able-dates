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
      <Box sx={{
        display: "flex",
        flexDirection: "row",
        mb: 3,
        flexWrap: "nowrap",
        alignItems: "center",
        justifyContent: { xs: "space-between", md: "flex-start" },
        gap: { xs: 0, md: 2 },
      }}>
        {/* Izquierda: actualizar */}
        <UpdateIcalButton
          isUpdating={isUpdating}
          handleUpdateAll={handleUpdateAll}
          handleCancelUpdate={handleCancelUpdate}
          status={status}
        />

        {/* Centro/derecha desktop: URL iCal + Agregar */}
        <Box sx={{ display: { xs: "none", md: "flex" }, gap: 2, alignItems: "center" }}>
          <IcalBaseUrlInput alertRef={alertRef} />
          <AddListing alertRef={alertRef} />
        </Box>

        {/* Derecha mobile: filtros + agregar + idioma agrupados */}
        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
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
          <Box sx={{ display: { xs: "block", md: "none" } }}>
            <AddListing alertRef={alertRef} />
          </Box>
          {/* Idioma: visible en mobile aquí, en desktop se mueve al extremo derecho */}
          <Box sx={{ display: { xs: "block", md: "none" } }}>
            <LanguageToggle />
          </Box>
        </Box>

        {/* Idioma desktop: extremo derecho con ml:auto */}
        <Box sx={{ display: { xs: "none", md: "block" }, ml: "auto" }}>
          <LanguageToggle />
        </Box>
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
