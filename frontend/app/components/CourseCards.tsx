// src/components/CourseCards.tsx

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
// NOTE: These functions need to be implemented in '../utils/api'
import { getLocalCourses, getAvailableCanvasCourses, addSelectedCanvasCourses } from '../utils/api'; 

// --- Type Definitions (Added LinkCourse to handle local_course_id from URL) ---

export interface LocalCourse { // Exported for use in other components if needed
  courseName: string;
  local_course_id: number;
  canvas_id: string;
  progress: number;
  total_modules: number;
  module_count: number;
  last_upload_filename: string;
}

interface CanvasCourse {
    canvas_id: string;
    name: string;
    course_code: string;
}

// --- Component: CourseList ---

export function CourseCards() {
  const [courses, setCourses] = useState<LocalCourse[]>([]);
  const [availableCourses, setAvailableCourses] = useState<CanvasCourse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [selectedCanvasIds, setSelectedCanvasIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // State for fetching the initial list of available courses
  const [isFetchingAvailable, setIsFetchingAvailable] = useState(false);
  
  // Ref for the modal content area
  const modalRef = useRef<HTMLDivElement>(null); 

  // Use useNavigate for navigation
  const navigate = useNavigate();

  // 1. Fetch Local Courses
  const fetchLocalCourses = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await getLocalCourses();
      setCourses(response.courses || []);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch local courses:", err);
      setError(err.message || "Failed to load local courses.");
      setCourses([]);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  // 2. Fetch Available Canvas Courses (for Modal)
  const fetchAvailableCanvasCourses = useCallback(async () => {
      setError(null);
      setIsFetchingAvailable(true); // START fetching
      try {
        const response = await getAvailableCanvasCourses();
        setAvailableCourses(response.available_courses || []);
        setIsModalOpen(true);
      } catch (err: any) {
        console.error("Failed to fetch available courses:", err);
        const errorMessage = err.response?.data?.detail || "Could not connect to Canvas API. Check token.";
        setError(errorMessage);
      } finally {
        setIsFetchingAvailable(false); // END fetching
      }
  }, []);


  useEffect(() => {
    fetchLocalCourses();
  }, [fetchLocalCourses]);

  // --- MODAL: Click Outside Handler ---
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // Check if the click occurred outside the modal content
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        setIsModalOpen(false);
        setSelectedCanvasIds([]); // Clear selections on close
        setError(null);
      }
    };

    if (isModalOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isModalOpen]);


  // --- Event Handlers ---
  
  const handleToggleSelect = (canvasId: string) => {
    setSelectedCanvasIds(prev => 
      prev.includes(canvasId) 
        ? prev.filter(id => id !== canvasId) 
        : [...prev, canvasId]
    );
  };

  const handleAddCourses = async () => {
    if (selectedCanvasIds.length === 0) return;
    setIsAdding(true);
    setError(null);
    try {
      await addSelectedCanvasCourses(selectedCanvasIds); 
      
      // Close modal and refresh local course list
      setIsModalOpen(false);
      setSelectedCanvasIds([]);
      await fetchLocalCourses();
    } catch (err: any) {
      console.error("Failed to add courses:", err);
      const errorMessage = err.response?.data?.detail || "Failed to add courses to local database.";
      setError(errorMessage);
    } finally {
      setIsAdding(false);
    }
  };


  // --- Render Functions ---

  // MODIFIED: Added onClick handler to navigate
  const renderCourseCard = (course: LocalCourse) => (
    <div 
      key={course.local_course_id}
      onClick={() => navigate(`/course/${course.local_course_id}`)} // NEW: Navigate on click
      className="bg-white dark:bg-gray-800 rounded-xl p-6 transition-shadow cursor-pointer 
                 shadow-lg hover:shadow-xl dark:shadow-gray-950/50 
                 border border-gray-100 dark:border-gray-700/50 
                 h-full" // Ensure card takes full height in the grid cell
    >
      {/* CARD CONTENT WRAPPER: Use flex-col and justify-between to push the footer down */}
      <div className="flex flex-col h-full">
        
        {/* TOP SECTION: Title and Canvas ID */}
        <div className="mb-4 flex-grow">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
            {course.courseName}
          </h3>
          <span className="text-xs font-medium text-blue-600 dark:text-blue-400 opacity-80">
            Canvas ID: {course.canvas_id || 'N/A'}
          </span>
        </div>
        
        {/* BOTTOM SECTION: Module Counts and Progress Bar (Pushed to bottom) */}
        <div className="mt-auto"> {/* mt-auto ensures this section is always at the bottom */}
            {/* Module Counts: Simplified and grouped */}
            <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-3 border-t border-b border-gray-100 dark:border-gray-700 py-2">
              <p>Total Modules: <span className="font-semibold">{course.total_modules}</span></p>
              <p>Stored: <span className="font-semibold">{course.module_count}</span></p>
            </div>
      
            {/* Progress Bar */}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 relative">
              <div
                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-3 rounded-full transition-all duration-500"
                style={{ width: `${course.progress}%` }}
              ></div>
              {/* Display % completion *inside* the progress bar */}
              {course.progress > 5 && ( 
                  <span className="absolute top-0 right-2 text-xs font-bold text-white leading-loose">
                     {course.progress}%
                  </span>
              )}
            </div>
        </div>
      </div>
    </div>
  );
  
  const renderAvailableCourseItem = (course: CanvasCourse) => {
    const isSelected = selectedCanvasIds.includes(course.canvas_id);
    return (
        <div 
            key={course.canvas_id} 
            className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors border ${
                isSelected 
                    ? 'bg-blue-50 border-blue-500 dark:bg-blue-900/20' 
                    : 'bg-white border-gray-200 dark:bg-gray-800 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
            onClick={() => handleToggleSelect(course.canvas_id)}
        >
            <div className="flex-1">
                <p className="font-semibold text-gray-900 dark:text-white">{course.name}</p>
                <p className="text-sm text-gray-500 dark:text-gray-400">{course.course_code}</p>
            </div>
            <input
                type="checkbox"
                checked={isSelected}
                readOnly
                className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            />
        </div>
    );
  };


  if (isLoading) {
    return (
      <div className="text-center p-12 text-gray-600 dark:text-gray-400">
        <svg className="animate-spin h-8 w-8 text-blue-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
        <p className="mt-4">Loading your local courses...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
        
      {error && (
        <div className="p-4 bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-800 text-red-800 dark:text-red-300 rounded-lg">
          <p className="font-semibold">Error:</p>
          <p>{error}</p>
        </div>
      )}

      {/* Header and Add Course Button */}
      <div className="flex justify-between items-center">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          Your Courses
        </h2>
        <button
          onClick={fetchAvailableCanvasCourses} 
          disabled={isFetchingAvailable} // Disabled while fetching
          className={`px-4 py-2 rounded-lg font-medium transition-colors shadow-md flex items-center justify-center ${
            isFetchingAvailable 
                ? "bg-green-400 text-white cursor-not-allowed" 
                : "bg-green-600 text-white hover:bg-green-700"
            }`}
        >
          {isFetchingAvailable ? (
              <>
                  <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Loading Courses...
              </>
          ) : (
              '+ Add Courses from Canvas'
          )}
        </button>
      </div>

      {/* Course List */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {courses.length > 0 ? (
          courses.map(renderCourseCard)
        ) : (
          <div className="col-span-full text-center p-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg">
            <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">
              No Courses Found
            </p>
            <p className="text-gray-500 dark:text-gray-400 mt-2">
              Click "+ Add Courses from Canvas" to get started!
            </p>
          </div>
        )}
      </div>

      {/* --- Add Course Modal --- */}
      {isModalOpen && (
        <div 
          // Updated Backdrop
          className="fixed inset-0 bg-gray-900/70 dark:bg-black/80 flex items-center justify-center z-50 p-4"
        >
          <div 
            // Increased max-width and set max-h to 70vh
            ref={modalRef} 
            className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-xl max-h-[70vh] overflow-y-auto"
          >
            <div className="p-6">
              <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Add Canvas Courses
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Select the courses you want to add to your AI Study Buddy.
              </p>
              
              {/* List of Available Courses: Increased vertical space to 50vh */}
              <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-2">
                  {availableCourses.length > 0 ? (
                      availableCourses.map(renderAvailableCourseItem)
                  ) : (
                      <p className="text-center text-gray-500 dark:text-gray-400 py-4">
                          All active Canvas courses are already added locally.
                      </p>
                  )}
              </div>
            </div>
            
            {/* Modal Footer */}
            <div className="flex justify-end space-x-3 p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => { setIsModalOpen(false); setSelectedCanvasIds([]); setError(null); }}
                className="px-4 py-2 text-gray-600 dark:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCourses}
                disabled={selectedCanvasIds.length === 0 || isAdding}
                className={`px-4 py-2 rounded-lg font-semibold transition-colors flex items-center ${
                  selectedCanvasIds.length > 0 && !isAdding
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-300 text-gray-500 cursor-not-allowed"
                }`}
              >
                {isAdding ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    Adding...
                  </>
                ) : (
                  `Add ${selectedCanvasIds.length} Course(s)`
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}