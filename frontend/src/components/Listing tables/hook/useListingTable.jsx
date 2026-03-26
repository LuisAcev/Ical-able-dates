import { useState, useCallback, useRef, useEffect } from 'react';
import {
  useGetListingsQuery,
  useUpdateListingIcalMutation,
  useUpdateAllListingsMutation,
  useGetStatusQuery,
  useToggleIcalMutation,
} from '../../../store/api/api';
import { t } from '../../../i18n';

export const useListingTable = (alertRef) => {
  const [updatingIds, setUpdatingIds] = useState(new Set());
  const wasUpdatingRef = useRef(false);
  const updateInFlightRef = useRef(false);

  const {
    data: listings = [],
    isLoading: loading,
    error: listingsError,
    refetch: refetchListings,
  } = useGetListingsQuery();

  const [updateIcal] = useUpdateListingIcalMutation();
  const [updateAll] = useUpdateAllListingsMutation();
  const [toggleIcal] = useToggleIcalMutation();

  const {
    data: status,
  } = useGetStatusQuery(undefined, {
    pollingInterval: updatingIds.size > 0 ? 3000 : 0,
  });

  const isUpdating = status?.updating ?? false;

  // Cuando status pasa de updating=true a updating=false, limpiar y notificar
  useEffect(() => {
    if (wasUpdatingRef.current && !isUpdating) {
      const hadError = status?.error;
      setUpdatingIds(new Set());
      updateInFlightRef.current = false;
      refetchListings();
      if (hadError) {
        alertRef?.current?.showError(t.updateAll.updateError(hadError));
      } else {
        alertRef?.current?.showSuccess(t.updateAll.updateSuccess);
      }
    }
    wasUpdatingRef.current = isUpdating;
  }, [isUpdating, refetchListings, status?.error, alertRef]);

  const handleUpdateOne = useCallback(async (listingId) => {
    if (updateInFlightRef.current) return;
    updateInFlightRef.current = true;
    try {
      setUpdatingIds(new Set([listingId]));
      await updateIcal(listingId).unwrap();
    } catch (err) {
      setUpdatingIds(new Set());
      updateInFlightRef.current = false;
      alertRef?.current?.showError(
        err?.data?.detail || t.updateAll.startSingleError
      );
    }
  }, [updateIcal, alertRef]);

  const handleToggleIcal = useCallback(async (listingId, icalEnabled) => {
    try {
      await toggleIcal({ listingId, ical_enabled: icalEnabled }).unwrap();
      alertRef?.current?.showSuccess(
        icalEnabled
          ? t.icalToggle.unlockSuccess
          : t.icalToggle.lockSuccess
      );
    } catch (err) {
      alertRef?.current?.showError(
        err?.data?.detail || t.icalToggle.toggleError
      );
    }
  }, [toggleIcal, alertRef]);

  const handleUpdateAll = useCallback(async () => {
    if (updateInFlightRef.current) return;
    updateInFlightRef.current = true;
    try {
      const allIds = new Set(listings.map((l) => l.listing_id));
      setUpdatingIds(allIds);
      await updateAll().unwrap();
    } catch (err) {
      setUpdatingIds(new Set());
      updateInFlightRef.current = false;
      alertRef?.current?.showError(
        err?.data?.detail || t.updateAll.startAllError
      );
    }
  }, [updateAll, listings, alertRef]);

  return {
    listings,
    loading,
    updatingIds,
    isUpdating,
    status,
    error: listingsError,
    handleUpdateOne,
    handleUpdateAll,
    handleToggleIcal,
  };
};
