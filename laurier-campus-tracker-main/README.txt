LAURIER CAMPUS TRACKER — FRONTEND / UI ONLY

OPEN THE PREVIEW
1. Unzip this package.
2. Open the frontend folder.
3. Double-click index.html to open it in Chrome.
No Python, Terminal, installation or backend is needed for this demo.

FILES
index.html — page structure and script links
style.css — colours, spacing, cards, buttons and responsive layout
app.js — browse/details/report views, navigation, form handling and messages
demo.js — sample spaces and simulated API responses for standalone preview

WHAT YOU CAN DEMONSTRATE
Browse the three demo spaces, open details, submit noise or busyness,
see the updated status, and try an empty submission to see validation.
Reports exist only in memory and reset when you reload or close the page.
This is a UI demonstration, not shared campus data or a database-backed service.

CONNECT TO THE TEAM BACKEND
Remove the demo.js script tag from index.html. Serve index.html, app.js
and style.css from the same origin as the team's API. app.js then uses:
GET /api/spaces — {spaces:[{id,building,name,description,category,status}]}
GET /api/spaces/{id} — {space:{id,building,name,description,category,status}}
POST /api/reports — JSON {space_id,noise,busyness}; successful JSON response.
Errors should return a non-2xx HTTP code and JSON {error:"message"}.
Each status contains noise and busyness objects with value, count,
updated_at (Unix seconds or null), and limited (boolean).
The backend remains responsible for validation, persistence and expiry.
Change the footer text after integration so it accurately describes the mode.

CHECK BEFORE HANDOFF
Test navigation, the two reporting fields, validation, keyboard focus,
phone layout and enlarged text in your browser. Browser visual checks
have not been completed in the build environment.
