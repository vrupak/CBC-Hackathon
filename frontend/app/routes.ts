import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("study-path", "routes/study-path.tsx"),
  route("chat", "routes/chat.tsx"),
] satisfies RouteConfig;
