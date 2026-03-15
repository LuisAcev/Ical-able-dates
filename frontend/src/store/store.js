import { configureStore } from '@reduxjs/toolkit';
import { listingsApi } from './api/api';

export const store = configureStore({
  reducer: {
    [listingsApi.reducerPath]: listingsApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(listingsApi.middleware),
});
