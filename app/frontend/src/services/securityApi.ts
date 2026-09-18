import { api, getApiErrorMessage } from './api';
import {
  PaginatedResponse,
  SecurityIntelligence,
  Threat,
  ThreatFilterParams,
} from '../types/conversation';

/** Paginated directory of persisted threat records. */
export async function getThreats(
  params?: ThreatFilterParams
): Promise<PaginatedResponse<Threat>> {
  try {
    const response = await api.get<PaginatedResponse<Threat>>('/security/threats', {
      params,
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load threats.'));
  }
}

/** Fetch a single persisted threat record by id. */
export async function getThreat(id: string): Promise<Threat> {
  try {
    const response = await api.get<Threat>(`/security/threats/${id}`);
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load threat details.'));
  }
}

/** Fetch latest persisted security analysis for a conversation. */
export async function getSecurityIntelligenceForConversation(
  conversationId: string
): Promise<SecurityIntelligence> {
  try {
    const response = await api.get<{ threat: Threat } | Threat>(
      `/security/conversation/${conversationId}`
    );
    const data = response.data as any;
    const threat: Threat | undefined = data.threat || data;
    if (!threat) {
      return emptyIntelligence();
    }
    return {
      threat_detected: Boolean(threat.threat_detected),
      threat_type: threat.threat_type || 'NONE',
      suspicious_urls: threat.suspicious_urls || [],
      suspicious_emails: threat.suspicious_emails || [],
      social_engineering_detected: Boolean(threat.social_engineering_detected),
      techniques: threat.techniques || [],
      risk_level: threat.risk_level || 'LOW',
      risk_reasons: threat.risk_reasons || [],
    };
  } catch (err) {
    // A 404 here simply means no analysis has been persisted yet.
    if (
      err &&
      typeof err === 'object' &&
      'response' in err &&
      (err as any).response?.status === 404
    ) {
      return emptyIntelligence();
    }
    throw new Error(getApiErrorMessage(err, 'Failed to load security intelligence.'));
  }
}

function emptyIntelligence(): SecurityIntelligence {
  return {
    threat_detected: false,
    threat_type: 'NONE',
    suspicious_urls: [],
    suspicious_emails: [],
    social_engineering_detected: false,
    techniques: [],
    risk_level: 'LOW',
    risk_reasons: [],
  };
}
