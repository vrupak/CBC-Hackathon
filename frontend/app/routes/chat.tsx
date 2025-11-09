import type { Route } from "./+types/chat";
import { Layout } from "../components/Layout";
import { useState, useRef, useEffect } from "react";
import { flushSync } from "react-dom";
import { streamChatMessage, type ChatMessage as APIChatMessage } from "../utils/api";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "AI Study Buddy - Chat" },
    {
      name: "description",
      content: "Chat with AI tutor to get help with your studies",
    },
  ];
}

interface Message {
  id: number;
  text: string;
  sender: "user" | "ai";
  timestamp: Date;
  usedWebSearch?: boolean;
  sources?: string[];
}

// Mock data for quick topic selection
const quickTopics = [
  "Explain machine learning",
  "What is supervised learning?",
  "Help me understand neural networks",
  "What's the difference between classification and regression?",
];

// Helper function to parse text and make URLs clickable
function linkifyText(text: string): React.ReactNode {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);

  return parts.map((part, index) => {
    if (part.match(urlRegex)) {
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 hover:text-blue-300 underline break-all"
        >
          {part}
        </a>
      );
    }
    return part;
  });
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hello! I'm your AI Study Buddy. How can I help you today? You can ask me questions about your study materials, or select a topic you'd like to learn more about.",
      sender: "ai",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [fileId, setFileId] = useState<string | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load file_id and messages from sessionStorage after hydration (client-side only)
  useEffect(() => {
    setIsHydrated(true);
    if (typeof sessionStorage !== "undefined") {
      const storedFileId = sessionStorage.getItem("current_file_id");
      if (storedFileId) {
        setFileId(storedFileId);
        console.log(`[Chat] Loaded file_id from sessionStorage: ${storedFileId}`);
      }

      // Restore messages from sessionStorage
      const storedMessages = sessionStorage.getItem("chat_messages");
      if (storedMessages) {
        try {
          const parsedMessages = JSON.parse(storedMessages);
          // Convert timestamp strings back to Date objects
          const messagesWithDates = parsedMessages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          }));
          setMessages(messagesWithDates);
          console.log(`[Chat] Restored ${messagesWithDates.length} messages from sessionStorage`);
        } catch (error) {
          console.error("[Chat] Failed to parse stored messages:", error);
        }
      }
    }
  }, []);

  // Save messages to sessionStorage whenever they change
  useEffect(() => {
    if (isHydrated && typeof sessionStorage !== "undefined") {
      sessionStorage.setItem("chat_messages", JSON.stringify(messages));
    }
  }, [messages, isHydrated]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      id: messages.length + 1,
      text: text.trim(),
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    const aiMessageId = messages.length + 2;
    let fullText = "";
    let usedWebSearch = false;

    try {
      // Build conversation history for context (convert to API format)
      const conversationHistory: APIChatMessage[] = messages
        .filter((msg) => msg.id !== 1) // Skip the initial greeting
        .map((msg) => ({
          role: msg.sender === "user" ? "user" : "assistant",
          content: msg.text,
        }));

      // Add placeholder message for streaming
      setMessages((prev) => [...prev, {
        id: aiMessageId,
        text: "",
        sender: "ai",
        timestamp: new Date(),
        usedWebSearch: false,
      }]);

      // Stream the response with forced synchronous updates
      const stream = streamChatMessage(text.trim(), conversationHistory, fileId || undefined);
      let buffer = "";
      let updateCount = 0;

      for await (const chunk of stream) {
        if (chunk.metadata) {
          // Capture web search metadata
          console.log("[STREAM] Metadata:", chunk.metadata);
          if (chunk.metadata.web_search_used) {
            usedWebSearch = true;
          }
        } else if (chunk.text) {
          fullText += chunk.text;
          buffer += chunk.text;

          // Update UI more frequently - every 3 characters OR on newline OR every 5 chunks
          updateCount++;
          if (buffer.length > 3 || chunk.text.includes("\n") || updateCount % 5 === 0) {
            // Use flushSync to force immediate DOM update (no React batching)
            flushSync(() => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === aiMessageId
                    ? { ...msg, text: fullText, usedWebSearch }
                    : msg
                )
              );
            });
            // Scroll to latest message immediately
            scrollToBottom();
            buffer = "";
          }
        } else if (chunk.done) {
          // Stream completed - final update
          console.log("[STREAM] Complete");
          flushSync(() => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === aiMessageId
                  ? { ...msg, text: fullText, usedWebSearch }
                  : msg
              )
            );
          });
          scrollToBottom();
          break;
        } else if (chunk.error) {
          console.error("[STREAM] Error:", chunk.error);
          throw new Error(chunk.error);
        }
      }

      // Ensure message is updated one final time
      if (fullText) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === aiMessageId
              ? { ...msg, text: fullText, usedWebSearch }
              : msg
          )
        );
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to send message. Please try again.";
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? { ...msg, text: `Sorry, I encountered an error: ${errorMessage}` }
            : msg
        )
      );
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputValue);
  };

  const handleQuickTopic = (topic: string) => {
    handleSendMessage(topic);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(inputValue);
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            AI Tutor Chat
          </h1>
          <p className="text-lg text-gray-600 dark:text-gray-300">
            Ask questions, get explanations, and learn at your own pace
          </p>
        </div>

        {/* Quick Topics */}
        {messages.length === 1 && (
          <div className="mb-6">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Quick topics to get started:
            </p>
            <div className="flex flex-wrap gap-2">
              {quickTopics.map((topic, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickTopic(topic)}
                  className="px-4 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
                >
                  {topic}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat Container */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden flex flex-col h-[600px]">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    message.sender === "user"
                      ? "bg-blue-600 text-white rounded-br-sm"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded-bl-sm"
                  }`}
                >
                  <div className="flex items-start space-x-2">
                    {message.sender === "ai" && (
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center mt-0.5">
                        <svg
                          className="w-4 h-4 text-white"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                          />
                        </svg>
                      </div>
                    )}
                    <div className="flex-1">
                      {message.usedWebSearch && message.sender === "ai" && (
                        <div className="inline-flex items-center gap-1 mb-2 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-md text-xs font-medium">
                          <svg
                            className="w-3 h-3"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                            />
                          </svg>
                          Web search used
                        </div>
                      )}
                      <p className="text-sm whitespace-pre-wrap break-words">
                        {linkifyText(message.text)}
                      </p>
                      <p
                        className={`text-xs mt-1 ${
                          message.sender === "user"
                            ? "text-blue-200"
                            : "text-gray-500 dark:text-gray-400"
                        }`}
                      >
                        {message.timestamp.toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 dark:bg-gray-700 rounded-2xl rounded-bl-sm px-4 py-3">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    />
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.4s" }}
                    />
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            <form onSubmit={handleSubmit} className="flex space-x-3">
              <div className="flex-1 relative">
                <textarea
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question or select a topic..."
                  className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white resize-none"
                  rows={1}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "auto";
                    target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                  }}
                  style={{
                    minHeight: "48px",
                    maxHeight: "120px",
                  }}
                />
                <button
                  type="submit"
                  disabled={!inputValue.trim() || isLoading}
                  className={`absolute right-2 bottom-2 p-2 rounded-lg transition-colors ${
                    inputValue.trim() && !isLoading
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "bg-gray-300 dark:bg-gray-600 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                </button>
              </div>
            </form>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>

        {/* Tips */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-xl p-4">
          <div className="flex items-start space-x-3">
            <svg
              className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-1">
                Tips for better learning
              </h3>
              <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
                <li>• Ask specific questions about topics you're struggling with</li>
                <li>• Request explanations at different difficulty levels</li>
                <li>• Ask for examples and real-world applications</li>
                <li>• Request step-by-step explanations for complex concepts</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

