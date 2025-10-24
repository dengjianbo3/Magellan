// frontend/src/services/api.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';
const USER_SERVICE_URL = 'http://localhost:8008';
const KNOWLEDGE_SERVICE_URL = 'http://localhost:8009';

export interface CompanyOption {
  ticker: string;
  name: string;
  exchange: string;
}

export interface AnalysisStep {
  id: number;
  title: string;
  status: 'pending' | 'running' | 'success' | 'error' | 'paused';
  result?: string | null;
  options?: CompanyOption[];
  progress?: number | null;
  sub_steps?: string[] | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ReportSection {
  section_title: string;
  content: string;
}

export interface FinancialChartData {
  years: number[];
  revenues: number[];
  profits: number[];
}

export interface FullReport {
  company_ticker: string;
  report_sections: ReportSection[];
  financial_chart_data?: FinancialChartData;
}

export interface AnalysisSession {
  session_id: string;
  status: 'in_progress' | 'hitl_required' | 'completed' | 'error' | 'hitl_follow_up_required';
  steps: AnalysisStep[];
  preliminary_report?: FullReport;
  key_questions?: string[];
}

export interface UserPersona {
  user_id: string;
  investment_style?: string;
  report_preference?: string;
  risk_tolerance?: string;
}


const handleError = (error: any): string => {
  if (axios.isAxiosError(error)) {
    console.error('API Error:', error.response?.data || error.message);
    return error.response?.data?.detail || 'An unknown API error occurred.';
  }
  console.error('Unexpected Error:', error);
  return 'An unexpected error occurred.';
};

// V3 WebSocket endpoint for DD workflow
const API_WS_URL = 'ws://localhost:8000/ws/start_dd_analysis';

export interface WebSocketMessage {
  session_id: string;
  status: 'in_progress' | 'hitl_required' | 'error' | 'hitl_follow_up_required';
  step?: AnalysisStep;
  preliminary_report?: FullReport;
  key_questions?: string[];
}

// --- Deprecated ---
export const startAnalysis = async (ticker: string): Promise<AnalysisSession> => {
  console.warn("DEPRECATED: startAnalysis is deprecated. Use WebSocket connection instead.");
  // ... (implementation remains for compatibility)
  try {
    const payload = { ticker };
    const response = await axios.post<AnalysisSession>(`${API_BASE_URL}/start_analysis`, payload);
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

export const continueAnalysis = async (sessionId: string, selectedTicker: string): Promise<AnalysisSession> => {
  console.warn("DEPRECATED: continueAnalysis is deprecated. Use WebSocket connection instead.");
  // ... (implementation remains for compatibility)
  try {
    const payload = { session_id: sessionId, selected_ticker: selectedTicker };
    const response = await axios.post<AnalysisSession>(`${API_BASE_URL}/continue_analysis`, payload);
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

export { API_WS_URL };

export const generateDeepReport = async (ticker: string, files: File[]): Promise<FullReport> => {
  try {
    const formData = new FormData();
    formData.append('ticker', ticker);
    files.forEach(file => {
      formData.append('files', file);
    });

    const response = await axios.post<FullReport>(`${API_BASE_URL}/generate_full_report`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

export const getInstantFeedback = async (analysisContext: string, userInput: string): Promise<string> => {
  try {
    const payload = { analysis_context: analysisContext, user_input: userInput };
    const response = await axios.post<{ feedback: string }>(`${API_BASE_URL}/get_instant_feedback`, payload);
    return response.data.feedback;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

export const getUserPersona = async (userId: string): Promise<UserPersona> => {
  try {
    const response = await axios.get<UserPersona>(`${USER_SERVICE_URL}/users/${userId}`);
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

export const updateUserPersona = async (userId: string, persona: UserPersona): Promise<UserPersona> => {
  try {
    const response = await axios.post<UserPersona>(`${USER_SERVICE_URL}/users/${userId}`, persona);
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

// --- Internal Knowledge Service ---
export interface InsightResult {
  content: string;
  metadata: {
    source?: string;
    project?: string;
    date?: string;
    [key: string]: any;
  };
}

export interface InsightsResponse {
  results: InsightResult[];
}

export const searchInternalInsights = async (query: string, limit: number = 3): Promise<InsightsResponse> => {
  try {
    const payload = { query, limit };
    const response = await axios.post<InsightsResponse>(`${KNOWLEDGE_SERVICE_URL}/search`, payload);
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};

// --- Valuation Analysis (Sprint 7) ---
export interface ValuationAnalysisResponse {
  session_id: string;
  valuation_analysis: {
    valuation_range: {
      low: number;
      high: number;
      currency: string;
    };
    methodology: string;
    comparable_companies: Array<{
      name: string;
      pe_ratio?: number;
      ps_ratio?: number;
      market_cap?: string;
      growth_rate?: string;
    }>;
    key_assumptions: string[];
    risks: string[];
    analysis_text: string;
  };
  exit_analysis: {
    primary_path: string;
    ipo_analysis: {
      feasibility: string;
      estimated_timeline: string;
      requirements: string[];
      target_board?: string;
    };
    ma_opportunities: string[];
    exit_risks: string[];
    analysis_text: string;
  };
  im_section: string;
}

export const generateValuationAnalysis = async (sessionId: string): Promise<ValuationAnalysisResponse> => {
  try {
    const response = await axios.post<ValuationAnalysisResponse>(
      `${API_BASE_URL}/api/v1/dd/${sessionId}/valuation`
    );
    return response.data;
  } catch (error) {
    throw new Error(handleError(error));
  }
};
