import apiClient from './apiClient';

function normalizeBoolean(value) {
  return Boolean(value);
}

function normalizeProductId(productId) {
  const safeProductId = String(productId || '').trim();

  if (!safeProductId) {
    throw new Error('productId is required');
  }

  return safeProductId;
}

export async function fetchItemRecommendationsApi(productId, randomize = false) {
  const safeProductId = normalizeProductId(productId);

  const res = await apiClient.get(`/recommendations/${safeProductId}`, {
    params: {
      randomize: normalizeBoolean(randomize),
    },
  });

  return Array.isArray(res.data) ? res.data : [];
}

export async function fetchPersonalizedItemRecommendationsApi(productId, randomize = false) {
  const safeProductId = normalizeProductId(productId);

  const res = await apiClient.get(`/recommendations/personalized/${safeProductId}`, {
    params: {
      randomize: normalizeBoolean(randomize),
    },
  });

  return Array.isArray(res.data) ? res.data : [];
}