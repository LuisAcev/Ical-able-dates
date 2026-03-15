import { useState, useCallback } from 'react';
import {
  useGetListingsQuery,
  useUpdateListingIcalMutation,
  useUpdateAllListingsMutation,
  useGetStatusQuery,
} from '../../../store/api/api';

export const useListingTable = () => {
  const [updatingIds, setUpdatingIds] = useState(new Set());

  const {
    data: listings = [],
    isLoading: loading,
    error: listingsError,
    refetch: refetchListings,
  } = useGetListingsQuery();

  const [updateIcal] = useUpdateListingIcalMutation();
  const [updateAll] = useUpdateAllListingsMutation();

  const {
    data: status,
  } = useGetStatusQuery(undefined, {
    pollingInterval: updatingIds.size > 0 ? 3000 : 0,
  });

  const isUpdating = status?.updating ?? false;

  // Cuando status deja de actualizar, refrescar listings y limpiar IDs
  const prevUpdating = status?.updating;
  if (prevUpdating === false && updatingIds.size > 0) {
    setUpdatingIds(new Set());
    refetchListings();
  }

  const handleUpdateOne = useCallback(async (listingId) => {
    try {
      setUpdatingIds((prev) => new Set(prev).add(listingId));
      await updateIcal(listingId).unwrap();
    } catch {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(listingId);
        return next;
      });
    }
  }, [updateIcal]);

  const handleUpdateAll = useCallback(async () => {
    try {
      // Marcar todos como updating
      const allIds = new Set(listings.map((l) => l.listing_id));
      setUpdatingIds(allIds);
      await updateAll().unwrap();
    } catch {
      setUpdatingIds(new Set());
    }
  }, [updateAll, listings]);

  return {
    listings,
    loading,
    updatingIds,
    isUpdating,
    status,
    error: listingsError,
    handleUpdateOne,
    handleUpdateAll,
    refetchListings,
  };
};
