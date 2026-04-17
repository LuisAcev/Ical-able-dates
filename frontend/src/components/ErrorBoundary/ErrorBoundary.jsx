import { Component } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            backgroundColor: "#2c2c2c",
            gap: 2,
            p: 4,
          }}
        >
          <Typography variant="h5" sx={{ color: "#ef9a9a" }}>
            Algo salió mal
          </Typography>
          <Typography variant="body2" sx={{ color: "#777", textAlign: "center", maxWidth: 400 }}>
            {this.state.error?.message || "Error inesperado"}
          </Typography>
          <Button
            variant="contained"
            onClick={() => window.location.reload()}
            sx={{ borderRadius: "1rem", textTransform: "none", backgroundColor: "#16A34A", "&:hover": { backgroundColor: "#15803d" } }}
          >
            Recargar página
          </Button>
        </Box>
      );
    }
    return this.props.children;
  }
}
