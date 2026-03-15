import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { ListingTable } from '../components/Listing tables/ListingTable';
import { RegisterListing } from '../components/RegisterListing/RegisterListing';

export const Canvas = () => {
  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: 'auto' }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        AVI — Dashboard de Listings
      </Typography>
      <RegisterListing />
      <ListingTable />
    </Box>
  );
};
