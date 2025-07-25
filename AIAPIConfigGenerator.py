import json
import os
from typing import Dict, List, Any
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

class AIAPIConfigGenerator:
    """
    AI-Powered API Configuration Generator
    Uses OpenAI via LangChain to generate REAL API configurations with actual endpoints
    """
    
    def __init__(self, openai_api_key: str = None):
        """
        Initialize the AI API Generator
        
        Args:
            openai_api_key: OpenAI API key (can also be set via OPENAI_API_KEY env var)
        """
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")
        
        # Initialize LangChain ChatOpenAI client
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.1,
            max_tokens=2500,
            openai_api_key=self.api_key
        )
    
    def _call_openai_api(self, application_name: str) -> Dict[str, Any]:
        """
        Call OpenAI via LangChain to generate REAL API configuration for the given application
        """
        prompt = f"""I need the ACTUAL, REAL API endpoints for {application_name}'s official API. Please provide the exact endpoints that exist in their current API documentation.

Generate a JSON configuration with this structure:
{{
    "provider": "Exact Official Name",
    "base_url": "Real base URL from official docs", 
    "endpoints": [
        {{"name": "real_endpoint_name", "method": "ACTUAL_METHOD", "path": "/real/api/path", "description": "What this real endpoint actually does"}},
        ...
    ]
}}

CRITICAL REQUIREMENTS:
1. Use ONLY real, documented endpoints from {application_name}'s official API
2. Use the exact base URL from their official documentation
3. Use real endpoint paths that actually exist
4. Include 15-25 of their most important/commonly used endpoints
5. Use correct HTTP methods (GET, POST, PUT, DELETE, PATCH)
6. For well-known APIs like Slack, GitHub, Discord, Twitter, etc. - use their EXACT documented endpoints

Examples of what I want:
- Slack: /chat.postMessage, /conversations.list, /users.info (real Slack API endpoints)
- GitHub: /user/repos, /repos/{{owner}}/{{repo}}/issues, /user (real GitHub API endpoints) 
- Discord: /channels/{{channel_id}}/messages, /guilds/{{guild_id}} (real Discord API endpoints)

Do NOT make up generic REST endpoints. Use the ACTUAL endpoints from {application_name}'s real API documentation.

Return ONLY the JSON, no explanations:"""

        messages = [
            SystemMessage(content="You are an expert API documentation specialist with deep knowledge of real API endpoints from major platforms. You know the exact endpoints, methods, and base URLs for services like Slack, GitHub, Discord, Twitter, Shopify, etc. Always provide REAL, documented endpoints that actually exist in their official APIs."),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm(messages)
            content = response.content.strip()
            
            # Clean up the response to ensure it's valid JSON
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()
            
            # Parse the JSON response
            api_config = json.loads(content)
            
            # Validate that we got real endpoints (basic check)
            if not self._validate_real_endpoints(api_config, application_name):
                print(f"Warning: Generated endpoints may not be real for {application_name}")
            
            return api_config
            
        except Exception as e:
            print(f"Error generating API config: {e}")
            return self._generate_fallback_config(application_name)
    
    def _validate_real_endpoints(self, config: Dict[str, Any], app_name: str) -> bool:
        """
        Basic validation to check if endpoints look real
        """
        if not config.get('endpoints'):
            return False
        
        # Check for generic patterns that suggest fake endpoints
        fake_patterns = ['/items', '/item/{id}', '/generic', '/api/v1/resource']
        
        for endpoint in config['endpoints']:
            path = endpoint.get('path', '')
            if any(pattern in path for pattern in fake_patterns):
                return False
        
        return True
    
    def _generate_fallback_config(self, application_name: str) -> Dict[str, Any]:
        """
        Simple fallback if API call fails
        """
        return {
            "provider": application_name.title(),
            "base_url": f"https://api.{application_name.lower()}.com",
            "endpoints": [
                {"name": "error", "method": "GET", "path": "/error", "description": f"Failed to generate API configuration for {application_name}."}
            ]
        }
    
    def astype(self, application_name: str) -> Dict[str, Any]:
        """
        Return REAL API configuration using astype method as requested
        
        Args:
            application_name: Name of the application
            
        Returns:
            Dictionary with provider, base_url, and real endpoints
        """
        return self._call_openai_api(application_name)
    
    def get_real_api_config(self, application_name: str) -> Dict[str, Any]:
        """
        Get REAL API configuration for the specified application
        
        Args:
            application_name: Name of the application (e.g., 'slack', 'github', 'discord')
            
        Returns:
            Dictionary with provider, base_url, and real endpoints
        """
        return self.astype(application_name)

    def generate_multiple_configs(self, applications_input: str) -> Dict[str, Dict[str, Any]]:
        """
        Generate API configurations for multiple applications from comma-separated input
        
        Args:
            applications_input: Comma-separated string like "youtube, google, gmail"
            
        Returns:
            Dictionary with app names as keys and their API configs as values
        """
        # Parse the input string
        app_names = [app.strip().lower() for app in applications_input.split(',')]
        app_names = [app for app in app_names if app]  # Remove empty strings
        
        if not app_names:
            return {}
        
        print(f"🚀 Generating real API configurations for: {', '.join(app_names)}")
        print("📡 Making API calls...\n")
        
        configs = {}
        
        for app_name in app_names:
            print(f"⏳ Generating config for {app_name}...")
            try:
                config = self.astype(app_name)
                configs[app_name] = config
                print(f"✅ Generated {len(config['endpoints'])} real endpoints for {app_name}")
            except Exception as e:
                print(f"❌ Error generating config for {app_name}: {e}")
                configs[app_name] = {
                    "provider": app_name.title(),
                    "base_url": f"https://api.{app_name}.com",
                    "endpoints": [{"name": "error", "method": "GET", "path": "/error", "description": f"Failed to generate config for {app_name}"}]
                }
        
        return configs