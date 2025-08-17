from openai import OpenAI
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
import os
import time


# Load environment variables from .env file
load_dotenv()
# Initialize the OpenAI client using the new SDK usage pattern
client = OpenAI()

# Initialize speech recognizer and text-to-speech engine
recognizer = sr.Recognizer()
speaker = pyttsx3.init()
# Set speech rate to 150 words per minute to ensure clear and understandable speech output (default is ~200, which can be too fast)
speaker.setProperty('rate', 150)  # Set speech rate (default is ~200)

# Function to speak out text
def speak(text):
    print("Romi:", text)
    speaker.say(text)
    speaker.runAndWait()

# Function to listen to microphone input and return the recognized command
def listen():
    # Adjust pause_threshold to 0.8 seconds to allow for natural pauses in speech before considering input complete
    recognizer.pause_threshold = 0.8
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        command = recognizer.recognize_google(audio)
        print("You:", command)
        return command.lower()
    except sr.UnknownValueError:
        speak("Sorry, I didn't catch that.")
        return ""

# Function to send command to OpenAI's GPT model and get a reply
def ask_gpt(prompt):
    # Use the OpenAI client to create a chat completion with the GPT-4 model
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Main loop that runs the assistant
def main():
    speak("Hello! I'm Romi. How can I help you today?")
    try:
        while True:
            command = listen()
            # Filter out very short commands to avoid unnecessary API calls or responses
            if len(command.strip()) < 2:
                continue
            # Check for exit commands to gracefully shut down the assistant
            if "exit" in command or "quit" in command:
                speak("Goodbye!")
                break
            elif command:
                reply = ask_gpt(command)
                speak(reply)
                # Pause briefly to ensure speech output completes before next iteration
                time.sleep(1)
    except KeyboardInterrupt:
        # Catch Ctrl+C to allow graceful shutdown and farewell message
        speak("Shutting down Romi. See you later!")

if __name__ == "__main__":
    main()