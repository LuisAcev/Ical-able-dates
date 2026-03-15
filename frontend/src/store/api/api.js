import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

export const listingsApi = createApi({
  reducerPath: 'listingsApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api' }),
  tagTypes: ['Listings', 'Status'],
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

  }),
});

export const {
  useGetListingsQuery,
  useRegisterListingMutation,
  useUpdateListingDataMutation,
  useUpdateListingIcalMutation,
  useUpdateAllListingsMutation,
  useGetStatusQuery,
} = listingsApi;
