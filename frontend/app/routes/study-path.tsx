import type { Route } from "./+types/study-path";
import { Layout } from "../components/Layout";
import { useState } from "react";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "AI Study Buddy - Study Path" },
    {
      name: "description",
      content: "Your personalized study path with topics and progress tracking",
    },
  ];
}

// Mock data for demonstration
const mockTopics = [
  {
    id: 1,
    title: "Introduction to Machine Learning",
    description: "Basic concepts and terminology",
    status: "completed" as const,
    subtopics: [
      { id: 1, title: "What is Machine Learning?", completed: true },
      { id: 2, title: "Types of Learning", completed: true },
      { id: 3, title: "Applications", completed: true },
    ],
  },
  {
    id: 2,
    title: "Supervised Learning",
    description: "Learning with labeled data",
    status: "in-progress" as const,
    subtopics: [
      { id: 1, title: "Regression", completed: true },
      { id: 2, title: "Classification", completed: true },
      { id: 3, title: "Decision Trees", completed: false },
      { id: 4, title: "Random Forests", completed: false },
    ],
  },
  {
    id: 3,
    title: "Unsupervised Learning",
    description: "Finding patterns in unlabeled data",
    status: "pending" as const,
    subtopics: [
      { id: 1, title: "Clustering", completed: false },
      { id: 2, title: "Dimensionality Reduction", completed: false },
      { id: 3, title: "PCA", completed: false },
    ],
  },
  {
    id: 4,
    title: "Neural Networks",
    description: "Deep learning fundamentals",
    status: "pending" as const,
    subtopics: [
      { id: 1, title: "Perceptrons", completed: false },
      { id: 2, title: "Backpropagation", completed: false },
      { id: 3, title: "CNN", completed: false },
      { id: 4, title: "RNN", completed: false },
    ],
  },
  {
    id: 5,
    title: "Model Evaluation",
    description: "Testing and validating your models",
    status: "pending" as const,
    subtopics: [
      { id: 1, title: "Cross-validation", completed: false },
      { id: 2, title: "Metrics", completed: false },
      { id: 3, title: "Overfitting", completed: false },
    ],
  },
];

export default function StudyPath() {
  const [topics, setTopics] = useState(mockTopics);
  const [expandedTopic, setExpandedTopic] = useState<number | null>(1);

  const toggleTopic = (topicId: number) => {
    setExpandedTopic(expandedTopic === topicId ? null : topicId);
  };

  const toggleSubtopic = (topicId: number, subtopicId: number) => {
    setTopics(
      topics.map((topic) => {
        if (topic.id === topicId) {
          return {
            ...topic,
            subtopics: topic.subtopics.map((subtopic) =>
              subtopic.id === subtopicId
                ? { ...subtopic, completed: !subtopic.completed }
                : subtopic
            ),
          };
        }
        return topic;
      })
    );
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
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Your Study Path
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-6">
            Follow this recommended path to master your study material
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
        <div className="space-y-4">
          {topics.map((topic, index) => {
            const completedSubtopic = topic.subtopics.filter(
              (st) => st.completed
            ).length;
            const totalSubtopic = topic.subtopics.length;
            const subtopicProgress =
              totalSubtopic > 0
                ? Math.round((completedSubtopic / totalSubtopic) * 100)
                : 0;

            return (
              <div
                key={topic.id}
                className="bg-white dark:bg-gray-800 rounded-xl shadow-md hover:shadow-lg transition-shadow overflow-hidden"
              >
                <button
                  onClick={() => toggleTopic(topic.id)}
                  className="w-full p-6 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-xl"
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
                          className="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
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
      </div>
    </Layout>
  );
}

