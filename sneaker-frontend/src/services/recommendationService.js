import apiClient from './apiClient';

export async function fetchItemRecommendationsApi(productId, randomize = false) {
  const res = await apiClient.get(`/recommendations/${productId}`, {
    params: { randomize },
  });
  return res.data;
}

export async function fetchPersonalizedItemRecommendationsApi(productId, randomize = false) {
  const res = await apiClient.get(`/recommendations/personalized/${productId}`, {
    params: { randomize },
  });
  return res.data;
}