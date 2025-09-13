import os
from dotenv import load_dotenv

load_dotenv()

# API Keys and Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 130000))

# Groq API Configuration
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Available Groq Models Configuration
GROQ_MODELS = [
    {
        "name": "llama-3.3-70b-versatile",
        "max_tokens": 32768,
        "priority": 1,
        "description": "Llama 3.3 70B - Most capable, good for complex tasks",
        "rate_limit_per_minute": 30,
        "context_window": 32768
    },
    {
        "name": "llama-3.1-8b-instant",
        "max_tokens": 131072,
        "priority": 2,
        "description": "Llama 3.1 8B - Fast and efficient",
        "rate_limit_per_minute": 100,
        "context_window": 131072
    },
    {
        "name": "llama-3.1-70b-versatile",
        "max_tokens": 131072,
        "priority": 3,
        "description": "Llama 3.1 70B - High capability with large context",
        "rate_limit_per_minute": 30,
        "context_window": 131072
    },
    {
        "name": "llama-3.2-1b-preview",
        "max_tokens": 8192,
        "priority": 4,
        "description": "Llama 3.2 1B - Ultra fast, lightweight",
        "rate_limit_per_minute": 200,
        "context_window": 8192
    },
    {
        "name": "llama-3.2-3b-preview",
        "max_tokens": 8192,
        "priority": 5,
        "description": "Llama 3.2 3B - Fast with good performance",
        "rate_limit_per_minute": 150,
        "context_window": 8192
    },
    {
        "name": "mixtral-8x7b-32768",
        "max_tokens": 32768,
        "priority": 6,
        "description": "Mixtral 8x7B - Good balance of speed and capability",
        "rate_limit_per_minute": 30,
        "context_window": 32768
    },
    {
        "name": "gemma-7b-it",
        "max_tokens": 8192,
        "priority": 7,
        "description": "Gemma 7B - Google's efficient model",
        "rate_limit_per_minute": 60,
        "context_window": 8192
    },
    {
        "name": "gemma2-9b-it",
        "max_tokens": 8192,
        "priority": 8,
        "description": "Gemma 2 9B - Updated Google model",
        "rate_limit_per_minute": 60,
        "context_window": 8192
    }
]

# Available Gemini Models Configuration
GEMINI_MODELS = [
    {
        "name": "gemini-1.5-pro",
        "max_tokens": 8192,
        "priority": 1,
        "description": "Gemini 1.5 Pro - Most capable Gemini model",
        "rate_limit_per_minute": 2,
        "context_window": 2097152  # 2M tokens
    },
    {
        "name": "gemini-1.5-flash",
        "max_tokens": 8192,
        "priority": 2,
        "description": "Gemini 1.5 Flash - Fast and efficient",
        "rate_limit_per_minute": 15,
        "context_window": 1048576  # 1M tokens
    },
    {
        "name": "gemini-1.5-flash-8b",
        "max_tokens": 8192,
        "priority": 3,
        "description": "Gemini 1.5 Flash 8B - Ultra fast",
        "rate_limit_per_minute": 100,
        "context_window": 1048576  # 1M tokens
    },
    {
        "name": "gemini-1.0-pro",
        "max_tokens": 8192,
        "priority": 4,
        "description": "Gemini 1.0 Pro - Stable and reliable",
        "rate_limit_per_minute": 60,
        "context_window": 32768
    }
]

# Default Model Selection Strategy
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"

# Fallback Strategy Configuration
FALLBACK_CONFIG = {
    "max_retries_per_model": 2,
    "retry_delay_base": 1,  # Base delay in seconds for exponential backoff
    "max_retry_delay": 60,  # Maximum retry delay in seconds
    "model_failure_cooldown": 3600,  # How long to avoid a failed model (1 hour)
    "cross_provider_fallback": True,  # Allow switching between Groq and Gemini
    "preferred_provider": "groq",  # Primary provider to try first
}

# Model Categories for Different Use Cases
MODEL_CATEGORIES = {
    "fast": {
        "groq": ["llama-3.2-1b-preview", "llama-3.2-3b-preview", "llama-3.1-8b-instant"],
        "gemini": ["gemini-1.5-flash-8b", "gemini-1.5-flash"]
    },
    "balanced": {
        "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "gemini": ["gemini-1.5-flash", "gemini-1.0-pro"]
    },
    "high_capacity": {
        "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"]
    },
    "cost_effective": {
        "groq": ["llama-3.2-1b-preview", "gemma-7b-it", "gemma2-9b-it"],
        "gemini": ["gemini-1.5-flash-8b", "gemini-1.0-pro"]
    }
}

# Request Configuration Templates
REQUEST_CONFIGS = {
    "creative": {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 4000
    },
    "analytical": {
        "temperature": 0.1,
        "top_p": 0.1,
        "max_tokens": 4000
    },
    "balanced": {
        "temperature": 0.3,
        "top_p": 0.5,
        "max_tokens": 4000
    },
    "long_form": {
        "temperature": 0.4,
        "top_p": 0.6,
        "max_tokens": 8000
    }
}

# Utility Functions for Configuration
def get_model_by_name(model_name: str, provider: str = None):
    """Get model configuration by name"""
    if provider == "groq" or provider is None:
        for model in GROQ_MODELS:
            if model["name"] == model_name:
                return {"provider": "groq", **model}
    
    if provider == "gemini" or provider is None:
        for model in GEMINI_MODELS:
            if model["name"] == model_name:
                return {"provider": "gemini", **model}
    
    return None

def get_models_by_category(category: str, provider: str = None):
    """Get models filtered by category and optionally by provider"""
    if category not in MODEL_CATEGORIES:
        return []
    
    result = []
    category_models = MODEL_CATEGORIES[category]
    
    if provider is None or provider == "groq":
        for model_name in category_models.get("groq", []):
            model_config = get_model_by_name(model_name, "groq")
            if model_config:
                result.append(model_config)
    
    if provider is None or provider == "gemini":
        for model_name in category_models.get("gemini", []):
            model_config = get_model_by_name(model_name, "gemini")
            if model_config:
                result.append(model_config)
    
    return sorted(result, key=lambda x: x["priority"])

def get_best_model_for_tokens(required_tokens: int, provider: str = None):
    """Get the best model that can handle the required token count"""
    all_models = []
    
    if provider is None or provider == "groq":
        all_models.extend([{"provider": "groq", **model} for model in GROQ_MODELS])
    
    if provider is None or provider == "gemini":
        all_models.extend([{"provider": "gemini", **model} for model in GEMINI_MODELS])
    
    # Filter models that can handle the required tokens
    suitable_models = [
        model for model in all_models 
        if model["context_window"] >= required_tokens
    ]
    
    if suitable_models:
        return min(suitable_models, key=lambda x: x["priority"])
    
    return None

def validate_api_keys():
    """Check if required API keys are available"""
    status = {
        "groq_available": bool(GROQ_API_KEY),
        "gemini_available": bool(GEMINI_API_KEY),
        "at_least_one_available": bool(GROQ_API_KEY or GEMINI_API_KEY)
    }
    
    if not status["at_least_one_available"]:
        raise ValueError("No API keys available. Please set GROQ_API_KEY or GEMINI_API_KEY")
    
    return status

# Model Provider Status
def get_provider_info():
    """Get information about available providers and models"""
    api_status = validate_api_keys()
    
    return {
        "providers": {
            "groq": {
                "available": api_status["groq_available"],
                "models_count": len(GROQ_MODELS),
                "default_model": DEFAULT_GROQ_MODEL
            },
            "gemini": {
                "available": api_status["gemini_available"],
                "models_count": len(GEMINI_MODELS),
                "default_model": DEFAULT_GEMINI_MODEL
            }
        },
        "total_models": len(GROQ_MODELS) + len(GEMINI_MODELS),
        "fallback_enabled": FALLBACK_CONFIG["cross_provider_fallback"],
        "preferred_provider": FALLBACK_CONFIG["preferred_provider"]
    }