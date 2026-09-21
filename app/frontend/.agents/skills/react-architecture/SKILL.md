# Skill: React & TypeScript Architecture

## Component Structure
1. Write functional React components using TypeScript interfaces for all props.
2. Export components using named exports (`export const Component = ...`), not default exports.
3. Keep components small. If a file exceeds 150 lines, break the UI down into smaller sub-components (e.g., extract a `Table` or `Card` component).

## Data Fetching & State
1. **No Mock Logic:** NEVER hardcode fake data arrays or simulate AI processing in the component. You must assume all data comes from the backend API via Axios.
2. **Mandatory States:** Every component that fetches data MUST implement and render three distinct states:
   - `loading`: Display a skeleton loader or a spinner (`Loader2` from lucide-react with `animate-spin`).
   - `error`: Display a styled error boundary or alert box if the Axios request fails.
   - `success`: Render the actual data.
3. **Optional Chaining:** Always use optional chaining (`?.`) and nullish coalescing (`??`) when accessing nested API data, especially for AI intelligence objects which may be undefined while processing.

## Clean Code Rules
- Destructure props in the function signature.
- Group imports logically: React/Hooks first, third-party libraries second, internal APIs/Types third, local components last.
- Do not use `any`. Import the strict types from `../types`.