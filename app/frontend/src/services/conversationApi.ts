import { api, getApiErrorMessage } from './api';
import {
  Conversation,
  ConversationCreate,
  ConversationDetail,
  ConversationFilterParams,
  PaginatedResponse,
} from '../types/conversation';

export async function getConversations(
  params?: ConversationFilterParams
): Promise<PaginatedResponse<Conversation>> {
  try {
    const response = await api.get<PaginatedResponse<Conversation>>('/conversations', {
      params,
    });
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load conversations.'));
  }
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  try {
    const response = await api.get<ConversationDetail>(`/conversations/${id}`);
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to load conversation details.'));
  }
}

export async function createConversation(
  data: ConversationCreate
): Promise<Conversation> {
  try {
    const response = await api.post<Conversation>('/conversations', data);
    return response.data;
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to create conversation.'));
  }
}

export async function appendMessage(
  conversationId: string,
  content: string,
  senderType: 'CUSTOMER' | 'AGENT' | 'SYSTEM' = 'AGENT',
  senderName?: string
): Promise<void> {
  try {
    await api.post(`/conversations/${conversationId}/messages`, {
      sender_type: senderType,
      sender_name: senderName,
      content,
    });
  } catch (err) {
    throw new Error(getApiErrorMessage(err, 'Failed to send message.'));
  }
}
