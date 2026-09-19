import axios from 'axios';
import { getApiErrorMessage } from './api';

export const DATA_API_BASE_URL =
  import.meta.env.VITE_DATA_API_BASE_URL || 'http://localhost:8002';

const dataApi = axios.create({
  baseURL: DATA_API_BASE_URL,
  timeout: 15000,
});

/** One raw customer-feedback record (ticket) from the ingested dataset. */
export interface InboxTicket {
  id: number;
  message: string;
  domain: string;
  channel: string;
  subject: string;
  intent: string;
  issue: string;
  technique: string | null;
  phishing: boolean | null;
  sender: string;
  label: string;
  priority: string;
  created_at: string;
}

export interface InboxPage {
  total: number;
  skip: number;
  limit: number;
  items: InboxTicket[];
}

export interface PhishingTechniqueFrequency {
  technique: string;
  count: number;
}

export interface DatasetStats {
  total_records: number;
  phishing_flagged: number;
  priority_counts: Record<string, number>;
  top_intents: { issue: string; count: number }[];
  phishing_techniques: PhishingTechniqueFrequency[];
}

export interface InboxFacets {
  total: number;
  phishing: number;
  intents: string[];
  priority_counts: Record<string, number>;
}

export interface InboxQuery {
  skip?: number;
  limit?: number;
  intent?: string;
  phishing?: boolean;
  priority?: string;
  search?: string;
}

export async function listTickets(params: InboxQuery = {}): Promise<InboxPage> {
  const { data } = await dataApi.get<InboxPage>('/tickets', { params });
  return data;
}

export async function getTicket(id: number): Promise<InboxTicket> {
  const { data } = await dataApi.get<InboxTicket>(`/tickets/${id}`);
  return data;
}

export async function getFacets(): Promise<InboxFacets> {
  const { data } = await dataApi.get<InboxFacets>('/tickets/facets');
  return data;
}

export async function getDatasetStats(): Promise<DatasetStats> {
  const { data } = await dataApi.get<DatasetStats>('/tickets/stats');
  return data;
}

export interface DatasetPhishingQuery {
  skip?: number;
  limit?: number;
  search?: string;
}

export async function listPhishingTickets(
  params: DatasetPhishingQuery = {}
): Promise<InboxPage> {
  const { data } = await dataApi.get<InboxPage>('/tickets', {
    params: { phishing: true, ...params },
  });
  return data;
}

export { getApiErrorMessage };
