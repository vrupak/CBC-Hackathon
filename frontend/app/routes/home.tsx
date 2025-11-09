import type { Route } from "./+types/home";
import { Layout } from "../components/Layout";
import { useState } from "react";
import { useNavigate } from "react-router";
import { uploadMaterial } from "../utils/api";

// Define the expected structure for the frontend
interface TopicData {
  id: number;
  title: string;
  description: string;
  subtopics: { id: number; title: string; }[];
  // Add frontend-specific fields
  status: 'completed' | 'in-progress' | 'pending';
}

/**
 * Parses the raw JSON string from the Claude service into a structured array
 * and initializes frontend-specific fields.
 */
const parseClaudeTopics = (jsonString: string): TopicData[] => {
  try {
    // 1. Clean the string: remove markdown code block fences and trim
    let cleanedString = jsonString.trim();
    if (cleanedString.startsWith('```json')) {
      cleanedString = cleanedString.substring(7);
    }
    if (cleanedString.endsWith('```')) {
      cleanedString = cleanedString.substring(0, cleanedString.length - 3);
    }
    cleanedString = cleanedString.trim();

    // 2. Parse the JSON string into an array
    const topics: TopicData[] = JSON.parse(cleanedString);

    // 3. Initialize frontend-specific fields: status and subtopic completion
    return topics.map((topic, index) => ({
      ...topic,
      // The very first topic starts as 'in-progress', rest are 'pending'
      status: index === 0 ? 'in-progress' : 'pending',
      // Add 'completed' flag to subtopics for tracking
      subtopics: topic.subtopics.map(subtopic => ({
        ...subtopic,
        completed: false, // Start all subtopics as incomplete
      })),
    }));

  } catch (error) {
    console.error("Failed to parse Claude JSON response:", error);
    // Return an empty array on failure
    return [];
  }
};


export function meta({}: Route.MetaArgs) {
  return [
    { title: "AI Study Buddy - Upload Study Material" },
    {
      name: "description",
      content: "Upload your study materials to get started with AI-powered learning",
    },
  ];
}

export default function Home() {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const navigate = useNavigate();

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      const file = files[0];
      // Updated file type validation to include DOCX from backend
      if (file.type === "application/pdf" || file.type === "text/plain" || file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
        setSelectedFile(file);
      } else {
        setUploadError("File type not supported. Please use PDF, TXT, or DOCX.");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      // Updated file type validation to include DOCX from backend
      if (file.type === "application/pdf" || file.type === "text/plain" || file.type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document") {
        setSelectedFile(file);
      } else {
        setUploadError("File type not supported. Please use PDF, TXT, or DOCX.");
      }
    }
  };

  const handleGeneratePath = async () => {
    if (!selectedFile) {
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const response = await uploadMaterial(selectedFile);
      
      // Log full response for debugging
      console.log("Upload response:", response);
      
      let structuredTopics: TopicData[] = [];

      // 1. Check if topics were extracted and the response body exists
      if (response.topics_extracted && response.topics) {
        // 2. Parse the raw topics string from the backend
        structuredTopics = parseClaudeTopics(response.topics);
        
        // 3. Store the structured topics in sessionStorage (good for refresh/direct navigation)
        // --- FIX: Check for client environment before writing to sessionStorage ---
        if (typeof sessionStorage !== 'undefined') {
          sessionStorage.setItem('uploadedFileId', response.file_id);
          sessionStorage.setItem('extractedTopicsJson', JSON.stringify(structuredTopics));
          sessionStorage.setItem('filename', response.filename);
        }
      } else {
        // Handle case where topics extraction failed
        setUploadError(response.topics_error || "File uploaded, but topic extraction failed.");
        setIsUploading(false);
        return; // Stop here if we can't get topics
      }

      setUploadSuccess(true);
      
      // Navigate to study path after a brief delay to show success message
      setTimeout(() => {
        navigate("/study-path", {
          state: {
            fileId: response.file_id,
            filename: response.filename,
            // Pass the structured array directly via state
            topics: structuredTopics, 
          },
        });
      }, 1500);
    } catch (error: any) {
      console.error("Upload error:", error);
      console.error("Error response:", error.response?.data);
      const errorMessage = error.response?.data?.detail || error.message || "Failed to upload file. Please try again.";
      setUploadError(errorMessage);
      setIsUploading(false);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setUploadError(null);
    setUploadSuccess(false);
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Welcome to AI Study Buddy
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Upload your study materials and let AI help you create a personalized
            study path, understand complex concepts, and ace your exams.
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
            Upload Study Material
          </h2>

          {uploadError && (
            <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-center">
                <svg
                  className="w-5 h-5 text-red-600 dark:text-red-400 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-sm text-red-800 dark:text-red-200">{uploadError}</p>
              </div>
            </div>
          )}

          {uploadSuccess && (
            <div className="mb-6 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-center">
                <svg
                  className="w-5 h-5 text-green-600 dark:text-green-400 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-sm text-green-800 dark:text-green-200">
                  File uploaded successfully! Processing topics...
                </p>
              </div>
            </div>
          )}

          <div
            onDragEnter={handleDragEnter}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ${
              isDragging
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500"
            }`}
          >
            {selectedFile ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <div className="bg-green-100 dark:bg-green-900/30 rounded-full p-4">
                    <svg
                      className="w-12 h-12 text-green-600 dark:text-green-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                </div>
                <div>
                  <p className="text-lg font-medium text-gray-900 dark:text-white">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <button
                  onClick={handleRemoveFile}
                  className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
                >
                  Remove file
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-center">
                  <div className="bg-blue-100 dark:bg-blue-900/30 rounded-full p-4">
                    <svg
                      className="w-16 h-16 text-blue-600 dark:text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                  </div>
                </div>
                <div>
                  <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                    Drag and drop your file here
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    or click to browse
                  </p>
                  <label className="inline-block">
                    <input
                      type="file"
                      accept=".pdf,.txt,.docx"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                    <span className="inline-flex items-center px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors cursor-pointer">
                      Select File
                    </span>
                  </label>
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-4">
                  Supported formats: PDF, TXT, DOCX
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="flex justify-center">
          <button
            onClick={handleGeneratePath}
            disabled={!selectedFile || isUploading}
            className={`px-8 py-4 rounded-lg font-semibold text-lg transition-all duration-200 flex items-center ${
              selectedFile && !isUploading
                ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5"
                : "bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed"
            }`}
          >
            {isUploading ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Uploading and Processing...
              </>
            ) : (
              "Generate Study Path"
            )}
          </button>
        </div>

        <div className="mt-12 grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon={
              <svg
                className="w-8 h-8"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            }
            title="Extract Topics"
            description="AI automatically extracts key topics and subtopics from your materials"
          />
          <FeatureCard
            icon={
              <svg
                className="w-8 h-8"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
            }
            title="Study Path"
            description="Get a personalized study path optimized for your learning style"
          />
          <FeatureCard
            icon={
              <svg
                className="w-8 h-8"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            }
            title="AI Tutor"
            description="Ask questions and get detailed explanations tailored to your level"
          />
        </div>
      </div>
    </Layout>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow">
      <div className="text-blue-600 dark:text-blue-400 mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-300">{description}</p>
    </div>
  );
}