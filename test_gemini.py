# test_gemini.py
import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv

async def main():
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key or api_key == "YOUR_GOOGLE_API_KEY_HERE":
        print("ERROR: GOOGLE_API_KEY not found or not set in .env file.")
        return

    print("API Key loaded. Configuring Gemini...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        print("Gemini configured. Sending a test message...")
        
        response = await model.generate_content_async("Hello, world!")
        
        print("\n--- Gemini API Test Successful ---")
        print(response.text)
        print("------------------------------------")

    except Exception as e:
        print(f"\n--- Gemini API Test Failed ---")
        print(f"An error occurred: {e}")
        print("--------------------------------")

if __name__ == "__main__":
    asyncio.run(main())

