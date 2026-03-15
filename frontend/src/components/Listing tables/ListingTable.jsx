import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Chip from '@mui/material/Chip';
import { DataGrid } from '@mui/x-data-grid';
import { useListingTable } from './hook/useListingTable';

const formatDate = (iso) => {
  if (!iso) return 'Nunca';
  const d = new Date(iso);
  return d.toLocaleString('es-CO', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

const bedroomLabel = (val) => {
  const n = parseInt(val, 10);
  if (n === 0) return 'Estudio';
  return `${n} hab`;
};

export const ListingTable = () => {
  const {
    listings, loading, updatingIds, isUpdating,
    handleUpdateOne, handleUpdateAll, status,
  } = useListingTable();

  const columns = [
    {
      field: 'listing_id',
      headerName: 'Listing ID',
      width: 110,
    },
    {
      field: 'title',
      headerName: 'Título',
      flex: 1,
      minWidth: 200,
      renderCell: (params) =>
        params.value || <em style={{ color: '#999' }}>Sin título</em>,
    },
    {
      field: 'resort_codes',
      headerName: 'Resort Codes',
      width: 180,
      renderCell: (params) =>
        (params.value || []).map((code) => (
          <Chip key={code} label={code} size="small" sx={{ mr: 0.5 }} />
        )),
    },
    {
      field: 'bedrooms',
      headerName: 'Tipo',
      width: 90,
      renderCell: (params) => bedroomLabel(params.value),
    },
    {
      field: 'sync_mode',
      headerName: 'Sync',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value === 'primary' ? 'primary' : 'default'}
        />
      ),
    },
    {
      field: 'has_ical',
      headerName: 'iCal',
      width: 70,
      renderCell: (params) => params.value ? '✓' : '—',
    },
    {
      field: 'last_updated',
      headerName: 'Última actualización',
      width: 170,
      renderCell: (params) => formatDate(params.value),
    },
    {
      field: 'actions',
      headerName: 'Acción',
      width: 130,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const lid = params.row.listing_id;
        const busy = updatingIds.has(lid) || isUpdating;
        return (
          <Button
            variant="outlined"
            size="small"
            disabled={busy}
            onClick={() => handleUpdateOne(lid)}
            startIcon={busy ? <CircularProgress size={16} /> : null}
          >
            {busy ? 'Actualizando' : 'Actualizar'}
          </Button>
        );
      },
    },
  ];

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ height: 700, width: '100%' }}>
        <DataGrid
          rows={listings}
          columns={columns}
          getRowId={(row) => row.listing_id}
          initialState={{
            pagination: { paginationModel: { pageSize: 25 } },
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          disableRowSelectionOnClick
          density="compact"
        />
      </Box>

      <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Button
          variant="contained"
          size="large"
          disabled={isUpdating}
          onClick={handleUpdateAll}
          startIcon={isUpdating ? <CircularProgress size={20} color="inherit" /> : null}
          sx={{ minWidth: 250, py: 1.5 }}
        >
          {isUpdating
            ? `Actualizando... ${status?.progress || 0}/${status?.total || 0}`
            : 'Actualizar todos los iCal'}
        </Button>
      </Box>
    </Box>
  );
};
