/**
 * API client configuration and utilities
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
  timeout: 60000, // 60 seconds timeout for file uploads
});

export interface UploadResponse {
  message: string;
  file_id: string;
  filename: string;
  saved_path: string;
  uploaded_at: string;
  text_extracted: boolean;
  text_length: number;
  supermemory_ingested?: boolean;
  memory_id?: string;
  supermemory_error?: string;
  supermemory_response?: any; // Full response from Supermemory for debugging
  topics_extracted?: boolean;
  topics?: string;
  topics_error?: string;
}

/**
 * Upload a file to the backend
 */
export async function uploadMaterial(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<UploadResponse>('/api/upload-material', formData);
  return response.data;
}

export const getLocalCourses = async () => {
    const response = await axios.get(`${API_BASE_URL}/courses`);
    return response.data; // Expects { courses: LocalCourse[], status: string }
};

export const getAvailableCanvasCourses = async () => {
    const response = await axios.get(`${API_BASE_URL}/canvas/available-courses`);
    return response.data; // Expects { available_courses: CanvasCourse[] }
};

export const addSelectedCanvasCourses = async (canvas_course_ids: string[]) => {
    const response = await axios.post(`${API_BASE_URL}/canvas/add-courses`, { 
        canvas_course_ids 
    });
    return response.data; // Expects { message: string }
};