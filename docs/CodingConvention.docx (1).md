# **Coding Convention**

## **1\. General Naming Rules**

Use clear, consistent, and descriptive names. Avoid abbreviations unless they are very common, such as id, url, api, ui, db.

### **Recommended**

studentProfile  
practiceSession  
feedbackAssessment  
startPracticeSession()  
submitAudioRecording()

### **Avoid**

stuProf  
pracSess  
fbAssess  
doThing()  
handleData()  
Names should describe **what the item is** or **what the function does**.

---

# **2\. UI Element ID and Class Naming**

## **2.1 HTML / JSX ID Convention**

Use **kebab-case** for id.

Format:

screen-section-element  
Example:

\<input id="login-form-email-input" /\>  
\<button id="practice-session-start-button" /\>  
\<div id="feedback-summary-card" /\>

### **Rules**

Each id must be unique on the page.

Use id only when the element needs to be directly referenced, such as:

document.getElementById("audio-record-button")  
Avoid using id only for styling. Use className instead.

---

## **2.2 CSS Class Naming**

Use **kebab-case** for CSS classes.

Recommended format:

component-name\_\_element-name--state  
This follows a BEM-style structure.

Example:

\<div class="practice-card"\>  
  \<h3 class="practice-card\_\_title"\>Restaurant Conversation\</h3\>  
  \<button class="practice-card\_\_button practice-card\_\_button--active"\>  
    Start  
  \</button\>  
\</div\>

### **Examples**

.practice-card {}  
.practice-card\_\_title {}  
.practice-card\_\_description {}  
.practice-card\_\_button {}  
.practice-card\_\_button--active {}  
.practice-card\_\_button--disabled {}

### **Common UI State Classes**

.is-active  
.is-disabled  
.is-loading  
.is-hidden  
.has-error  
.has-success  
Example:

\<button class="record-button is-loading"\>Processing...\</button\>  
---

## **2.3 React / Component Class Naming**

Use **PascalCase** for components.

LoginScreen  
PracticeSessionScreen  
FeedbackSummaryCard  
AudioRecorderButton  
Component file names should match the component name.

PracticeSessionScreen.tsx  
FeedbackSummaryCard.tsx  
AudioRecorderButton.tsx  
---

# **3\. Functions Naming Convention**

Use **camelCase** for functions.

Function names should usually start with a verb.

## **Common Verb Prefixes**

| Prefix | Use For | Example |
| ----- | ----- | ----- |
| get | retrieve data | getStudentProfile() |
| fetch | call API or remote service | fetchPracticeSessions() |
| create | create new data | createPracticeSession() |
| update | update existing data | updateStudentProgress() |
| delete | delete data | deleteAudioRecord() |
| handle | UI event handlers | handleStartPractice() |
| validate | validation logic | validateEmail() |
| format | display formatting | formatFeedbackScore() |
| calculate | calculations | calculatePronunciationScore() |
| generate | AI-generated content | generateHint() |
| submit | form or request submission | submitAudioRecording() |

### **Examples**

function fetchStudentProfile(studentId: string) {}

function handleRecordButtonClick() {}

function validatePracticeInput(input: string) {}

function generateAiFeedback(audioRecordId: string) {}

### **Avoid vague function names**

processData()  
doSubmit()  
handleClick()  
makeResult()  
Better:

processAudioRecording()  
submitPracticeAnswer()  
handleStartRecordingClick()  
generateFeedbackResult()  
---

# **4\. Variables Naming Convention**

Use **camelCase** for variables.

const studentId \= "123";  
const practiceSessionId \= "abc";  
const pronunciationScore \= 85;  
const isRecording \= true;

## **Boolean Variables**

Boolean variables should start with:

is / has / can / should / was / did  
Examples:

const isRecording \= false;  
const hasCompletedLesson \= true;  
const canSubmitAnswer \= false;  
const shouldShowHint \= true;  
const wasFeedbackGenerated \= true;  
Avoid:

const recording \= true;  
const completed \= false;  
const submit \= true;  
---

## **Array Variables**

Use plural names for arrays.

const students \= \[\];  
const practiceSessions \= \[\];  
const feedbackAssessments \= \[\];  
const lessonPhrases \= \[\];  
Avoid:

const studentListArray \= \[\];  
const data \= \[\];  
const items \= \[\];  
---

## **Constants**

Use UPPER\_SNAKE\_CASE for global constants.

const MAX\_RECORDING\_DURATION\_SECONDS \= 60;  
const DEFAULT\_FEEDBACK\_LANGUAGE \= "vi";  
const API\_BASE\_URL \= "/api/v1";  
For local constants, use camelCase.

const maxRetryCount \= 3;  
const defaultTopicId \= "daily-conversation";  
---

# **5\. API Route Naming Convention**

Use **kebab-case** for API paths.

Use nouns instead of verbs.

Recommended format:

/api/v1/resource-name  
/api/v1/resource-name/:id  
/api/v1/resource-name/:id/sub-resource  
---

## **5.1 REST API Route Examples**

### **Students**

GET    /api/v1/students  
GET    /api/v1/students/:studentId  
POST   /api/v1/students  
PATCH  /api/v1/students/:studentId  
DELETE /api/v1/students/:studentId

### **Student Profiles**

GET    /api/v1/students/:studentId/profile  
PATCH  /api/v1/students/:studentId/profile

### **Topics**

GET    /api/v1/topics  
GET    /api/v1/topics/:topicId

### **Lessons**

GET    /api/v1/topics/:topicId/lessons  
GET    /api/v1/lessons/:lessonId

### **Practice Sessions**

GET    /api/v1/students/:studentId/practice-sessions  
POST   /api/v1/practice-sessions  
GET    /api/v1/practice-sessions/:sessionId  
PATCH  /api/v1/practice-sessions/:sessionId  
DELETE /api/v1/practice-sessions/:sessionId

### **Audio Records**

POST   /api/v1/practice-sessions/:sessionId/audio-records  
GET    /api/v1/audio-records/:audioRecordId  
DELETE /api/v1/audio-records/:audioRecordId

### **AI Feedback**

POST   /api/v1/practice-sessions/:sessionId/feedback-assessments  
GET    /api/v1/feedback-assessments/:feedbackAssessmentId

### **Hints**

POST   /api/v1/practice-sessions/:sessionId/hints  
GET    /api/v1/practice-sessions/:sessionId/hints  
---

## **5.2 API Route Rules**

Use nouns:

GET /api/v1/practice-sessions  
Avoid verbs:

GET /api/v1/get-practice-sessions  
Use HTTP methods to describe the action:

| Action | Method |
| ----- | ----- |
| Read | GET |
| Create | POST |
| Update partially | PATCH |
| Replace fully | PUT |
| Delete | DELETE |

---

# **6\. API Request and Response Body Naming**

Use **camelCase** for JSON fields.

Example request:

{  
  "studentId": "stu\_123",  
  "topicId": "topic\_restaurant",  
  "lessonId": "lesson\_order\_food"  
}  
Example response:

{  
  "sessionId": "session\_123",  
  "studentId": "stu\_123",  
  "status": "inProgress",  
  "startedAt": "2026-06-10T10:00:00Z"  
}  
Avoid mixing styles:

{  
  "student\_id": "stu\_123",  
  "topic-id": "topic\_restaurant"  
}  
---

# **7\. Database Naming Convention**

Use **snake\_case** for database tables and columns.

## **Table Names**

Use plural nouns.

students  
student\_profiles  
practice\_sessions  
audio\_records  
feedback\_assessments  
progress\_records  
recommendations  
safety\_events

## **Column Names**

Use snake\_case.

student\_id  
practice\_session\_id  
audio\_record\_url  
pronunciation\_score  
created\_at  
updated\_at

## **Primary Key**

Use:

id  
or entity-specific ID:

student\_id  
practice\_session\_id  
Choose one style and keep it consistent.

Recommended for your project:

id  
with foreign keys like:

student\_id  
lesson\_id  
topic\_id  
practice\_session\_id  
---

# **8\. File and Folder Naming**

Use **kebab-case** for folders and non-component files.

practice-session/  
audio-recorder/  
feedback-summary/  
api-client.ts  
date-utils.ts  
validation-utils.ts  
Use **PascalCase** for React component files.

PracticeSessionScreen.tsx  
AudioRecorderButton.tsx  
FeedbackSummaryCard.tsx  
Suggested frontend structure:

src/  
  components/  
    audio-recorder/  
      AudioRecorderButton.tsx  
      audio-recorder.css  
  screens/  
    practice-session/  
      PracticeSessionScreen.tsx  
  services/  
    api-client.ts  
    practice-session-service.ts  
  utils/  
    date-utils.ts  
    score-utils.ts  
  types/  
    student.ts  
    practice-session.ts  
Suggested backend structure:

src/  
  modules/  
    students/  
      student.controller.ts  
      student.service.ts  
      student.repository.ts  
    practice-sessions/  
      practice-session.controller.ts  
      practice-session.service.ts  
      practice-session.repository.ts  
    ai-feedback/  
      ai-feedback.service.ts  
  middlewares/  
  config/  
  utils/  
---

# **9\. Type / Interface Naming**

Use **PascalCase**.

type StudentProfile \= {};  
type PracticeSession \= {};  
type FeedbackAssessment \= {};  
type AudioRecord \= {};  
For request and response DTOs:

type CreatePracticeSessionRequest \= {};  
type CreatePracticeSessionResponse \= {};

type GenerateFeedbackRequest \= {};  
type GenerateFeedbackResponse \= {};  
Avoid vague names:

type Data \= {};  
type Result \= {};  
type Response \= {};  
---

# **10\. Enum Naming**

Use **PascalCase** for enum names and **UPPER\_SNAKE\_CASE** for enum values.

enum PracticeSessionStatus {  
  NOT\_STARTED \= "NOT\_STARTED",  
  IN\_PROGRESS \= "IN\_PROGRESS",  
  COMPLETED \= "COMPLETED",  
  CANCELLED \= "CANCELLED"  
}  
Example:

const sessionStatus \= PracticeSessionStatus.IN\_PROGRESS;  
---

# **11\. Error Naming Convention**

Error classes should use **PascalCase** and end with Error.

StudentNotFoundError  
PracticeSessionNotFoundError  
AudioUploadFailedError  
AiFeedbackGenerationError  
API error response should use camelCase:

{  
  "errorCode": "PRACTICE\_SESSION\_NOT\_FOUND",  
  "message": "Practice session not found.",  
  "details": {  
    "sessionId": "session\_123"  
  }  
}  
---

# **12\. Event Handler Naming**

Frontend event handlers should start with handle.

handleLoginSubmit()  
handleStartRecordingClick()  
handleStopRecordingClick()  
handleHintButtonClick()  
handlePracticeSessionEnd()  
Props for event handlers should start with on.

\<AudioRecorderButton  
  onStartRecording={handleStartRecording}  
  onStopRecording={handleStopRecording}  
/\>  
---

# **13\. AI Feature Naming Convention**

For AI-related logic, use clear prefixes such as:

ai  
generate  
evaluate  
analyze  
recommend  
Examples:

generateAiHint()  
generateAiFeedback()  
evaluatePronunciation()  
analyzeConversationMessage()  
recommendNextLesson()  
For AI API routes:

POST /api/v1/ai/feedback  
POST /api/v1/ai/hints  
POST /api/v1/ai/recommendations  
Or, if tied to a practice session:

POST /api/v1/practice-sessions/:sessionId/ai-feedback  
POST /api/v1/practice-sessions/:sessionId/ai-hints  
Recommended style for your project:

POST /api/v1/practice-sessions/:sessionId/feedback-assessments  
POST /api/v1/practice-sessions/:sessionId/hints  
POST /api/v1/students/:studentId/recommendations  
This keeps the API resource-based instead of AI-feature-based.

---

# **14\. Git Branch Naming**

Use lowercase and kebab-case.

Format:

type/short-description  
Examples:

dev/practice-session-flow  
feature/audio-recording  
fix/login-validation-error  
refactor/feedback-service  
docs/api-route-convention  
Common branch types:

dev/  
fix/  
refactor/  
docs/  
test/  
chore/  
---

# **15\. Commit Message Convention**

Use this format:

type: short description  
Examples:

dev: add practice session creation API  
fix: prevent empty audio submission  
refactor: move feedback logic to ai feedback service  
docs: add coding convention section  
test: add unit tests for score calculation  
Common commit types:

| Type | Meaning |
| ----- | ----- |
| dev | develop new feature |
| fix | bug fix |
| refactor | code restructure without behavior change |
| docs | documentation |
| test | tests |
| chore | maintenance |
| style | formatting only |

---

# **16\. Environment Variable Naming**

Use **UPPER\_SNAKE\_CASE**.

DATABASE\_URL=  
JWT\_SECRET=  
OPENAI\_API\_KEY=  
AUDIO\_STORAGE\_BUCKET=  
MAX\_RECORDING\_DURATION\_SECONDS=  
Do not expose secret values in frontend code.

Avoid:

dbUrl=  
openAiKey=  
secret=  
---

# **17\. Logging Convention**

Use structured log messages.

logger.info("Practice session created", {  
  studentId,  
  sessionId  
});

logger.error("AI feedback generation failed", {  
  sessionId,  
  audioRecordId,  
  error  
});  
Avoid unclear logs:

console.log("done");  
console.log("error here");  
console.log(data);  
---

# **18\. Test Naming Convention**

Test file names:

practice-session.service.test.ts  
audio-record.controller.test.ts  
feedback-assessment.service.test.ts  
Test case names should describe expected behavior.

it("creates a practice session when student and lesson are valid", () \=\> {});

it("returns an error when audio file is missing", () \=\> {});

it("generates feedback after audio record is submitted", () \=\> {});  
---

# **19\. Recommended Summary Table**

| Area | Convention | Example |
| ----- | ----- | ----- |
| UI ID | kebab-case | practice-session-start-button |
| CSS class | BEM / kebab-case | practice-card\_\_button--active |
| Component | PascalCase | FeedbackSummaryCard |
| Function | camelCase | generateAiFeedback() |
| Variable | camelCase | pronunciationScore |
| Boolean | is/has/can/should prefix | isRecording |
| Constant | UPPER\_SNAKE\_CASE | MAX\_RECORDING\_DURATION\_SECONDS |
| API route | kebab-case | /api/v1/practice-sessions |
| JSON field | camelCase | practiceSessionId |
| DB table | snake\_case plural | practice\_sessions |
| DB column | snake\_case | student\_id |
| Type/interface | PascalCase | PracticeSession |
| Enum value | UPPER\_SNAKE\_CASE | IN\_PROGRESS |
| File/folder | kebab-case | practice-session-service.ts |
| Git branch | kebab-case | feature/audio-recording |
| Commit | conventional commit | feat: add audio upload API |

---

