import type { Route } from "./+types/study-path";
import { Layout } from "../components/Layout"; // <-- FIX: Changed path from ../ to ./
import { useState, useEffect } from "react";
import { useLocation } from "react-router";
import { updateStudyPath } from "../utils/api"; // <-- FIX: Changed path from ../ to ./

export function meta({}: Route.MetaArgs) {
  return [
    { title: "AI Study Buddy - Study Path" },
    {
      name: "description",
      content: "Your personalized study path with topics and progress tracking",
    },
  ];
}

// Define the required data structure to match the parsed data from home.tsx
interface Subtopic {
  id: number;
  title: string;
  completed: boolean;
}

interface Topic {
  id: number;
  title: string;
  description: string;
  status: "completed" | "in-progress" | "pending";
  subtopics: Subtopic[];
}

// Fallback logic to get the data if state is empty (e.g., page refresh)
const loadTopicsFromSession = (): Topic[] => {
  // --- Guard against server-side rendering ---
  if (typeof window === 'undefined' || typeof sessionStorage === 'undefined') {
    return [
      {
        id: 0,
        title: "Loading...",
        description: "Awaiting client-side execution to check local storage or navigation data.",
        status: "pending",
        subtopics: [],
      }
    ];
  }
  
  try {
    const jsonString = sessionStorage.getItem('extractedTopicsJson');
    if (jsonString) {
      const topics: Topic[] = JSON.parse(jsonString);
      return topics;
    }
  } catch (error) {
    console.error("Error loading topics from session storage:", error);
  }
  // Fallback to a single placeholder topic if no data is found
  return [
    {
      id: 0,
      title: "No Topics Found",
      description: "Please go back to the Home page and upload a study material to generate a path.",
      status: "pending",
      subtopics: [],
    }
  ];
};


export default function StudyPath() {
  const location = useLocation();

  // 1. Get initial topics from navigation state or session storage
  const initialTopicsFromState = (location.state as any)?.topics;

  const initialTopics: Topic[] = initialTopicsFromState && Array.isArray(initialTopicsFromState) && initialTopicsFromState.length > 0
    ? initialTopicsFromState
    : loadTopicsFromSession();

  // Also retrieve the filename for display
  const filename = (location.state as any)?.filename || (
    typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('filename') : null
  ) || "Uploaded Material";
  
  // --- NEW: Get Module ID for persisting updates ---
  const initialModuleId = (location.state as { moduleId?: number })?.moduleId || 
    (typeof sessionStorage !== 'undefined' ? parseInt(sessionStorage.getItem('currentModuleId') || '0', 10) : 0);

  const [topics, setTopics] = useState(initialTopics);
  const [moduleId, setModuleId] = useState(initialModuleId); // <-- NEW STATE
  
  // Default to expanding the first active topic
  const [expandedTopic, setExpandedTopic] = useState<number | null>(
    topics && topics.length > 0 && topics[0] && topics[0].id !== 0 ? topics[0].id : null
  );

  // Get file ID from session storage
  const fileId = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('uploadedFileId') : null;

  const toggleTopic = (topicId: number) => {
    setExpandedTopic(expandedTopic === topicId ? null : topicId);
  };

  const toggleSubtopic = async (topicId: number, subtopicId: number) => { // <-- MAKE ASYNC
    const newTopics = topics.map((topic) => {
      if (topic.id === topicId) {
        // Toggle the completed status of the subtopic
        const newSubtopics = topic.subtopics.map((subtopic) =>
          subtopic.id === subtopicId
            ? { ...subtopic, completed: !subtopic.completed }
            : subtopic
        );
        
        // Update the main topic status based on subtopic completion
        const completedCount = newSubtopics.filter(st => st.completed).length;
        const totalCount = newSubtopics.length;
        let newStatus: Topic['status'];

        if (completedCount === totalCount) {
          newStatus = 'completed';
          // Find the next topic and set it to 'in-progress'
          const nextTopicIndex = topics.findIndex(t => t.id === topicId) + 1;
          if (nextTopicIndex < topics.length) {
            setTopics(prevTopics => prevTopics.map((t, index) => {
              if (index === nextTopicIndex && t.status === 'pending') {
                return { ...t, status: 'in-progress' };
              }
              return t;
            }));
          }
        } else if (completedCount > 0) {
          newStatus = 'in-progress';
        } else {
          newStatus = 'pending';
        }
        
        return {
          ...topic,
          subtopics: newSubtopics,
          status: newStatus
        };
      }
      return topic;
    });

    setTopics(newTopics);
    
    // Persist the updated topics to session storage
    const newTopicsJson = JSON.stringify(newTopics); // <-- Store JSON in a var
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem('extractedTopicsJson', newTopicsJson);
    }
    
    // --- NEW: Persist to backend ---
    if (moduleId && moduleId !== 0) {
      try {
        // Fire and forget, but log errors
        await updateStudyPath(moduleId, newTopicsJson);
      } catch (err) {
        console.error("Failed to sync progress to backend:", err);
        // Optionally show a small error toast to the user here
      }
    }
    // --- END NEW ---
  };


  const getProgress = () => {
    const totalSubtopic = topics.reduce(
      (acc, topic) => acc + topic.subtopics.length,
      0
    );
    const completedSubtopic = topics.reduce(
      (acc, topic) =>
        acc + topic.subtopics.filter((st) => st.completed).length,
      0
    );
    return totalSubtopic > 0
      ? Math.round((completedSubtopic / totalSubtopic) * 100)
      : 0;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500";
      case "in-progress":
        return "bg-blue-500";
      default:
        return "bg-gray-300 dark:bg-gray-600";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <svg
            className="w-5 h-5 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        );
      case "in-progress":
        return (
          <svg
            className="w-5 h-5 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
      default:
        return (
          <svg
            className="w-5 h-5 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
    }
  };

  return (
    <Layout>
      <div className="max-w-5xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Your Study Path
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-4">
            Path generated from: <span className="font-semibold text-blue-600 dark:text-blue-400">{filename}</span>
          </p>

          {/* Progress Overview */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Overall Progress
              </h2>
              <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {getProgress()}%
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-4">
              <div
                className="bg-gradient-to-r from-blue-500 to-indigo-600 h-4 rounded-full transition-all duration-500"
                style={{ width: `${getProgress()}%` }}
              />
            </div>
            <div className="mt-4 flex space-x-6 text-sm">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-gray-600 dark:text-gray-300">
                  Completed
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-gray-600 dark:text-gray-300">
                  In Progress
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-600" />
                <span className="text-gray-600 dark:text-gray-300">Pending</span>
              </div>
            </div>
          </div>
        </div>

        {/* Topics List */}
        {topics && topics.length > 0 ? (
          <div className="space-y-4">
            {topics.map((topic, index) => {
              if (!topic || topic.id === 0 || topic.title === "Loading..." || topic.title === "No Topics Found") return null;
              const completedSubtopic = topic.subtopics.filter(
                (st) => st.completed
              ).length;
              const totalSubtopic = topic.subtopics.length;
              const subtopicProgress =
                totalSubtopic > 0
                  ? Math.round((completedSubtopic / totalSubtopic) * 100)
                  : 0;

              // Check if the topic is currently active (in-progress or completed)
              const isTopicActive = topic.status !== 'pending';

              return (
                <div
                  key={topic.id}
                  className="bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-shadow overflow-hidden"
                >
                  <button
                    onClick={() => toggleTopic(topic.id)}
                    className="w-full p-6 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-xl"
                    // 🛑 FIX: REMOVED THE disabled PROP TO ALLOW EXPANSION 🛑
                    // disabled={topic.status === 'pending' && index !== 0} 
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 flex-1">
                        <div
                          className={`flex-shrink-0 w-10 h-10 rounded-full ${getStatusColor(
                            topic.status
                          )} flex items-center justify-center`}
                        >
                          {getStatusIcon(topic.status)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-1">
                            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
                              {String(index + 1).padStart(2, "0")}
                            </span>
                            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                              {topic.title}
                            </h3>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-300 mb-2">
                            {topic.description}
                          </p>
                          <div className="flex items-center space-x-4">
                            <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                              <div
                                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${subtopicProgress}%` }}
                              />
                            </div>
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              {completedSubtopic}/{totalSubtopic} subtopics
                            </span>
                          </div>
                        </div>
                      </div>
                      <svg
                        className={`w-6 h-6 text-gray-400 transform transition-transform ${
                          expandedTopic === topic.id ? "rotate-180" : ""
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>
                  </button>

                  {expandedTopic === topic.id && (
                    <div className="px-6 pb-6 border-t border-gray-200 dark:border-gray-700 pt-4">
                      <div className="space-y-2">
                        {topic.subtopics.map((subtopic) => (
                          <label
                            key={subtopic.id}
                            className="flex items-center space-x-3 p-3 rounded-lg cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50"
                          >
                            <input
                              type="checkbox"
                              checked={subtopic.completed}
                              onChange={() =>
                                toggleSubtopic(topic.id, subtopic.id)
                              }
                              className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                            />
                            <span
                              className={`flex-1 ${
                                subtopic.completed
                                  ? "line-through text-gray-400 dark:text-gray-500"
                                  : "text-gray-700 dark:text-gray-300"
                              }`}
                            >
                              {subtopic.title}
                            </span>
                            {!subtopic.completed && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  // Navigate to chat with this topic
                                }}
                                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium"
                              >
                                Study
                              </button>
                            )}
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center p-12 bg-white dark:bg-gray-800 rounded-xl shadow-lg">
             <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">
                {topics && topics[0] && topics[0].title === "Loading..." ? "Loading Study Path..." : "No Study Path Available."}
            </p>
            <p className="text-gray-500 dark:text-gray-400 mt-2">
                {topics && topics[0] && topics[0].description ? topics[0].description : "Please upload study materials to get started."}
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}