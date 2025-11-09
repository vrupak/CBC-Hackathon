import { type RouteConfig, index, route } from "@react-router/dev/routes";
// You need to manually import the CourseDetails component here if it's not handled automatically by your dev tool.
// Assuming CourseDetails is located at 'routes/CourseDetails.tsx' based on import paths in other files.

// Define the static routes
const routes = [
  index("routes/home.tsx"),
  route("study-path", "routes/study-path.tsx"),
  route("chat", "routes/chat.tsx"),
];

// Define the dynamic route pattern separately
const dynamicRoutes = [
  // --- ADD THE COURSE DETAILS DYNAMIC ROUTE ---
  route("course/:id", "routes/CourseDetails.tsx"), 
  // --------------------------------------------
];

// Combine and export all routes
export default [
    ...routes,
    ...dynamicRoutes
] satisfies RouteConfig;