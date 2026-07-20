import os
import sys
import subprocess
from google import genai
from dotenv import load_dotenv

# SigmaFidelity™ Security: Load the .env file for local development
load_dotenv()

class AntigravityClient:
    """
    AntigravityClient provides a bridge to the Antigravity CLI (agy).
    Mandated by HWB-QMS-9.1-AGY for post-Gemini CLI decommissioning.
    """
    def __init__(self):
        # Retrieve the AV API Key from environment variables (Modern Standard)
        self.api_key = os.getenv("AV_API_KEY")
        if not self.api_key:
            # Fallback to GEMINI_API_KEY during transition phase
            self.api_key = os.getenv("GEMINI_API_KEY")

    def generate_content(self, prompt, context="HWB Cleaning Services LLC | SigmaFidelity™ Protocol"):
        """Generates high-authority content via Antigravity CLI (agy)."""
        full_prompt = f"--- BRAND CONTEXT: {context} ---\n\n{prompt}"
        
        try:
            # Execute agy --print "prompt" with automated permission handling
            # Using --dangerously-skip-permissions to ensure non-interactive flow
            result = subprocess.run(
                ["agy", "--print", full_prompt, "--dangerously-skip-permissions"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            output = result.stdout.strip()
            
            if not output:
                # Handle potential quota exhaustion or empty response
                return None # Return None to trigger legacy fallback
                
            return output
        except Exception:
            # Return None to trigger legacy fallback
            return None

class GeminiClient:
    """
    GeminiClient is the legacy entry point, now hardened with the Antigravity Bridge.
    All calls are redirected to Antigravity CLI (agy) where functional.
    """
    def __init__(self):
        # Mandatory: Retrieve the API Key from environment variables
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("ERROR: GEMINI_API_KEY not found in environment. Per HWB-QMS-9.3 Section 3.2, check your .env file.")
            sys.exit(1)
        
        # Initialize the official Google GenAI Client (Legacy Fallback)
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        
        # Initialize the Antigravity Bridge
        self.agy_bridge = AntigravityClient()

    def generate_content(self, prompt, context="HWB Cleaning Services LLC | SigmaFidelity™ Protocol"):
        """Generates high-authority, brand-aligned content."""
        
        # 1. Attempt Antigravity Handshake (Primary Engine)
        agy_output = self.agy_bridge.generate_content(prompt, context)
        if agy_output:
            return agy_output

        # 2. Fallback to Legacy GenAI SDK (Until 06/18/2026)
        full_prompt = "--- BRAND CONTEXT: " + context + " ---\n\n" + prompt
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            return "Dual-Engine Generation Error: " + str(e)

if __name__ == "__main__":
    # Internal Audit Test: Generate a LinkedIn post about the Zero-Cost Illusion
    gemini = GeminiClient()
    test_prompt = "Write a high-authority LinkedIn post for a CEO about why the 'Zero-Cost Illusion' in janitorial services leads to long-term quality failure. Focus on ISO 9001 and SigmaFidelity™ standards."
    print("\n--- SigmaFidelity: Dual-Engine AI Test (agy + SDK) ---")
    output = gemini.generate_content(test_prompt)
    print(output)
