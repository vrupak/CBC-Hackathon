// frontend/app/utils/TopicParser.ts

// Define the expected structure for the frontend
export interface TopicData {
  id: number;
  title: string;
  description: string;
  subtopics: { id: number; title: string; completed?: boolean; }[];
  // Add frontend-specific fields
  status: 'completed' | 'in-progress' | 'pending';
}

/**
 * Parses the raw JSON string from the Claude service into a structured array
 * and initializes frontend-specific fields.
 */
export const parseClaudeTopics = (jsonString: string): TopicData[] => {
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