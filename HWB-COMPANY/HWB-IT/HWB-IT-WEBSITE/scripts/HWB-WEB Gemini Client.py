import os
import sys
from google import genai
from dotenv import load_dotenv

# SigmaFidelity™ Security: Load the .env file for local development
load_dotenv()

class GeminiClient:
    def __init__(self):
        # Mandatory: Retrieve the API Key from environment variables
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not found in environment. Per HWB-QMS-9.3 Section 3.2, check your .env file.")
            sys.exit(1)
        
        # Initialize the official Google GenAI Client
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-1.5-flash"

    def generate_content(self, prompt, context="HWB Cleaning Services LLC | SigmaFidelity™ Protocol"):
        """Generates high-authority, brand-aligned content."""
        # Use simple string concatenation to avoid multi-line f-string issues
        full_prompt = "--- BRAND CONTEXT: " + context + " ---\n\n" + prompt
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            return "Generation Error: " + str(e)

if __name__ == "__main__":
    # Internal Audit Test: Generate a LinkedIn post about the Zero-Cost Illusion
    gemini = GeminiClient()
    test_prompt = "Write a high-authority LinkedIn post for a CEO about why the 'Zero-Cost Illusion' in janitorial services leads to long-term quality failure. Focus on ISO 9001 and SigmaFidelity™ standards."
    print("\n--- SigmaFidelity: Generative AI Test ---")
    output = gemini.generate_content(test_prompt)
    print(output)
