================================================================================
                      DATA ANALYST AI WEB - README
================================================================================

PROJECT OVERVIEW
================================================================================
Data Analyst AI Web is a full-stack web application that combines artificial 
intelligence, data analysis, and interactive visualization. It enables users to 
upload data files (CSV/Excel), ask natural-language questions, and receive 
AI-generated insights, executable Python code, and interactive charts.

The system uses a structured AI-System communication protocol where an LLM 
processes user queries, generates Python code, executes it in a secure E2B 
sandbox, and provides final analysis results.


KEY FEATURES
================================================================================
1. FILE MANAGEMENT
   • Upload CSV, XLS, and XLSX files (max 100 MB)
   • Automatic data extraction and analysis
   • Support for multiple files in a single session
   • File browsing and download capabilities

2. NATURAL LANGUAGE CHAT INTERFACE
   • Ask questions about your data in plain English
   • AI-powered data analysis and insights
   • Real-time chat messaging
   • Session management with file context

3. INTELLIGENT CODE GENERATION & EXECUTION
   • AI generates Python code based on user queries
   • Secure sandbox execution via E2B Code Interpreter
   • Automatic retry logic (up to 4 attempts)
   • Dependency management and installation

4. INTERACTIVE VISUALIZATIONS
   • Automatic chart generation (plots, graphs, dashboards)
   • Manual chart builder for custom visualizations
   • HTML chart rendering
   • Real-time chart preview

5. DATA EXPLORATION
   • Automatic data profiling and statistics
   • Column type inference and semantic understanding
   • Data preview (head/tail rows)
   • Missing data analysis

6. USER FEEDBACK SYSTEM
   • Submit reviews and ratings
   • Provide feedback on AI responses
   • Track user satisfaction

7. API SECURITY
   • X-API-Key authentication for all endpoints
   • CORS support for cross-origin requests
   • RESTful API design


PROJECT STRUCTURE
================================================================================

ROOT DIRECTORY
│
├── back_end/                        # FastAPI backend application
│   ├── requirements.txt             # Python dependencies
│   ├── test_backend.py              # Backend tests
│   ├── test_response.txt            # Test responses
│   ├── app/
│   │   ├── main.py                  # FastAPI application entry point
│   │   │
│   │   ├── api/
│   │   │   └── routers/
│   │   │       ├── chat.py          # Chat and workflow endpoint
│   │   │       ├── upload.py        # File upload endpoint
│   │   │       ├── manual_plot.py   # Manual charting data endpoint
│   │   │       ├── reviews.py       # User feedback endpoint
│   │   │       └── download.py      # File download & management endpoint
│   │   │
│   │   ├── core/
│   │   │   ├── config.py            # Configuration & environment variables
│   │   │   └── security.py          # Authentication & API key validation
│   │   │
│   │   ├── services/
│   │   │   ├── llm_service.py       # LLM integration (OpenRouter, Gemini)
│   │   │   ├── data_service.py      # Data processing & extraction
│   │   │   ├── e2b_service.py       # E2B sandbox execution
│   │   │   ├── session_service.py   # Session & file management
│   │   │   └── structured_workflow.py # AI-System communication protocol
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── response_formatter.py # Response formatting utilities
│   │
│   └── temp_data/                   # Generated files & temporary data
│       ├── *.csv                    # Processed data files
│       ├── *.html                   # Generated charts & visualizations
│       └── *.png                    # Chart images
│
├── frontend/                        # React + Vite frontend application
│   ├── package.json                 # NPM dependencies & scripts
│   ├── vite.config.js               # Vite configuration
│   ├── tailwind.config.js           # Tailwind CSS configuration
│   ├── eslint.config.js             # ESLint configuration
│   ├── index.html                   # HTML entry point
│   │
│   ├── public/                      # Static assets
│   │
│   └── src/
│       ├── main.jsx                 # React entry point
│       ├── App.jsx                  # Root component
│       ├── App.css                  # Global styles
│       ├── index.css                # Index styles
│       │
│       ├── api/
│       │   └── axiosClient.js       # HTTP client configuration
│       │
│       ├── components/
│       │   ├── Layout/
│       │   │   ├── MainLayout.jsx   # Main layout container
│       │   │   ├── Sidebar.jsx      # File navigation sidebar
│       │   │   ├── Topbar.jsx       # Top navigation bar
│       │   │   └── RightPanel.jsx   # Right panel (charts/data)
│       │   │
│       │   ├── chat/
│       │   │   ├── ChatInterface.jsx # Main chat component
│       │   │   └── MessageList.jsx  # Chat message display
│       │   │
│       │   ├── data_view/
│       │   │   ├── DataExplorer.jsx # Data exploration interface
│       │   │   ├── DataExplorerModal.jsx # Data explorer modal
│       │   │   ├── DataTab.jsx      # Data tab component
│       │   │   ├── Charts.jsx       # Chart display
│       │   │   └── Table.jsx        # Data table viewer
│       │   │
│       │   ├── Charts/
│       │   │   ├── ManualChartBuilder.jsx # Custom chart builder
│       │   │   └── VisualizationViewer.jsx # Visualization viewer
│       │   │
│       │   ├── Upload/
│       │   │   └── FileUploader.jsx # File upload component
│       │   │
│       │   ├── Renderers/
│       │   │   ├── DataTableViewer.jsx # Table renderer
│       │   │   ├── MarkdownRenderer.jsx # Markdown renderer
│       │   │   └── PlotlyHtmlRenderer.jsx # HTML chart renderer
│       │   │
│       │   └── Feedback/
│       │       └── ReviewModal.jsx  # Feedback modal
│       │
│       ├── pages/
│       │   └── ManualPlotPage.jsx   # Manual plotting page
│       │
│       ├── services/
│       │   └── api.js               # API service layer
│       │
│       ├── store/
│       │   └── useAppStore.js       # Zustand state management
│       │
│       ├── hooks/                   # Custom React hooks
│       └── assets/                  # Images, icons, etc.


TECHNOLOGY STACK
================================================================================

BACKEND
-------
• FastAPI 0.115.0           - Web framework
• Uvicorn 0.30.6            - ASGI server
• Python 3.9+               - Programming language
• Pydantic 2.9.2            - Data validation

DATA & AI
---------
• Pandas 2.2.3              - Data processing
• OpenRouter API            - LLM provider (OpenAI-compatible)
• Google Gemini API         - Alternative LLM provider
• Hugging Face Hub 0.25.0   - Model hub integration
• E2B Code Interpreter 1.0.5 - Secure Python execution sandbox
• Pinecone 5.0.1            - Vector database (RAG)

FRONTEND
--------
• React 19.2.5              - UI framework
• Vite 8.0.10               - Build tool
• Tailwind CSS 4.2.4        - Utility CSS framework
• Zustand 5.0.13            - State management
• Axios 1.16.0              - HTTP client
• Recharts 3.8.1            - Chart library
• React-Markdown 10.1.0     - Markdown rendering
• Lucide React 1.11.0       - Icon library

UTILITIES
---------
• python-multipart 0.0.12   - File upload handling
• python-dotenv 1.0.1       - Environment configuration
• OpenAI 0.5.0              - OpenRouter client library
• Tenacity                  - Retry logic


ENVIRONMENT SETUP
================================================================================

REQUIREMENTS
------------
• Python 3.9 or higher
• Node.js 18+ and npm
• API Keys (see .env setup below)

BACKEND SETUP
-------------
1. Navigate to back_end directory:
   cd back_end

2. Create a virtual environment:
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Create .env file in back_end directory with:
   OPENROUTER_API_KEY=your_openrouter_key
   GEMINI_API_KEY=your_gemini_api_key (optional)
   HF_TOKEN=your_huggingface_token
   E2B_API_KEY=your_e2b_api_key
   PINECONE_API_KEY=your_pinecone_api_key (optional)
   BACKEND_SECRET_TOKEN=your_secret_token
   TEMP_DATA_DIR=temp_data
   LOG_LEVEL=INFO

5. Run the backend:
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

The backend will be available at http://localhost:8000
Swagger documentation at http://localhost:8000/docs

FRONTEND SETUP
--------------
1. Navigate to frontend directory:
   cd frontend

2. Install dependencies:
   npm install

3. Create .env file in frontend directory with:
   VITE_API_BASE_URL=http://localhost:8000
   VITE_API_KEY=your_secret_token

4. Run development server:
   npm run dev

The frontend will be available at http://localhost:5173

BUILD FOR PRODUCTION
--------------------
Backend:
  • Use gunicorn or similar ASGI server
  • Set BACKEND_SECRET_TOKEN securely
  • Configure CORS to specific origins

Frontend:
  • npm run build
  • Serve dist folder with web server


API ENDPOINTS
================================================================================

All endpoints require X-API-Key header for authentication.

FILE MANAGEMENT
---------------
POST /upload
  Description: Upload a CSV or Excel file for AI analysis
  Parameters: file (multipart/form-data)
  Returns: AI overview of the uploaded data

POST /download
  Description: Download processed files from session
  Parameters: filename (query)
  Returns: File content

CHAT & ANALYSIS
---------------
POST /chat
  Description: Send natural-language query for data analysis
  Parameters: query (string, min 1-5000 chars)
  Returns: AI response, generated code, execution results, artifacts

CHART BUILDING
--------------
POST /manual_plot
  Description: Get data context for manual chart building
  Parameters: chart configuration
  Returns: Chart data and metadata

USER FEEDBACK
-------------
POST /reviews
  Description: Submit user feedback and ratings
  Parameters: feedback (string), rating (1-5)
  Returns: Confirmation

SYSTEM
------
GET /health
  Description: Health check endpoint
  Returns: Server status, version, temp_data_dir path

GET /docs
  Description: Interactive Swagger API documentation

GET /redoc
  Description: ReDoc API documentation


WORKFLOW & COMMUNICATION PROTOCOL
================================================================================

The system uses a structured AI-System communication protocol:

UPLOAD & ANALYSIS FLOW
1. User uploads CSV/Excel file
2. Backend extracts data context (columns, types, statistics)
3. Structured prompt sent to LLM with data context
4. LLM responds with analysis and insights
5. Frontend displays data preview and AI analysis

CHAT & CODE EXECUTION FLOW
1. User asks question about their data
2. System builds structured prompt with:
   - User query
   - Data context (table info, statistics)
   - Available Python packages
   - Previous code execution results
3. LLM generates response with:
   - Response to user (if ready to answer)
   - Request system (tool/E2B_EXE if needs execution)
   - Code (Python code to execute)
4. If E2B_EXE requested:
   - Code executed in secure E2B sandbox
   - Dependencies installed automatically
   - Output and generated files captured
   - Results sent back to LLM for final answer
5. Loop continues up to 4 retries on error
6. Final response returned to frontend

RESPONSE FORMAT
1. Response to user: Final natural language answer
2. Request system: Tool request or E2B_EXE
3. Code: Python code executed (if applicable)


SUPPORTED DATA FORMATS
================================================================================
• CSV (.csv)
• Microsoft Excel (.xls, .xlsx)
• Max file size: 100 MB
• Automatically infers data types and semantic meaning of columns


FEATURES IN DETAIL
================================================================================

DATA PROFILING
--------------
• Automatic column type detection (numeric, categorical, datetime, etc.)
• Statistical summary (mean, median, std dev, min, max)
• Missing value analysis
• Data quality assessment
• Business semantic hints (Revenue, Customer ID, etc.)

CHART GENERATION
----------------
Supported chart types:
• Line charts (time series, trends)
• Bar charts (comparisons, distributions)
• Scatter plots (correlations)
• Histograms (distributions)
• Pie charts (composition)
• Heatmaps (relationships)
• Box plots (statistical distributions)
• Custom Plotly visualizations

MANUAL CHART BUILDER
--------------------
• Define custom chart configurations
• Select data columns for X/Y axes
• Choose chart type and styling
• Generate interactive HTML charts
• Save and export visualizations

SESSION MANAGEMENT
-------------------
• Multiple files in single session
• File context preservation
• Installed package tracking
• Temporary file management
• Automatic cleanup


SECURITY
================================================================================

AUTHENTICATION
• X-API-Key header required for all endpoints
• API key validation on every request
• Session isolation per API key

DATA PROTECTION
• File upload size limits (100 MB)
• File extension validation
• Temporary file storage in isolated directory
• Secure E2B sandbox execution (no system access)

CODE EXECUTION
• Python code runs in ephemeral E2B sandbox (no persistence)
• Only whitelisted packages available
• Automatic dependency installation
• Execution timeout protection


ERROR HANDLING & RETRIES
================================================================================

AUTOMATIC RETRY LOGIC
• LLM calls retry up to 3 times on network errors
• Code execution retries up to 4 times on failure
• Exponential backoff (2s, 4s, 8s)
• Helpful error messages returned to user

COMMON ERRORS
• File too large (>100 MB)
• Unsupported file format
• No data files selected
• Invalid API key
• E2B sandbox errors
• LLM API unavailable


TROUBLESHOOTING
================================================================================

BACKEND WON'T START
• Check Python version (3.9+)
• Verify all dependencies: pip install -r requirements.txt
• Check .env file exists and has required API keys
• Verify port 8000 is not in use

FRONTEND WON'T START
• Check Node.js version (18+)
• Clear npm cache: npm cache clean --force
• Reinstall dependencies: rm node_modules && npm install
• Check .env has VITE_API_BASE_URL

API CALLS FAILING
• Verify X-API-Key header is sent
• Check BACKEND_SECRET_TOKEN matches frontend .env
• Enable CORS if calling from different origin
• Check network connectivity

FILE UPLOAD FAILURES
• File size must be under 100 MB
• Only .csv, .xls, .xlsx formats supported
• Verify file is not corrupted
• Check temp_data directory exists and is writable

CODE EXECUTION ERRORS
• Check Python syntax is valid
• Verify required packages are available
• Check E2B_API_KEY is configured
• Review error message from E2B sandbox

CHART GENERATION ISSUES
• Ensure data columns are valid
• Check data types for axes
• Verify sufficient data for chart type
• Check browser console for rendering errors


DEVELOPMENT TIPS
================================================================================

LOGGING
• Backend logs to console with timestamps
• Set LOG_LEVEL in .env (DEBUG, INFO, WARNING, ERROR)
• Frontend console logs visible in browser DevTools

DEBUGGING
• Backend: Add print() statements or use Python debugger
• Frontend: React Developer Tools browser extension
• Network: Browser DevTools Network tab to inspect API calls
• State: Zustand DevTools to inspect state changes

ADDING NEW FEATURES
• Backend routers: Add to app/api/routers/
• Backend services: Add to app/services/
• Frontend components: Add to src/components/
• Frontend pages: Add to src/pages/
• State: Update Zustand store in src/store/

TESTING
• Backend: python test_backend.py
• Frontend: npm run lint
• API: Use /docs Swagger interface


PRODUCTION DEPLOYMENT
================================================================================

BACKEND
• Use production ASGI server (Gunicorn, Hypercorn)
• Set CORS to specific origins only
• Use secure API keys (rotate regularly)
• Enable HTTPS/TLS
• Set LOG_LEVEL=WARNING
• Use database for session persistence
• Implement rate limiting
• Monitor error logs

FRONTEND
• Build: npm run build
• Serve dist/ folder with CDN or static hosting
• Enable gzip compression
• Set cache headers appropriately
• Use environment-specific .env files

MONITORING
• Track API usage and performance
• Monitor error rates
• Alert on service degradation
• Log all API calls for audit
• Regular security audits


DEPENDENCIES & LICENSES
================================================================================

The project uses open-source libraries with the following licenses:
• FastAPI (MIT)
• React (MIT)
• Tailwind CSS (MIT)
• Zustand (MIT)
• Pandas (BSD)
• E2B (MIT)
• Pinecone (Free tier available)
• OpenRouter (Commercial)

See individual library repositories for full license text.


SUPPORT & CONTACT
================================================================================

For issues or questions:
1. Check this README and troubleshooting section
2. Review API documentation at /docs endpoint
3. Check backend logs for error details
4. Verify .env configuration
5. Test individual endpoints with Swagger UI


VERSION HISTORY
================================================================================

Version 2.2.0 (Current)
• Structured AI-System communication protocol
• OpenRouter LLM integration
• E2B sandbox code execution
• Full chat workflow with retries
• Manual chart builder
• User feedback system
• Session management

Features in development:
• Vector database integration (Pinecone RAG)
• Advanced data profiling
• Collaborative features
• Export/import workflows


AUTHOR & CONTRIBUTORS
================================================================================

Project: Data Analyst AI Web
Type: Full-Stack Web Application
Purpose: AI-powered data analysis with interactive visualization


NOTES & FUTURE ENHANCEMENTS
================================================================================

UPCOMING FEATURES
• Real-time collaboration
• Advanced ML model integration
• SQL query generation
• Natural language to chart conversion
• Data validation and quality scoring
• Export to PowerPoint/PDF
• Scheduled analysis workflows
• API rate limiting and quotas

PERFORMANCE OPTIMIZATION
• Cache data context
• Optimize chart rendering
• Implement pagination for large datasets
• Use web workers for heavy computations

SECURITY IMPROVEMENTS
• OAuth2 authentication
• Role-based access control
• Audit logging
• Data encryption at rest
• Regular security audits


================================================================================
                              END OF README
================================================================================
