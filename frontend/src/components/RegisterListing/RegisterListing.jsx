import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { useRegisterListingMutation } from '../../store/api/api';

export const RegisterListing = () => {
  const [open, setOpen] = useState(false);
  const [listingId, setListingId] = useState('');
  const [registerListing, { isLoading, error, reset }] = useRegisterListingMutation();

  const handleOpen = () => {
    setOpen(true);
    setListingId('');
    reset();
  };

  const handleClose = () => {
    if (isLoading) return;
    setOpen(false);
    setListingId('');
    reset();
  };

  const handleSubmit = async () => {
    if (!listingId.trim()) return;
    const result = await registerListing(listingId.trim());
    if (!result.error) handleClose();
  };

  return (
    <>
      <Button variant="contained" onClick={handleOpen} sx={{ mb: 2 }}>
        Registrar Listing
      </Button>

      <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
        <DialogTitle>Registrar nuevo Listing</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Airbnb Listing ID"
            placeholder="Ej: 1142004991848222683"
            value={listingId}
            onChange={(e) => setListingId(e.target.value)}
            fullWidth
            disabled={isLoading}
            sx={{ mt: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error.data?.detail || 'Error al registrar'}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={isLoading || !listingId.trim()}
            startIcon={isLoading ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {isLoading ? 'Obteniendo datos...' : 'Registrar'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
