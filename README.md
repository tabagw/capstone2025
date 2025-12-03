# Cooking Captain

Cooking Captain is a recipe book that utilizes a voice assistant to guide its users through a sequence of instructions hands-free. The user chooses their recipes through discovering, saving, and accessing recipes from popular cooking websites. Built with Python and deployed through AWS Lambda, this application integrates with Alexa Skills Kit SDK to provide its users with a voice interface. Using the MYSQL database, users can save recipes for future use. The application can handle multiple user intents through a recipe search, help requests, and session management through a conversational model. 

## ✨ Features

**Recipe Discovery** — Search your recipe database by name using natural language. The skill uses fuzzy matching to find recipes even when you don't remember the exact name.

**Hands-Free Cooking** — Navigate through cooking instructions using voice commands. Say "next" to advance, "repeat" to hear a step again, or "previous" to go back.

**Smart Step Combining** — Automatically combines short header steps (like "Preheat") with their detailed instructions for a smoother cooking experience.

## 🚀 Quick Start 

**Amazon Website** — Visit [Cooking Captain on Amazon](https://www.amazon.com/Cooking-Captain/dp/B0FZKH5WCM) and click "Enable"

**Alexa App** — Open the Alexa app → More → Skills & Games → Search "Cooking Captain" → Enable to Use

**Voice** — Say "Alexa, enable Cooking Captain"

### Basic Commands

```
"Alexa, open Cooking Captain"    → Launch the skill
"Find [recipe name]"             → Search for a recipe
"Yes" / "No"                     → Confirm or decline
"Next"                           → Go to next step
"Repeat"                         → Hear current step again
"Previous"                       → Go back one step
"Help"                           → Get assistance
"Stop"                           → Exit the skill
```

## Voice Commands

**Finding Recipes**
- "Find chocolate cake"
- "Search for pasta recipes"
- "How do I make chicken soup"

**During Cooking**
- "Next" or "Next step" — Move to the next instruction
- "Repeat" — Hear the current step again
- "Previous" or "Go back" — Return to the previous step

**General**
- "Help" — Get usage instructions
- "Stop" or "Cancel" — Exit the skill

## License

MIT License
