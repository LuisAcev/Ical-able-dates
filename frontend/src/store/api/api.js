import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const listingsApi = createApi({
  reducerPath: 'listingsApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  tagTypes: ['Listings', 'Status', 'Settings'],
  keepUnusedDataFor: 120,
  refetchOnReconnect: true,
  endpoints: (builder) => ({

    getListings: builder.query({
      query: () => '/listings',
      transformResponse: (res) => res.listings,
      providesTags: ['Listings'],
    }),

    registerListing: builder.mutation({
      query: (listingId) => ({
        url: '/listings',
        method: 'POST',
        body: { listing_id: String(listingId) },
      }),
      invalidatesTags: ['Listings', 'Status'],
    }),

    createListingManual: builder.mutation({
      query: (body) => ({
        url: '/listings/manual',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Listings'],
    }),

    updateListingData: builder.mutation({
      query: ({ listingId, ...body }) => ({
        url: `/listings/${listingId}`,
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Listings'],
    }),

    deleteListing: builder.mutation({
      query: (listingId) => ({
        url: `/listings/${listingId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Listings'],
    }),

    toggleIcal: builder.mutation({
      query: ({ listingId, ical_enabled }) => ({
        url: `/listings/${listingId}/toggle-ical`,
        method: 'PATCH',
        body: { ical_enabled },
      }),
      invalidatesTags: ['Listings'],
    }),

    updateListingIcal: builder.mutation({
      query: (listingId) => ({
        url: `/listings/${listingId}/update`,
        method: 'POST',
      }),
      invalidatesTags: ['Status'],
    }),

    updateAllListings: builder.mutation({
      query: () => ({
        url: '/update-all',
        method: 'POST',
      }),
      invalidatesTags: ['Status'],
    }),

    getStatus: builder.query({
      query: () => '/status',
      providesTags: ['Status'],
    }),

    getIcalBaseUrl: builder.query({
      query: () => '/settings/ical-base-url',
      providesTags: ['Settings'],
    }),

    setIcalBaseUrl: builder.mutation({
      query: (base_url) => ({
        url: '/settings/ical-base-url',
        method: 'PUT',
        body: { base_url },
      }),
      invalidatesTags: ['Settings', 'Listings'],
    }),

  }),
});

export const {
  useGetListingsQuery,
  useRegisterListingMutation,
  useToggleIcalMutation,
  useUpdateListingIcalMutation,
  useUpdateAllListingsMutation,
  useGetStatusQuery,
  useGetIcalBaseUrlQuery,
  useSetIcalBaseUrlMutation,
  useCreateListingManualMutation,
  useDeleteListingMutation,
  useUpdateListingDataMutation,
} = listingsApi;
