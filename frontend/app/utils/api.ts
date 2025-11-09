/**
 * API client configuration and utilities
 */
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    // Note: 'Content-Type' is set to 'multipart/form-data' only for file uploads,
    // we remove it here to let axios default to 'application/json' for other requests.
  },
  timeout: 60000, // 60 seconds timeout for file uploads
});

// --- Interface Definitions ---

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

export interface LocalModule {
  id: number;
  course_id: number;
  name: string;
  completed: boolean;
  canvas_file_id: string | null;
  file_url: string | null;
  is_downloaded: boolean;
  is_ingested: boolean;
  // --- NEW: Front-end status for path generation ---
  has_study_path?: boolean; 
}

export interface LocalCourse {
  courseName: string;
  local_course_id: number;
  canvas_id: string;
  progress: number;
  total_modules: number;
  module_count: number;
  last_upload_filename: string;
}

export interface CanvasCourse {
    canvas_id: string;
    name: string;
    course_code: string;
}


// --- API Functions ---

/**
 * Upload a file to the backend
 */
export async function uploadMaterial(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<UploadResponse>('/upload-material', formData);
  return response.data;
}

export const getLocalCourses = async (): Promise<{ courses: LocalCourse[], status: string }> => {
    // The endpoint is just /courses, not /api/courses if the axios base url is already /api
    const response = await axios.get(`${API_BASE_URL}/courses`);
    return response.data; // Expects { courses: LocalCourse[], status: string }
};

export const getAvailableCanvasCourses = async (): Promise<{ available_courses: CanvasCourse[] }> => {
    const response = await axios.get(`${API_BASE_URL}/canvas/available-courses`);
    return response.data; // Expects { available_courses: CanvasCourse[] }
};

export const addSelectedCanvasCourses = async (canvas_course_ids: string[]): Promise<{ message: string }> => {
    const response = await axios.post(`${API_BASE_URL}/canvas/add-courses`, { 
        canvas_course_ids 
    });
    return response.data; // Expects { message: string }
};

/**
 * Fetches modules (files) associated with a local course ID.
 */
export const getCourseModules = async (localCourseId: number): Promise<{ modules: LocalModule[], courseName: string, courseId: number, canvasId: string }> => {
  const response = await axios.get(`${API_BASE_URL}/courses/${localCourseId}/modules`);
  // Note: LocalModule now includes 'has_study_path' to simplify the logic on the frontend
  return response.data; 
};

/**
 * Syncs the local module list with the live files on Canvas for a specific course.
 */
export const syncCourseFiles = async (localCourseId: number): Promise<{ message: string, total_files_found: number }> => {
  const response = await axios.post(`${API_BASE_URL}/canvas/courses/${localCourseId}/sync-files`);
  return response.data;
};

/**
 * Downloads the file content for a specific module from Canvas.
 */
export const downloadModuleFile = async (localModuleId: number): Promise<{ message: string, local_path: string }> => {
  const response = await axios.post(`${API_BASE_URL}/canvas/modules/${localModuleId}/download`);
  return response.data;
};

/**
 * Ingests the downloaded file content for a specific module into Supermemory (RAG).
 */
export const ingestModuleFile = async (localModuleId: number): Promise<{ message: string, supermemory_response: any }> => {
  const response = await axios.post(`${API_BASE_URL}/canvas/modules/${localModuleId}/ingest`);
  return response.data;
};

/**
 * Triggers topic extraction for an ingested module file (Path Generation).
 */
export const generateTopics = async (localModuleId: number): Promise<{ topics: string, filename: string, source: string }> => {
    const response = await axios.post(`${API_BASE_URL}/llm/modules/${localModuleId}/generate-topics`);
    // 'topics' contains the raw Claude JSON string
    return response.data;
};

/**
 * Retrieves the persisted study path for a module (used after refresh).
 */
export const retrieveTopics = async (localModuleId: number): Promise<{ topics: string, filename: string, source: string }> => {
    // This endpoint should return the same structure as generateTopics but fetch from the DB
    const response = await axios.get(`${API_BASE_URL}/llm/modules/${localModuleId}/study-path`);
    return response.data;
};