// frontend/app/components/UploadForm.tsx

import React, { useState } from "react";
import { useNavigate } from "react-router";
import { uploadMaterial } from "../utils/api";
import { parseClaudeTopics, type TopicData } from "../utils/TopicParser";

// The TopicData interface is now imported from the new utility file
// interface TopicData is defined in TopicParser.ts

export function UploadForm() {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const navigate = useNavigate();

  // --- Drag and Drop Handlers ---

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
        setUploadError(null); // Clear error on successful file selection
      } else {
        setUploadError("File type not supported. Please use PDF, TXT, or DOCX.");
        setSelectedFile(null);
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
        setUploadError(null); // Clear error on successful file selection
      } else {
        setUploadError("File type not supported. Please use PDF, TXT, or DOCX.");
        setSelectedFile(null);
      }
    }
  };

  // --- Core Upload and Navigation Logic ---
  
  const handleGeneratePath = async () => {
    if (!selectedFile) {
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      const response = await uploadMaterial(selectedFile);
      
      let structuredTopics: TopicData[] = [];

      if (response.topics_extracted && response.topics) {
        // Parse the raw topics string from the backend using the utility function
        structuredTopics = parseClaudeTopics(response.topics);
        
        // Store the structured topics in sessionStorage (good for refresh/direct navigation)
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
            topics: structuredTopics, 
          },
        });
      }, 1500);
    } catch (error: any) {
      console.error("Upload error:", error);
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
  
  // --- Render ---

  return (
    <div className="space-y-8">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">
            Upload Study Material
          </h2>

          {/* Upload Error Message */}
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

          {/* Upload Success Message */}
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

          {/* Drag and Drop Area */}
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

        {/* Generate Study Path Button */}
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
    </div>
  );
}