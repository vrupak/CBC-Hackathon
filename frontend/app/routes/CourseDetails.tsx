import React, { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from 'react-router-dom';
import { RefreshCw } from 'lucide-react';
import { 
    getCourseModules, 
    syncCourseFiles, 
    downloadModuleFile, 
    ingestModuleFile,
    type LocalModule,
} from "../utils/api"; 
import { Layout } from "../components/Layout"; 


// Define component for file status icons/buttons
const ModuleActions: React.FC<{ 
    module: LocalModule; 
    onActionComplete: () => void;
    onError: (msg: string) => void;
    // Inject navigate function to handle redirection to Study Path
    navigate: ReturnType<typeof useNavigate>;
    courseName: string;
}> = ({ module, onActionComplete, onError, navigate, courseName }) => {
    const [isDownloading, setIsDownloading] = useState(false);
    const [isIngesting, setIsIngesting] = useState(false);
    
    // Determine the next required action
    const nextAction = !module.is_downloaded ? 'download' : !module.is_ingested ? 'ingest' : 'completed';

    const handleAction = async () => {
        if (nextAction === 'download') {
            setIsDownloading(true);
            try {
                await downloadModuleFile(module.id);
                onActionComplete(); // Trigger parent refresh
            } catch (err: any) {
                console.error("Download failed:", err);
                onError(err.response?.data?.detail || "Failed to download file.");
            } finally {
                setIsDownloading(false);
            }
        } else if (nextAction === 'ingest') {
            setIsIngesting(true);
            try {
                // NOTE: In a full implementation, the ingestion response might return the extracted topics directly.
                // For this mock, we just proceed after successful ingestion status update.
                await ingestModuleFile(module.id); 
                onActionComplete(); // Trigger parent refresh
            } catch (err: any) {
                console.error("Ingestion failed:", err);
                onError(err.response?.data?.detail || "Failed to ingest file into Supermemory.");
            } finally {
                setIsIngesting(false);
            }
        }
    };
    
    // Handle navigation to study path (simulating topic extraction via navigation state)
    const handleGeneratePath = () => {
        // NOTE: Since the backend currently only marks 'is_ingested=True' and doesn't return topics on ingestion,
        // we'll navigate to the study path route and pass a placeholder to simulate the link.

        // Placeholder for future topic extraction logic:
        const mockTopics = [
            {
                id: 1,
                title: "Mock Topic 1: Introduction to Data Structures",
                description: "Fundamental concepts needed for understanding the rest of the course.",
                status: 'in-progress',
                subtopics: [{ id: 1, title: 'Arrays vs Linked Lists', completed: false }, { id: 2, title: 'Big O Notation Overview', completed: false }],
            }
        ];
        
        // Use sessionStorage as a reliable way to pass complex data across routes, 
        // similar to how the main Home upload works.
        if (typeof sessionStorage !== 'undefined') {
            sessionStorage.setItem('extractedTopicsJson', JSON.stringify(mockTopics));
            sessionStorage.setItem('filename', module.name);
        }

        navigate("/study-path", {
            state: {
                // Simulate topic data being passed from an extraction endpoint
                topics: mockTopics, 
                filename: module.name,
                source: `${courseName} - ${module.name}`
            },
        });
    };


    // --- THEMED BUTTON LOGIC ---
    const isActionDisabled = isDownloading || isIngesting;

    // Status Indicator
    const StatusBadge = ({ label, color }: { label: string, color: string }) => (
        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${color}`}>
            {label}
        </span>
    );

    let statusElement: React.ReactNode;
    let buttonText: string | null = null;
    let buttonColor: string;
    let buttonHandler: (() => void) | null = null;

    if (module.is_ingested) {
        statusElement = <StatusBadge label="Ingested" color="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300" />;
        buttonText = "Generate Path";
        // Final action uses the bold purple/indigo theme
        buttonColor = "bg-purple-600 hover:bg-purple-700 text-white";
        buttonHandler = handleGeneratePath;
    } else if (module.is_downloaded) {
        statusElement = <StatusBadge label="Downloaded" color="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300" />;
        buttonText = isIngesting ? "Ingesting..." : "Ingest into AI";
        // Primary action uses the indigo theme
        buttonColor = isIngesting ? "bg-indigo-400 text-white cursor-not-allowed" : "bg-indigo-600 hover:bg-indigo-700 text-white";
        buttonHandler = handleAction;
    } else {
        statusElement = <StatusBadge label="Available" color="bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300" />;
        buttonText = isDownloading ? "Downloading..." : "Download File";
        // Primary action uses the blue theme
        buttonColor = isDownloading ? "bg-blue-400 text-white cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700 text-white";
        buttonHandler = handleAction;
    }
    

    return (
        <div className="flex items-center space-x-4">
            {statusElement}
            {buttonText && (
                <button
                    onClick={buttonHandler ?? undefined}
                    disabled={isActionDisabled}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow ${
                        isActionDisabled && !buttonText.includes('Generate') // Only disable if actively downloading/ingesting
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : buttonColor
                    }`}
                >
                    {buttonText}
                </button>
            )}
        </div>
    );
};


export default function CourseDetails() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const localCourseId = parseInt(id || '0', 10);
    
    const [courseName, setCourseName] = useState('Loading Course...');
    const [modules, setModules] = useState<LocalModule[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isSyncing, setIsSyncing] = useState(false);
    
    // 1. Fetch Course Details and Modules
    const fetchModules = useCallback(async () => {
        if (!localCourseId) return;
        setIsLoading(true);
        setError(null);
        try {
            const data = await getCourseModules(localCourseId);
            setCourseName(data.courseName);
            setModules(data.modules);
        } catch (err: any) {
            const message = err.response?.data?.detail || "Failed to load course details. Course not found.";
            setError(message);
        } finally {
            setIsLoading(false);
        }
    }, [localCourseId]);

    useEffect(() => {
        fetchModules();
    }, [fetchModules]);

    // 2. Sync Files Handler
    const handleSyncFiles = async () => {
        setIsSyncing(true);
        setError(null);
        try {
            const response = await syncCourseFiles(localCourseId);
            setError(null);
            // Refresh module list after successful sync
            await fetchModules(); 
            // Show a success message if modules were found/synced
            if (response.total_files_found > 0) {
                 setError(`Success: Synced ${response.total_files_found} file(s) from Canvas.`);
            } else {
                 setError("Success: No new files found on Canvas to sync.");
            }
        } catch (err: any) {
            const message = err.response?.data?.detail || "Failed to sync files from Canvas. Check token.";
            setError(message);
        } finally {
            setIsSyncing(false);
        }
    };
    
    // 3. Module Action Handler (passed to child component)
    const handleModuleActionComplete = () => {
        // Just refetch the modules list to update statuses in real-time
        fetchModules();
    };

    if (isLoading) {
        return (
            <Layout>
                <div className="text-center p-12 text-gray-600 dark:text-gray-400">
                    <svg className="animate-spin h-8 w-8 text-blue-600 mx-auto" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    <p className="mt-4">Loading course details...</p>
                </div>
            </Layout>
        );
    }
    
    if (error && courseName === 'Loading Course...') {
         return (
            <Layout>
                <div className="max-w-4xl mx-auto p-8 bg-red-100 dark:bg-red-900/20 rounded-xl">
                    <h1 className="text-2xl font-bold text-red-800 dark:text-red-300 mb-4">Error Loading Course</h1>
                    <p className="text-red-700 dark:text-red-400">{error}</p>
                    <button onClick={() => navigate('/')} className="mt-6 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Go to Home</button>
                </div>
            </Layout>
        );
    }

    return (
        <Layout>
            <div className="max-w-6xl mx-auto">
                {/* Header: Fixed to use separate blocks for text and button */}
                <div className="mb-8 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-4"> 
                    
                    {/* Course Info Block */}
                    <div className="flex-1 min-w-0 pr-4"> {/* Added min-w-0 to handle overflow */}
                        <button onClick={() => navigate('/')} className="flex items-center text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 mb-2">
                             <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                             Back to Courses
                        </button>
                        <h1 className="text-4xl font-bold text-gray-900 dark:text-white leading-tight"> {/* Added leading-tight for better line spacing */}
                            {courseName}
                        </h1>
                        <p className="text-lg text-gray-600 dark:text-gray-300">
                            Manage Study Materials from Canvas
                        </p>
                    </div>

                    {/* Sync Button Block (Flex-shrink to prevent it from forcing overflow) */}
                    <div className="flex-shrink-0 pt-2 sm:pt-0"> 
                         <button
                            onClick={handleSyncFiles}
                            disabled={isSyncing}
                            className={`px-6 py-3 rounded-xl font-semibold transition-colors shadow-lg flex items-center justify-center ${
                                isSyncing
                                    ? "bg-blue-400 text-white cursor-not-allowed" // Loading state uses lighter blue
                                    : "bg-blue-600 text-white hover:bg-blue-700" // Primary button color (matching nav bar blue)
                            }`}
                        >
                            {isSyncing ? (
                                <>
                                    {/* Loading spinner for sync */}
                                    <svg className="animate-spin h-5 w-5 text-white mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                                    Syncing...
                                </>
                            ) : (
                                <>
                                    {/* Updated Sync Icon: Generic Reload/Refresh */}
                                    <RefreshCw className="w-5 h-5 mr-2" />
                                    Sync Files from Canvas
                                </>
                            )}
                        </button>
                    </div>
                </div>
                
                {/* Error/Message Display */}
                {error && (
                    <div className={`mb-6 p-4 rounded-xl ${error.includes('Success') || error.includes('synced') ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800'}`}>
                        <p className="font-semibold">{error}</p>
                    </div>
                )}


                {/* Modules List */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl overflow-hidden">
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {modules.length > 0 ? (
                            modules.map(module => (
                                <div key={module.id} className="p-4 sm:p-6 flex justify-between items-center hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                    <div className="flex-1 min-w-0 pr-4">
                                        <p className="text-lg font-medium text-gray-900 dark:text-white truncate">
                                            {module.name}
                                        </p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                            {module.canvas_file_id ? `Canvas File ID: ${module.canvas_file_id}` : 'Manual Upload'}
                                        </p>
                                    </div>
                                    <div className="flex-shrink-0">
                                        <ModuleActions 
                                            module={module} 
                                            onActionComplete={handleModuleActionComplete} 
                                            onError={setError} 
                                            navigate={navigate}
                                            courseName={courseName}
                                        />
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="p-12 text-center text-gray-600 dark:text-gray-400">
                                <p className="text-xl font-semibold">No Study Materials Found</p>
                                <p className="mt-2">Click "Sync Files from Canvas" above to load files from this course.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
}