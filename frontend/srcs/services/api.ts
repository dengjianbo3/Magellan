const USER_SERVICE_URL = 'http://localhost:8008';

export interface UserPersona {
  user_id: string;
  investment_style?: string;
  report_preference?: string;
  risk_tolerance?: string;
}

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
