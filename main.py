import json
import os
from pathlib import Path
from typing import Dict, List, Any
from langchain.agents import AgentExecutor, Tool, initialize_agent
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import MessagesPlaceholder
from langchain.agents import AgentType

class APIGeneratorAgent:
    """
    Agent-based API Generator with memory and interactive capabilities
    """
    
    def __init__(self, openai_api_key: str = None):
        """
        Initialize the API Generator Agent
        
        Args:
            openai_api_key: OpenAI API key (can also be set via OPENAI_API_KEY env var)
        """
        self.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it directly.")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.1,
            max_tokens=2500,
            openai_api_key=self.api_key
        )
        
        # Set up tools
        self.tools = [
            Tool(
                name="api_config_generator",
                func=self._generate_api_config,
                description="Generates real API configurations for given applications. Input should be a comma-separated list of application names."
            ),
            Tool(
                name="save_configurations",
                func=self._save_configurations,
                description="Saves generated API configurations to files. Input should be a JSON string of configurations."
            )
        ]
        
        # Initialize agent
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
        )
    
    def _generate_api_config(self, applications_input: str) -> Dict[str, Dict[str, Any]]:
        """
        Generate API configurations for multiple applications
        """
        app_names = [app.strip().lower() for app in applications_input.split(',')]
        app_names = [app for app in app_names if app]
        
        if not app_names:
            return {}
        
        configs = {}
        
        for app_name in app_names:
            config = self._call_openai_api(app_name)
            configs[app_name] = config
        
        return configs
    
    def _call_openai_api(self, application_name: str) -> Dict[str, Any]:
        """
        Call OpenAI to generate API configuration
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
4. Include 5-10 of their most important/commonly used endpoints
5. Use correct HTTP methods (GET, POST, PUT, DELETE, PATCH)
6. For well-known APIs like Slack, GitHub, Discord, Twitter, etc. - use their EXACT documented endpoints

Return ONLY the JSON, no explanations:"""

        messages = [
            SystemMessage(content="You are an expert API documentation specialist with deep knowledge of real API endpoints from major platforms."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm(messages)
        content = response.content.strip()
        
        if content.startswith('```json'):
            content = content.replace('```json', '').replace('```', '').strip()
        elif content.startswith('```'):
            content = content.replace('```', '').strip()
        
        return json.loads(content)
    
    def _save_configurations(self, configs_json: str) -> str:
        """
        Save configurations to files
        """
        try:
            configs = json.loads(configs_json)
            self._generate_files(configs)
            return "Successfully saved all API configurations to files."
        except Exception as e:
            return f"Error saving configurations: {str(e)}"
    
    def _generate_files(self, configs: Dict[str, Dict[str, Any]]) -> None:
        """
        Generate Python files, requirements.txt, and README for each API
        """
        base_dir = Path("generated")
        base_dir.mkdir(exist_ok=True)
        
        for app_name, config in configs.items():
            app_dir = base_dir / app_name
            app_dir.mkdir(exist_ok=True)
            
            # Generate Python client file
            self._generate_python_client(app_dir, app_name, config)
            
            # Generate requirements.txt
            self._generate_requirements(app_dir)
            
            # Generate README
            self._generate_readme(app_dir, app_name, config)
    
    def _generate_python_client(self, app_dir: Path, app_name: str, config: Dict[str, Any]) -> None:
        """
        Generate Python client file for the API
        """
        endpoint_methods = []
        
        for endpoint in config['endpoints']:
            method_name = endpoint['name'].replace('.', '_').replace('-', '_')
            docstring = f"    \"\"\"\n    {endpoint['description']}\n    "
            
            if '{' in endpoint['path']:
                # Handle path parameters
                path_parts = endpoint['path'].split('/')
                params = []
                for part in path_parts:
                    if part.startswith('{') and part.endswith('}'):
                        param = part[1:-1]
                        params.append(param)
                
                params_str = ', '.join(params)
                method_def = f"def {method_name}(self, {params_str}):"
                path_str = endpoint['path']
                for param in params:
                    path_str = path_str.replace(f'{{{param}}}', f'{{{param}}}')
                
                endpoint_code = f"""
{method_def}
{docstring}
    \"\"\"
    url = f\"{config['base_url']}{path_str}\"
    response = requests.{endpoint['method'].lower()}(url, headers=self.headers)
    return self._handle_response(response)
"""
            else:
                # Simple endpoint without path parameters
                method_def = f"def {method_name}(self):"
                endpoint_code = f"""
{method_def}
{docstring}
    \"\"\"
    url = \"{config['base_url']}{endpoint['path']}\"
    response = requests.{endpoint['method'].lower()}(url, headers=self.headers)
    return self._handle_response(response)
"""
            
            endpoint_methods.append(endpoint_code)
        
        methods_str = '\n'.join(endpoint_methods)
        
        client_code = f"""import requests
import json

class {app_name.title()}Client:
    \"\"\"
    Python client for {config['provider']} API
    \"\"\"
    
    def __init__(self, api_key=None):
        self.base_url = \"{config['base_url']}\"
        self.headers = {{
            \"Content-Type\": \"application/json\",
            \"Accept\": \"application/json\"
        }}
        if api_key:
            self.headers[\"Authorization\"] = f\"Bearer {{api_key}}\"
    
    def _handle_response(self, response):
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as errh:
            print(f\"Http Error: {{errh}}\")
        except requests.exceptions.ConnectionError as errc:
            print(f\"Error Connecting: {{errc}}\")
        except requests.exceptions.Timeout as errt:
            print(f\"Timeout Error: {{errt}}\")
        except requests.exceptions.RequestException as err:
            print(f\"Something went wrong: {{err}}\")
        return None

{methods_str}
"""

        with open(app_dir / f"{app_name}_client.py", "w") as f:
            f.write(client_code)
    
    def _generate_requirements(self, app_dir: Path) -> None:
        """
        Generate requirements.txt file
        """
        requirements = """requests>=2.28.1
python-dotenv>=0.21.0
"""
        with open(app_dir / "requirements.txt", "w") as f:
            f.write(requirements)
    
    def _generate_readme(self, app_dir: Path, app_name: str, config: Dict[str, Any]) -> None:
        """
        Generate README.md file
        """
        endpoints_table = "| Endpoint | Method | Path | Description |\n"
        endpoints_table += "|----------|--------|------|-------------|\n"
        
        for endpoint in config['endpoints']:
            endpoints_table += f"| {endpoint['name']} | {endpoint['method']} | `{endpoint['path']}` | {endpoint['description']} |\n"
        
        readme_content = f"""# {config['provider']} API Client

## Overview
Python client for interacting with the {config['provider']} API.

## Installation
1. Clone this repository
2. Install requirements:
```bash
pip install -r requirements.txt
Usage
python
from {app_name}_client import {app_name.title()}Client

# Initialize client with your API key
client = {app_name.title()}Client(api_key="your_api_key_here")

# Example API call
response = client.example_endpoint()
print(response)
Available Endpoints
{endpoints_table}

Authentication
Most endpoints require an API key. Pass it when initializing the client.
"""

        with open(app_dir / "README.md", "w") as f:
            f.write(readme_content)

    def run(self):
        """
        Run the agent in interactive mode
        """
        print("="*50)
        print("🌟 API Generator Agent 🌟")
        print("I can generate Python clients for real APIs. What would you like to do?")
        print("Examples:")
        print("- Generate API clients for youtube, slack, github")
        print("- Save the configurations")
        print("- Exit")
        
        while True:
            user_input = input("\nYou: ").strip()

            apps = user_input.split(", ")
            
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
            for app in apps:
                try:
                    response = self.agent.invoke(app)
                    print(f"\nAgent: {response}")
                except Exception as e:
                    print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Initialize the agent
    agent = APIGeneratorAgent()

    # Run the agent interactively
    agent.run()