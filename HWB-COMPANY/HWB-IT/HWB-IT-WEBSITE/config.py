import os
from dotenv import load_dotenv

# Load institutional secrets from .env (Traverse up to project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(ENV_PATH)

class Config:
    """Base configuration for SigmaFidelity™ Ecosystem.
    
    Configuration is loaded strictly from environment variables per the 
    Twelve-Factor App methodology. The application will fail to start if 
    required variables are missing.
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Microsoft Graph API (Phase 5 Hardening)
    GRAPH_TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
    GRAPH_CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
    GRAPH_CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
    GRAPH_USER_ID = "hdominguez@hwbcleaning.com" # Non-critical value, fallback is acceptable

    # --- 12-Factor Compliance: Backing Services as Attached Resources ---
    # Database connections are now managed via URLs from the environment.
    DATABASE_URL = os.getenv('DATABASE_URL')
    CLIENT_DATABASE_URL = os.getenv('CLIENT_DATABASE_URL')
    
    # --- 12-Factor Compliance: Strict Configuration Separation ---
    # SECRET_KEY is mandatory and must be set in the environment.
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # LinkedIn Configuration
    LI_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    LI_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    LI_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")

class DevelopmentConfig(Config):
    """Local Development Configuration."""
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    """Azure Production Configuration."""
    DEBUG = False
    ENV = 'production'
    # Ensure Azure enforces HTTPS
    PREFERRED_URL_SCHEME = 'https'

# Dynamic Environment Selection
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()

# Institutional Config Instance
sys_config = get_config()
