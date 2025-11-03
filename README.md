# Jarvis Voice AI Agent (Python + Web)

A deployable voice-controlled web assistant that listens for commands like:
- "Hey Jarvis, call daddy"
- "Jarvis, open Google Maps and start directions to Sadar Bazaar Chatgali"
- "Jarvis, make a hair salon appointment on 4th November at 2 pm"

It runs as a static web app with a Python serverless backend on Vercel.

## Features
- Voice capture in the browser (Web Speech API)
- Text-to-speech responses
- Python intent parser (no external ML required)
- Actions:
  - Call a contact (via `tel:` link on supported devices)
  - Open Google Maps with navigation to a destination
  - Create a Google Calendar event via pre-filled template URL
- Works without any API keys (demo mode). Optional environment variables improve behavior.

## Quick Start (Local Preview)
1. Serve the folder locally with any static server, or open `index.html` directly in a Chromium browser.
2. Click "Start Listening" and speak your command.
3. The app sends your text to `/api/agent` (Python) and executes returned actions in the browser.

Note: The Python serverless function is designed for Vercel. Local testing of the function requires `vercel dev` or a similar serverless emulator; otherwise use the live deployment.

## Deploy to Vercel
1. Ensure Vercel CLI is authenticated in your environment.
2. Deploy:
   ```bash
   vercel deploy --prod --yes --token $VERCEL_TOKEN --name agentic-e976b4b6
   ```
3. After a few seconds, verify:
   ```bash
   curl https://agentic-e976b4b6.vercel.app
   ```

## Environment Variables (Optional)
Set any of these in your Vercel project for better results:
- `DADDY_PHONE`: E.g. `+15551234567`
- `MOM_PHONE`, `WIFE_PHONE`, `HUSBAND_PHONE`: Similar format
- Custom contact: create `ALICE_PHONE`, then say "call Alice"

No keys are required for maps or calendar (uses public URLs). Calls use `tel:` link which opens the system dialer on supported devices (phones, some desktop apps).

## Usage Examples
- Call:
  - "Hey Jarvis, call daddy" → triggers `tel:+...` using `DADDY_PHONE`
  - "Jarvis, call +91 98765 43210" → directly dials the given number
- Navigation:
  - "Jarvis, open Google Maps and start directions to Sadar Bazaar Chatgali"
  - "Jarvis, navigate to Delhi airport"
- Appointment:
  - "Jarvis, make a hair salon appointment on 4th November at 2 pm"
  - If time omitted, defaults to 9:00 AM

## How It Works (Step by Step AGI-Style Flow)
1. Wake phrase and capture
   - You say "Hey Jarvis ..." in the browser.
   - Web Speech API transcribes speech to text.
2. Intent parsing (Python)
   - The text is sent to `/api/agent`.
   - `api/agent.py` normalizes the text, removes wake words, and applies rule-based parsing for intents: `CALL`, `MAPS`, `APPOINTMENT`.
3. Entity extraction
   - `CALL`: extracts contact name/number. Looks up env vars for names like `DADDY_PHONE`.
   - `MAPS`: extracts destination after the word "to".
   - `APPOINTMENT`: parses simple natural date/time like "4th November at 2 pm".
4. Action planning and response
   - The agent builds a response string and an array of actions, such as `open_url`, `call`, `create_calendar`.
5. Client execution
   - The web app speaks the response (TTS) and performs actions:
     - `open_url`: opens Google Maps or Calendar in a new tab
     - `call`: triggers a `tel:` link
6. User confirmation
   - For calendar creation, Google Calendar shows a pre-filled event; you confirm and save.

## Files
- `index.html`: UI scaffold
- `styles.css`: Minimal styling
- `script.js`: Speech recognition, TTS, UI, and action execution
- `api/agent.py`: Python serverless intent parser and action planner
- `vercel.json`: Vercel config for static + Python function

## Extending the Agent
- Add more contacts: define `ALICE_PHONE`, `BOB_PHONE`, etc.
- Add new intents in `api/agent.py` by detecting keywords and returning new action types.
- Integrate real telephony (Twilio) by adding a secure server-side function and storing credentials in env vars (not included by default).

## Browser Support
- Speech recognition uses the Web Speech API; best in Chrome-based browsers.
- Text-to-speech works across most modern browsers.

## Privacy
- Speech stays in your browser except for the transcribed text sent to the serverless function for intent parsing.

## License
MIT
