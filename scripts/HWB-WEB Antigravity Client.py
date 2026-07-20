import os
import sys
import subprocess
from dotenv import load_dotenv

# SigmaFidelity™ Security: Load the .env file for local development
load_dotenv()

class AntigravityClient:
    """
    AntigravityClient provides a bridge to the Antigravity CLI (agy).
    Mandated by HWB-QMS-9.1-AGY for post-Gemini CLI decommissioning.
    """
    def __init__(self):
        # Retrieve the AV API Key from environment variables
        self.api_key = os.getenv("AV_API_KEY")
        if not self.api_key:
            # Fallback to GEMINI_API_KEY during transition phase
            self.api_key = os.getenv("GEMINI_API_KEY")
            
        # Verify agy binary is available in PATH
        try:
            subprocess.run(["agy", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("WARNING: Antigravity CLI (agy) not found in PATH.")

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
                return "Antigravity Error: Received empty response from CLI. Check 'agy' logs or quota status."
                
            return output
        except subprocess.CalledProcessError as e:
            return f"Antigravity Execution Error: {e.stderr if e.stderr else str(e)}"
        except Exception as e:
            return f"Unexpected Bridge Error: {str(e)}"

if __name__ == "__main__":
    client = AntigravityClient()
    test_prompt = "Generate a 1-sentence verification of the Antigravity bridge."
    print("\n--- SigmaFidelity: Antigravity CLI Bridge Test ---")
    output = client.generate_content(test_prompt)
    print(output)
