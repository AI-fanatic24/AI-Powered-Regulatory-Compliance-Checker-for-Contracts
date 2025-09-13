import requests
import google.generativeai as genai
import time
import random
from typing import List, Dict, Optional, Union
from config import (
    GROQ_API_KEY, GEMINI_API_KEY, GROQ_BASE_URL,
    GROQ_MODELS, GEMINI_MODELS, DEFAULT_GROQ_MODEL, DEFAULT_GEMINI_MODEL,
    FALLBACK_CONFIG, REQUEST_CONFIGS, MODEL_CATEGORIES,
    get_model_by_name, get_models_by_category, get_best_model_for_tokens,
    validate_api_keys
)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class ModelRotator:
    """Handles model selection, rotation, and failure tracking"""
    
    def __init__(self):
        self.failed_models = {}  # model_name -> failure_timestamp
        self.model_usage_count = {}
        self.last_reset_time = time.time()
        
    def is_model_available(self, provider: str, model_name: str) -> bool:
        """Check if a model is currently available (not in cooldown)"""
        full_name = f"{provider}:{model_name}"
        if full_name not in self.failed_models:
            return True
        
        failure_time = self.failed_models[full_name]
        cooldown_period = FALLBACK_CONFIG["model_failure_cooldown"]
        
        if time.time() - failure_time > cooldown_period:
            # Remove from failed list after cooldown
            del self.failed_models[full_name]
            return True
        
        return False
    
    def mark_model_failed(self, provider: str, model_name: str):
        """Mark a model as failed with timestamp"""
        full_name = f"{provider}:{model_name}"
        self.failed_models[full_name] = time.time()
        print(f"⚠️ Marking {full_name} as failed (cooldown: {FALLBACK_CONFIG['model_failure_cooldown']}s)")
    
    def get_available_models(self, provider: str) -> List[Dict]:
        """Get available models for a provider, excluding failed ones"""
        if provider.lower() == "groq":
            models = GROQ_MODELS
        elif provider.lower() == "gemini":
            models = GEMINI_MODELS
        else:
            return []
        
        available = []
        for model in models:
            if self.is_model_available(provider, model["name"]):
                available.append({"provider": provider, **model})
        
        return sorted(available, key=lambda x: x["priority"])
    
    def get_best_available_model(self, provider: str, category: str = None, 
                                min_tokens: int = 0) -> Optional[Dict]:
        """Get the best available model based on criteria"""
        if category:
            models = get_models_by_category(category, provider)
        else:
            models = self.get_available_models(provider)
        
        # Filter by availability and token requirements
        suitable = []
        for model in models:
            if (self.is_model_available(model["provider"], model["name"]) and
                model.get("context_window", 0) >= min_tokens):
                suitable.append(model)
        
        return suitable[0] if suitable else None

# Global model rotator instance
model_rotator = ModelRotator()

def call_groq(prompt: str, model: str = None, request_config: Dict = None, 
              max_retries: int = None) -> str:
    """
    Call Groq REST API with enhanced configuration and error handling.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in environment variables")
    
    # Use default retry count from config if not specified
    if max_retries is None:
        max_retries = FALLBACK_CONFIG["max_retries_per_model"]
    
    # Auto-select model if not specified
    if not model:
        best_model = model_rotator.get_best_available_model("groq")
        if not best_model:
            raise Exception("No available Groq models")
        model = best_model["name"]
        print(f"🎯 Auto-selected Groq model: {model}")
    
    # Get model configuration
    model_config = get_model_by_name(model, "groq")
    if not model_config:
        raise ValueError(f"Unknown Groq model: {model}")
    
    # Use provided request config or default analytical config
    if request_config is None:
        request_config = REQUEST_CONFIGS["analytical"]
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Ensure max_tokens doesn't exceed model limit
    max_tokens = min(
        request_config.get("max_tokens", 4000),
        model_config["max_tokens"]
    )
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": request_config.get("temperature", 0.1),
        "max_tokens": max_tokens,
    }
    
    # Add optional parameters if they exist in request_config
    if "top_p" in request_config:
        payload["top_p"] = request_config["top_p"]
    
    for attempt in range(max_retries):
        try:
            print(f"🤖 Calling Groq model: {model} (attempt {attempt + 1}/{max_retries})")
            
            resp = requests.post(GROQ_BASE_URL, headers=headers, json=payload, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                if 'choices' in data and len(data['choices']) > 0:
                    content = data["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content.strip()
                    else:
                        raise ValueError("Empty response from Groq")
                else:
                    raise ValueError("Invalid response format from Groq")
                    
            elif resp.status_code == 429:  # Rate limit
                print(f"⏱️ Rate limited on {model}")
                model_rotator.mark_model_failed("groq", model)
                raise Exception(f"Rate limited: {model}")
                
            elif resp.status_code == 400:  # Bad request (context too long, etc.)
                print(f"❌ Bad request for {model}: {resp.text}")
                raise Exception(f"Bad request for model {model}: {resp.text}")
                
            else:
                print(f"❌ Groq API Error: {resp.status_code} - {resp.text}")
                if attempt == max_retries - 1:
                    resp.raise_for_status()
                
                delay = min(
                    FALLBACK_CONFIG["retry_delay_base"] * (2 ** attempt),
                    FALLBACK_CONFIG["max_retry_delay"]
                )
                time.sleep(delay)
                
        except requests.exceptions.Timeout:
            print(f"⏱️ Groq request timed out (attempt {attempt + 1})")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Groq request error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2)
    
    # Mark model as failed and raise exception
    model_rotator.mark_model_failed("groq", model)
    raise Exception(f"Groq model {model} failed after all retries")

def call_gemini(prompt: str, model: str = None, request_config: Dict = None, 
                max_retries: int = None) -> str:
    """
    Call Gemini API with enhanced configuration and error handling.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in environment variables")
    
    # Use default retry count from config if not specified
    if max_retries is None:
        max_retries = FALLBACK_CONFIG["max_retries_per_model"]
    
    # Auto-select model if not specified
    if not model:
        best_model = model_rotator.get_best_available_model("gemini")
        if not best_model:
            raise Exception("No available Gemini models")
        model = best_model["name"]
        print(f"🎯 Auto-selected Gemini model: {model}")
    
    # Get model configuration
    model_config = get_model_by_name(model, "gemini")
    if not model_config:
        raise ValueError(f"Unknown Gemini model: {model}")
    
    # Use provided request config or default analytical config
    if request_config is None:
        request_config = REQUEST_CONFIGS["analytical"]
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Calling Gemini model: {model} (attempt {attempt + 1}/{max_retries})")
            
            max_tokens = min(
                request_config.get("max_tokens", 4000),
                model_config["max_tokens"]
            )
            
            generation_config = genai.types.GenerationConfig(
                temperature=request_config.get("temperature", 0.1),
                max_output_tokens=max_tokens,
            )
            
            # Add top_p if specified
            if "top_p" in request_config:
                generation_config.top_p = request_config["top_p"]
            
            gemini_model = genai.GenerativeModel(model)
            response = gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            if response and response.text and response.text.strip():
                return response.text.strip()
            else:
                raise ValueError("Empty response from Gemini")
                
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for quota/rate limit errors
            if any(keyword in error_str for keyword in ["quota", "rate", "limit", "429"]):
                print(f"🚫 Quota/Rate limit hit on {model}")
                model_rotator.mark_model_failed("gemini", model)
                raise Exception(f"Rate/Quota limited: {model}")
            
            # Check for context length errors
            if any(keyword in error_str for keyword in ["context", "length", "token"]):
                print(f"📏 Context length exceeded for {model}")
                raise Exception(f"Context too long for {model}")
            
            print(f"❌ Gemini error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                model_rotator.mark_model_failed("gemini", model)
                raise Exception(f"Gemini model {model} error: {str(e)}")
            
            delay = min(
                FALLBACK_CONFIG["retry_delay_base"] * (2 ** attempt),
                FALLBACK_CONFIG["max_retry_delay"]
            )
            time.sleep(delay)
    
    model_rotator.mark_model_failed("gemini", model)
    raise Exception(f"Gemini model {model} failed after all retries")

def call_llm_with_fallback(prompt: str, 
                          preferred_provider: str = None,
                          model_category: str = "balanced",
                          request_type: str = "analytical",
                          specific_model: str = None,
                          min_tokens: int = 0) -> Dict:
    """
    Advanced LLM calling with intelligent model selection and fallback.
    
    Args:
        prompt: The input prompt
        preferred_provider: "groq" or "gemini" (uses config default if None)
        model_category: "fast", "balanced", "high_capacity", "cost_effective"
        request_type: "creative", "analytical", "balanced", "long_form"
        specific_model: Specific model name to use
        min_tokens: Minimum context window required
    
    Returns:
        Dict with response, model used, and metadata
    """
    if not prompt or not prompt.strip():
        raise ValueError("Empty prompt provided")
    
    # Validate API keys
    validate_api_keys()
    
    # Set preferred provider from config if not specified
    if preferred_provider is None:
        preferred_provider = FALLBACK_CONFIG["preferred_provider"]
    
    # Get request configuration
    request_config = REQUEST_CONFIGS.get(request_type, REQUEST_CONFIGS["analytical"])
    
    print(f"🚀 Starting LLM call - Provider: {preferred_provider}, Category: {model_category}, Type: {request_type}")
    
    # If specific model is requested, try it first
    if specific_model:
        model_config = get_model_by_name(specific_model)
        if model_config:
            provider = model_config["provider"]
            try:
                if provider == "groq":
                    response = call_groq(prompt, specific_model, request_config)
                else:
                    response = call_gemini(prompt, specific_model, request_config)
                
                return {
                    "response": response,
                    "model_used": specific_model,
                    "provider_used": provider,
                    "attempts": 1,
                    "fallback_used": False
                }
            except Exception as e:
                print(f"⚠️ Specific model {specific_model} failed: {e}")
    
    # Try preferred provider first
    providers_to_try = [preferred_provider]
    if FALLBACK_CONFIG["cross_provider_fallback"]:
        other_provider = "gemini" if preferred_provider == "groq" else "groq"
        providers_to_try.append(other_provider)
    
    total_attempts = 0
    
    for provider in providers_to_try:
        # Skip if provider not available
        if provider == "groq" and not GROQ_API_KEY:
            continue
        if provider == "gemini" and not GEMINI_API_KEY:
            continue
        
        # Get available models for this provider in the specified category
        available_models = model_rotator.get_available_models(provider)
        
        # Filter by category if specified
        if model_category and model_category != "all":
            category_models = get_models_by_category(model_category, provider)
            available_models = [m for m in available_models if any(
                cm["name"] == m["name"] for cm in category_models
            )]
        
        # Filter by minimum token requirements
        if min_tokens > 0:
            available_models = [m for m in available_models 
                              if m.get("context_window", 0) >= min_tokens]
        
        print(f"📋 Available {provider} models: {[m['name'] for m in available_models]}")
        
        # Try each available model for this provider
        for model_config in available_models:
            try:
                total_attempts += 1
                model_name = model_config["name"]
                print(f"🔄 Trying {provider} model: {model_name}")
                
                if provider == "groq":
                    response = call_groq(prompt, model_name, request_config)
                else:
                    response = call_gemini(prompt, model_name, request_config)
                
                return {
                    "response": response,
                    "model_used": model_name,
                    "provider_used": provider,
                    "attempts": total_attempts,
                    "fallback_used": provider != preferred_provider
                }
                
            except Exception as model_error:
                print(f"❌ {model_name} failed: {model_error}")
                continue
    
    # All models failed
    raise Exception(f"All available models failed after {total_attempts} attempts")

def get_model_status() -> Dict:
    """Get comprehensive status of all models and providers"""
    status = {
        "providers": {
            "groq": {
                "available": bool(GROQ_API_KEY),
                "total_models": len(GROQ_MODELS),
                "available_models": len(model_rotator.get_available_models("groq")),
                "models": model_rotator.get_available_models("groq")
            },
            "gemini": {
                "available": bool(GEMINI_API_KEY),
                "total_models": len(GEMINI_MODELS),
                "available_models": len(model_rotator.get_available_models("gemini")),
                "models": model_rotator.get_available_models("gemini")
            }
        },
        "failed_models": {
            model_name: {
                "failed_at": timestamp,
                "cooldown_remaining": max(0, FALLBACK_CONFIG["model_failure_cooldown"] - (time.time() - timestamp))
            }
            for model_name, timestamp in model_rotator.failed_models.items()
        },
        "config": FALLBACK_CONFIG
    }
    
    return status

def reset_model_failures():
    """Reset all model failure tracking"""
    model_rotator.failed_models.clear()
    model_rotator.model_usage_count.clear()
    print("✅ All model failures reset")

# Backward Compatibility Functions - EXACT same interface as original
def call_llm_with_fallback(prompt: str, groq_model: str = None, gemini_model: str = None) -> str:
    """
    Original function signature - maintains exact compatibility.
    Call LLM with Groq as primary and Gemini as fallback.
    
    Args:
        prompt: The input prompt
        groq_model: Specific Groq model (optional) 
        gemini_model: Specific Gemini model (optional)
    
    Returns:
        Response string (same as original)
    """
    if not prompt or not prompt.strip():
        raise ValueError("Empty prompt provided")
    
    # Try Groq first (same logic as original)
    try:
        return call_groq(prompt, groq_model)
    except Exception as groq_error:
        print(f"⚠️ Groq failed: {groq_error}")
        
        # Try Gemini as fallback (same logic as original) 
        if GEMINI_API_KEY:
            print("🔄 Attempting Gemini fallback...")
            try:
                return call_gemini(prompt, gemini_model)
            except Exception as gemini_error:
                print(f"❌ Gemini also failed: {gemini_error}")
                raise Exception(f"Both LLMs failed. Groq: {groq_error}, Gemini: {gemini_error}")
        else:
            print("❌ No Gemini API key available for fallback")
            raise Exception(f"Groq failed and no fallback available: {groq_error}")

# New enhanced function with different name to avoid conflicts
def call_llm_smart(prompt: str, 
                   preferred_provider: str = None,
                   model_category: str = "balanced", 
                   request_type: str = "analytical",
                   specific_model: str = None,
                   min_tokens: int = 0) -> Dict:
    """
    NEW enhanced LLM calling with intelligent model selection and fallback.
    Use this for new code that wants the enhanced features.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Empty prompt provided")
    
    # Validate API keys
    validate_api_keys()
    
    # Set preferred provider from config if not specified
    if preferred_provider is None:
        preferred_provider = FALLBACK_CONFIG["preferred_provider"]
    
    # Get request configuration
    request_config = REQUEST_CONFIGS.get(request_type, REQUEST_CONFIGS["analytical"])
    
    print(f"🚀 Starting enhanced LLM call - Provider: {preferred_provider}, Category: {model_category}")
    
    # If specific model is requested, try it first
    if specific_model:
        model_config = get_model_by_name(specific_model)
        if model_config:
            provider = model_config["provider"]
            try:
                if provider == "groq":
                    response = call_groq(prompt, specific_model, request_config)
                else:
                    response = call_gemini(prompt, specific_model, request_config)
                
                return {
                    "response": response,
                    "model_used": specific_model,
                    "provider_used": provider,
                    "attempts": 1,
                    "fallback_used": False
                }
            except Exception as e:
                print(f"⚠️ Specific model {specific_model} failed: {e}")
    
    # Try preferred provider first
    providers_to_try = [preferred_provider]
    if FALLBACK_CONFIG["cross_provider_fallback"]:
        other_provider = "gemini" if preferred_provider == "groq" else "groq"
        providers_to_try.append(other_provider)
    
    total_attempts = 0
    
    for provider in providers_to_try:
        # Skip if provider not available
        if provider == "groq" and not GROQ_API_KEY:
            continue
        if provider == "gemini" and not GEMINI_API_KEY:
            continue
        
        # Get available models for this provider
        available_models = model_rotator.get_available_models(provider)
        
        # Filter by category if specified
        if model_category and model_category != "all":
            category_models = get_models_by_category(model_category, provider)
            available_models = [m for m in available_models if any(
                cm["name"] == m["name"] for cm in category_models
            )]
        
        # Filter by minimum token requirements
        if min_tokens > 0:
            available_models = [m for m in available_models 
                              if m.get("context_window", 0) >= min_tokens]
        
        # Try each available model for this provider
        for model_config in available_models:
            try:
                total_attempts += 1
                model_name = model_config["name"]
                print(f"🔄 Trying {provider} model: {model_name}")
                
                if provider == "groq":
                    response = call_groq(prompt, model_name, request_config)
                else:
                    response = call_gemini(prompt, model_name, request_config)
                
                return {
                    "response": response,
                    "model_used": model_name,
                    "provider_used": provider,
                    "attempts": total_attempts,
                    "fallback_used": provider != preferred_provider
                }
                
            except Exception as model_error:
                print(f"❌ {model_name} failed: {model_error}")
                continue
    
    # All models failed
    raise Exception(f"All available models failed after {total_attempts} attempts")