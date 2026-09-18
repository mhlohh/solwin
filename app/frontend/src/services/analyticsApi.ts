import { api, getApiErrorMessage } from './api';
import {
  CustomerAnalytics,
  DashboardOverview,
  IssueFrequency,
  SecurityAnalytics,
  TrendResponse,
} from '../types/conversation';

export async function getDashboardOverview(): Promise<DashboardOverview> {
  try {
    const response = await api.get<DashboardOverview>('/dashboard/overview');
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load dashboard overview.'));
  }
}

export async function getCustomerAnalytics(): Promise<CustomerAnalytics> {
  try {
    const response = await api.get<CustomerAnalytics>('/analytics/customer');
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load customer analytics.'));
  }
}

export async function getSecurityAnalytics(): Promise<SecurityAnalytics> {
  try {
    const response = await api.get<SecurityAnalytics>('/analytics/security');
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load security analytics.'));
  }
}

export async function getTopIssues(limit = 10): Promise<IssueFrequency[]> {
  try {
    const response = await api.get<IssueFrequency[]>('/analytics/customer/top-issues', {
      params: { limit },
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load top issues.'));
  }
}

export async function getCustomerTrends(days = 30): Promise<TrendResponse> {
  try {
    const response = await api.get<TrendResponse>('/analytics/customer/trends', {
      params: { days },
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load customer trends.'));
  }
}

export async function getSecurityTrends(days = 30): Promise<TrendResponse> {
  try {
    const response = await api.get<TrendResponse>('/analytics/security/trends', {
      params: { days },
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load security trends.'));
  }
}
