import { forwardRef, useImperativeHandle, useState, useCallback } from "react";
import { Alert, Snackbar } from "@mui/material";
import { t } from "../../i18n";

/**
 * AlertInline - Componente unificado para alertas y notificaciones
 *
 * MODO INLINE (por defecto):
 * <AlertInline message="Error message" severity="error" />
 *
 * MODO SNACKBAR (con ref):
 * const alertRef = useRef();
 * alertRef.current?.showSuccess("Guardado exitosamente");
 * <AlertInline ref={alertRef} asSnackbar />
 */
export const AlertInline = forwardRef(
  (
    {
      message,
      children,
      severity = "error",
      variant = "standard",
      icon,
      onClose,
      sx = {},
      asSnackbar = false,
      autoHideDuration = 4000,
      position = { vertical: "top", horizontal: "center" },
    },
    ref
  ) => {
    const [snackbarState, setSnackbarState] = useState({
      open: false,
      message: "",
      severity: "success",
    });

    const show = useCallback((msg, sev) => {
      setSnackbarState({ open: true, message: msg, severity: sev });
    }, []);

    const showSuccess = useCallback(
      (msg) => show(msg || t.alert.defaultSuccess, "success"),
      [show]
    );
    const showError = useCallback(
      (msg) => show(msg || t.alert.defaultError, "error"),
      [show]
    );
    const showWarning = useCallback(
      (msg) => show(msg || t.alert.defaultWarning, "warning"),
      [show]
    );
    const showInfo = useCallback(
      (msg) => show(msg || t.alert.defaultInfo, "info"),
      [show]
    );
    const hide = useCallback(() => {
      setSnackbarState((prev) => ({ ...prev, open: false }));
    }, []);

    useImperativeHandle(
      ref,
      () => ({ showSuccess, showError, showWarning, showInfo, hide }),
      [showSuccess, showError, showWarning, showInfo, hide]
    );

    const handleClose = (_event, reason) => {
      if (reason === "clickaway") return;
      hide();
    };

    const alertStyles = { borderRadius: "1.5rem", ...sx };

    if (asSnackbar) {
      return (
        <Snackbar
          open={snackbarState.open}
          autoHideDuration={autoHideDuration}
          onClose={handleClose}
          anchorOrigin={position}
        >
          <Alert
            onClose={handleClose}
            severity={snackbarState.severity}
            variant={variant}
            sx={alertStyles}
          >
            {snackbarState.message}
          </Alert>
        </Snackbar>
      );
    }

    return (
      <Alert
        severity={severity}
        variant={variant}
        icon={icon}
        onClose={onClose}
        sx={alertStyles}
      >
        {children || message}
      </Alert>
    );
  }
);

AlertInline.displayName = "AlertInline";
