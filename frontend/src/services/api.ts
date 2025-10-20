// frontend/src/services/api.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Orchestrator's address

interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
}

export const postChatMessage = async (history: ChatMessage[], newMessage: string): Promise<string> => {
  try {
    const payload = {
      history: history.map(msg => ({ ...msg, content: msg.content })), // Ensure correct structure
      new_message: newMessage,
    };
    const response = await axios.post(`${API_BASE_URL}/chat`, payload);
    return response.data.ai_message;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('API Error:', error.response?.data || error.message);
      return error.response?.data?.detail || 'An unknown API error occurred.';
    }
    console.error('Unexpected Error:', error);
    return 'An unexpected error occurred.';
  }
};
