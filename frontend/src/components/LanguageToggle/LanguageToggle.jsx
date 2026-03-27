import { useState } from "react";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import ListItemText from "@mui/material/ListItemText";
import CheckIcon from "@mui/icons-material/Check";
import { useI18n } from "../../i18n/useI18n";

export const LanguageToggle = () => {
  const { locale, changeLocale, localeOptions } = useI18n();
  const [anchorEl, setAnchorEl] = useState(null);

  return (
    <>
      <IconButton
        onClick={(e) => setAnchorEl(e.currentTarget)}
        sx={{
          ml: "auto",
          width: 40,
          height: 40,
          borderRadius: "50%",
          fontSize: "0.8rem",
          fontWeight: 700,
          color: "#fff",
          backgroundColor: "#16A34A",
          "&:hover": { backgroundColor: "#15803d" },
        }}
      >
        {locale.toUpperCase()}
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        slotProps={{ paper: { sx: { backgroundColor: "#424242", color: "#E0E0E0", borderRadius: "8px" } } }}
      >
        {localeOptions.map((opt) => (
          <MenuItem
            key={opt.code}
            selected={locale === opt.code}
            onClick={() => { changeLocale(opt.code); setAnchorEl(null); }}
            sx={{ "&.Mui-selected": { backgroundColor: "rgba(22, 163, 74, 0.2)" }, "&:hover": { backgroundColor: "rgba(255,255,255,0.08)" } }}
          >
            <ListItemText>{opt.label}</ListItemText>
            {locale === opt.code && <CheckIcon sx={{ ml: 1, fontSize: 18, color: "#16A34A" }} />}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};
