import apiClient from './apiClient';

export async function registerUser(payload) {
  const res = await apiClient.post('/register', payload);
  return res.data;
}

export async function loginUser(payload) {
  const res = await apiClient.post('/login', payload);
  return res.data;
}