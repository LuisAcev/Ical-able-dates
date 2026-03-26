import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import { ListingCircularProgress } from '../ListingCircularProgress/ListingCircularProgress';
import { AlertInline } from '../AlertInline/AlertInline';
import { useRegisterListingMutation } from '../../store/api/api';
import { t } from '../../i18n';

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

  const isValidId = (id) => /^\d+$/.test(id.trim());

  const handleSubmit = async () => {
    if (!isValidId(listingId)) return;
    const result = await registerListing(listingId.trim());
    if (!result.error) handleClose();
  };

  return (
    <>
      <Button variant="contained" onClick={handleOpen} sx={{ mb: 2 }}>
        {t.registerListing.openButton}
      </Button>

      <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
        <DialogTitle>{t.registerListing.dialogTitle}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label={t.registerListing.inputLabel}
            placeholder={t.registerListing.inputPlaceholder}
            value={listingId}
            onChange={(e) => setListingId(e.target.value)}
            fullWidth
            disabled={isLoading}
            sx={{ mt: 1 }}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          {error && (
            <AlertInline
              severity="error"
              message={error.data?.detail || t.registerListing.errorFallback}
              sx={{ mt: 2 }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={isLoading}>
            {t.registerListing.cancelButton}
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={isLoading || !isValidId(listingId)}
            startIcon={isLoading ? <ListingCircularProgress size={16} color="inherit" /> : null}
          >
            {isLoading ? t.registerListing.submitting : t.registerListing.submitButton}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
