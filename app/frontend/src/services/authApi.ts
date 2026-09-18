import { api, getApiErrorMessage } from './api';
import { TokenResponse, User } from '../types/conversation';

export async function login(email: string, password: string): Promise<TokenResponse> {
  try {
    const response = await api.post<TokenResponse>('/auth/login', { email, password });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Invalid email or password.'));
  }
}

export async function getCurrentUser(): Promise<User> {
  try {
    const response = await api.get<User>('/auth/me');
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load current user.'));
  }
}

export function logout(): void {
  localStorage.removeItem('solwin_auth_token');
  localStorage.removeItem('solwin_auth_user');
}
