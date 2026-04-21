import apiClient from './apiClient';

export async function fetchProductsApi(page = 1, size = 30) {
  const res = await apiClient.get('/products', {
    params: { page, size },
  });
  return res.data;
}

export async function fetchProductDetailApi(productId) {
  const res = await apiClient.get(`/products/detail/${productId}`);
  return res.data;
}

export async function interactProductApi(productId, actionType, quantity = 1) {
  const res = await apiClient.post('/interact', {
    product_id: String(productId),
    action_type: actionType,
    quantity,
  });
  return res.data;
}