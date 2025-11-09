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

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
  file_id?: string; // ID of uploaded material for context
}

export interface ChatResponse {
  success: boolean;
  response: string;
  message?: string;
}

export interface Topic {
  id: number;
  title: string;
  description: string;
  status: 'completed' | 'in-progress' | 'pending';
  subtopics: Array<{
    id: number;
    title: string;
    completed: boolean;
  }>;
}

export interface StudyProgressRequest {
  file_id: string;
  filename: string;
  topics: Topic[];
  overall_progress: number;
  last_updated: string;
  title?: string;
}

/**
 * Send a chat message to the AI Study Buddy backend
 * Optionally includes file_id for context-aware responses from uploaded materials
 */
export async function sendChatMessage(
  message: string,
  conversationHistory?: ChatMessage[],
  fileId?: string
): Promise<ChatResponse> {
  const request: ChatRequest = {
    message,
    conversation_history: conversationHistory,
    file_id: fileId,
  };

  const response = await apiClient.post<ChatResponse>('/chat', request);
  return response.data;
}

/**
 * Stream a chat message to the AI Study Buddy backend
 * Returns async generator that yields tokens as they are generated
 * Each chunk is a JSON object with either:
 * - {"metadata": {"context_used": bool, "web_search_used": bool}}
 * - {"text": "token"}
 * - {"done": true}
 */
export async function* streamChatMessage(
  message: string,
  conversationHistory?: ChatMessage[],
  fileId?: string
): AsyncGenerator<{metadata?: {context_used: boolean, web_search_used: boolean}, text?: string, done?: boolean, error?: string}, void, unknown> {
  const request: ChatRequest = {
    message,
    conversation_history: conversationHistory,
    file_id: fileId,
  };

  console.log('[streamChatMessage] Starting stream request');
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  console.log('[streamChatMessage] Response received:', response.status);

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let lineCount = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const lines = buffer.split('\n');
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim()) {
            lineCount++;
            try {
              const parsed = JSON.parse(line);
              console.log(`[streamChatMessage] Chunk ${lineCount}:`, parsed);
              yield parsed;
            } catch (e) {
              console.error('Failed to parse JSON chunk:', line, e);
            }
          }
        }
      }

      if (done) {
        console.log('[streamChatMessage] Stream done, processing remaining buffer');
        break;
      }
    }

    // Process any remaining buffer
    if (buffer.trim()) {
      try {
        const parsed = JSON.parse(buffer);
        console.log('[streamChatMessage] Final chunk:', parsed);
        yield parsed;
      } catch (e) {
        console.error('Failed to parse final JSON chunk:', buffer, e);
      }
    }

    console.log('[streamChatMessage] Stream complete');
  } finally {
    reader.releaseLock();
  }
}

/**
 * Save study progress to Supermemory for persistence across sessions
 */
export async function saveStudyProgress(progress: StudyProgressRequest): Promise<{ success: boolean; memory_id?: string; message: string }> {
  try {
    const response = await apiClient.post('/study-progress/save', progress);
    return response.data;
  } catch (error: any) {
    console.error('Failed to save study progress:', error);
    throw error;
  }
}

/**
 * Load study progress from Supermemory for a specific file
 */
export async function loadStudyProgress(fileId: string): Promise<{ success: boolean; progress_data: any; message: string }> {
  try {
    const response = await apiClient.get(`/study-progress/load/${fileId}`);
    return response.data;
  } catch (error: any) {
    console.error('Failed to load study progress:', error);
    return {
      success: false,
      progress_data: null,
      message: 'Failed to load study progress'
    };
  }
}

/**
 * List all previously uploaded materials
 */
export async function listUploadedMaterials(): Promise<{ success: boolean; materials: any[]; count: number }> {
  try {
    const response = await apiClient.get('/materials/list');
    return response.data;
  } catch (error: any) {
    console.error('Failed to list materials:', error);
    return {
      success: false,
      materials: [],
      count: 0
    };
  }
}

// Canvas integration functions
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

/**
 * Updates the persisted study path JSON for a module with new progress.
 */
export const updateStudyPath = async (localModuleId: number, topicsJson: string): Promise<{ message: string }> => {
    const response = await axios.put(`${API_BASE_URL}/llm/modules/${localModuleId}/update-study-path`, {
        topics_json: topicsJson
    });
    return response.data;
};