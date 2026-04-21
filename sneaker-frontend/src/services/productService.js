import apiClient from './apiClient';

function normalizePositiveInteger(value, fallback = 1) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return fallback;
  }
  return Math.floor(parsed);
}

function normalizeActionType(actionType) {
  return String(actionType || '').trim().toLowerCase();
}

export async function fetchProductsApi(page = 1, size = 30) {
  const res = await apiClient.get('/products', {
    params: {
      page: normalizePositiveInteger(page, 1),
      size: normalizePositiveInteger(size, 30),
    },
  });
  return res.data;
}

export async function fetchHomepageProductsApi(page = 1, size = 30) {
  const res = await apiClient.get('/products/homepage', {
    params: {
      page: normalizePositiveInteger(page, 1),
      size: normalizePositiveInteger(size, 30),
    },
  });
  return res.data;
}

export async function fetchProductDetailApi(productId) {
  const safeProductId = String(productId || '').trim();

  if (!safeProductId) {
    throw new Error('productId is required');
  }

  const res = await apiClient.get(`/products/detail/${safeProductId}`);
  return res.data;
}

export async function interactProductApi(productId, actionType, quantity = 1) {
  const safeProductId = String(productId || '').trim();
  const safeActionType = normalizeActionType(actionType);

  if (!safeProductId) {
    throw new Error('productId is required');
  }

  if (!safeActionType) {
    throw new Error('actionType is required');
  }

  const allowedActions = new Set(['view', 'like', 'add_to_cart', 'purchase']);
  if (!allowedActions.has(safeActionType)) {
    throw new Error(`Unsupported actionType: ${safeActionType}`);
  }

  let safeQuantity = normalizePositiveInteger(quantity, 1);

  if (safeActionType === 'view' || safeActionType === 'like') {
    safeQuantity = 1;
  }

  const res = await apiClient.post('/interact', {
    product_id: safeProductId,
    action_type: safeActionType,
    quantity: safeQuantity,
  });

  return res.data;
}