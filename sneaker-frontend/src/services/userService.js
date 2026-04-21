import apiClient from './apiClient';

export async function fetchRecentViewedApi() {
  const res = await apiClient.get('/recently-viewed');
  return res.data;
}

export async function fetchFavoritesApi() {
  const res = await apiClient.get('/favorites');
  return res.data;
}

export async function fetchCartApi() {
  const res = await apiClient.get('/cart');
  return res.data;
}

export async function fetchOrdersApi() {
  const res = await apiClient.get('/orders');
  return res.data;
}