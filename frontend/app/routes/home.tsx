// frontend/app/routes/home.tsx

import type { Route } from "./+types/home";
import { Layout } from "../components/Layout";
// Removed useState, useNavigate, uploadMaterial, parseClaudeTopics, TopicData
// New Imports:
import { CourseCards } from '../components/CourseCards';
import { UploadForm } from '../components/UploadForm';
import { FeatureCard, ExtractTopicsIcon, StudyPathIcon, AiTutorIcon } from '../components/FeatureCard';


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
  // Removed all state and handler functions (drag/drop, upload logic)

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        {/* --- Header --- */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Welcome to AI Study Buddy
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Upload your study materials and let AI help you create a personalized
            study path, understand complex concepts, and ace your exams.
          </p>
        </div>

        {/* --- Course Cards Section (NEW) --- */}
        <CourseCards /> 

        <hr className="my-12 border-gray-200 dark:border-gray-700" /> {/* Added separator */}

        {/* --- Upload Form (NEW COMPONENT) --- */}
        {/* <UploadForm /> */}
        
        {/* Removed button logic which is now inside UploadForm */}

        {/* --- Feature Cards (NEW COMPONENT) --- */}
        <div className="mt-12 grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon={<ExtractTopicsIcon />}
            title="Extract Topics"
            description="AI automatically extracts key topics and subtopics from your materials"
          />
          <FeatureCard
            icon={<StudyPathIcon />}
            title="Study Path"
            description="Get a personalized study path optimized for your learning style"
          />
          <FeatureCard
            icon={<AiTutorIcon />}
            title="AI Tutor"
            description="Ask questions and get detailed explanations tailored to your level"
          />
        </div>
      </div>
    </Layout>
  );
}
