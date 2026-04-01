import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_new_model():
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("No API Key")
        return
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Try gemini-1.5-flash
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Hello, can you hear me?")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_new_model()
