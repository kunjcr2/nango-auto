#!/usr/bin/env python3
"""
Integration Automation Agent
Automates the creation of API integrations using Nango for OAuth management
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from datetime import datetime

# LangChain imports
from langchain_community.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import BaseOutputParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for an API integration"""
    name: str
    provider: str
    client_id: str
    client_secret: str
    scopes: List[str]
    base_url: str
    auth_url: str
    token_url: str
    endpoints: List[Dict[str, Any]]
    webhook_url: Optional[str] = None

@dataclass
class GeneratedIntegration:
    """Result of generated integration"""
    config: IntegrationConfig
    client_code: str
    server_code: str
    middleware_code: str
    usage_examples: str

class NangoClient:
    """Client for interacting with Nango API"""
    
    def __init__(self, nango_secret_key: str, nango_public_key: str, base_url: str = "https://api.nango.dev"):
        self.secret_key = nango_secret_key
        self.public_key = nango_public_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def create_integration(self, integration_config: IntegrationConfig) -> Dict[str, Any]:
        """Create an integration in Nango"""
        payload = {
            "unique_key": integration_config.name.lower().replace(" ", "_"),
            "provider": integration_config.provider.lower(),
            "client_id": integration_config.client_id,
            "client_secret": integration_config.client_secret,
            "scopes": integration_config.scopes,
            "auth_mode": "OAUTH2",
            "oauth_client_id": integration_config.client_id,
            "oauth_client_secret": integration_config.client_secret,
            "oauth_scopes": integration_config.scopes
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/config",
                headers=self.headers,
                json=payload
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    logger.info(f"Successfully created integration: {integration_config.name}")
                    return result
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to create integration: {error_text}")
    
    async def get_connection(self, connection_id: str, provider_config_key: str) -> Dict[str, Any]:
        """Get connection details from Nango"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/connection/{connection_id}",
                headers={**self.headers, "Provider-Config-Key": provider_config_key}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to get connection: {error_text}")

class CodeGenerator:
    """Generates integration code using LangChain"""
    
    def __init__(self, openai_api_key: str):
        self.llm = OpenAI(
            api_key=openai_api_key,
            temperature=0.1,
            max_tokens=2000
        )
        
        # Prompt templates for different code generation tasks
        self.client_template = PromptTemplate(
            input_variables=["integration_name", "provider", "endpoints", "base_url"],
            template="""
Generate a PYTHON client class for {integration_name} integration with {provider}.

Requirements:
- Use async/await patterns
- Include proper error handling
- Base URL: {base_url}
- Available endpoints: {endpoints}
- Use Nango for token management
- Include rate limiting
- Add comprehensive docstrings

Generate a complete, production-ready client class.
"""
        )
        
        self.server_template = PromptTemplate(
            input_variables=["integration_name", "provider", "endpoints"],
            template="""
Generate a FLASK server in PYTHON with endpoints for {integration_name} integration with {provider}.

Requirements:
- Flask framework
- Async endpoints
- Error handling middleware
- Nango integration for OAuth
- Available endpoints to proxy: {endpoints}
- Include health check endpoint
- Add request/response models with Pydantic
- Include CORS middleware

Generate complete server code with all routes.
"""
        )
        
        self.middleware_template = PromptTemplate(
            input_variables=["integration_name", "provider"],
            template="""
Generate middleware code in PYTHON for {integration_name} with {provider} that handles:

Requirements:
- Token refresh logic using Nango
- Rate limiting
- Request/response logging
- Error handling and retries
- Connection pooling
- Health checks

Generate production-ready middleware.
"""
        )
        
        self.usage_template = PromptTemplate(
            input_variables=["integration_name", "provider", "endpoints"],
            template="""
Generate comprehensive usage examples in PYTHON for {integration_name} integration with {provider}.

Include:
- Basic setup and initialization
- Authentication flow
- Examples for each endpoint: {endpoints}
- Error handling examples
- Best practices
- Common use cases

Provide clear, commented examples.
"""
        )
    
    async def generate_client_code(self, config: IntegrationConfig) -> str:
        """Generate client code for the integration"""
        chain = LLMChain(llm=self.llm, prompt=self.client_template)
        result = await chain.arun(
            integration_name=config.name,
            provider=config.provider,
            endpoints=json.dumps(config.endpoints, indent=2),
            base_url=config.base_url
        )
        return result
    
    async def generate_server_code(self, config: IntegrationConfig) -> str:
        """Generate server code for the integration"""
        chain = LLMChain(llm=self.llm, prompt=self.server_template)
        result = await chain.arun(
            integration_name=config.name,
            provider=config.provider,
            endpoints=json.dumps(config.endpoints, indent=2)
        )
        return result
    
    async def generate_middleware_code(self, config: IntegrationConfig) -> str:
        """Generate middleware code for the integration"""
        chain = LLMChain(llm=self.llm, prompt=self.middleware_template)
        result = await chain.arun(
            integration_name=config.name,
            provider=config.provider
        )
        return result
    
    async def generate_usage_examples(self, config: IntegrationConfig) -> str:
        """Generate usage examples for the integration"""
        chain = LLMChain(llm=self.llm, prompt=self.usage_template)
        result = await chain.arun(
            integration_name=config.name,
            provider=config.provider,
            endpoints=json.dumps(config.endpoints, indent=2)
        )
        return result

class IntegrationAgent:
    """Main agent class that orchestrates the integration automation"""
    
    # Predefined configurations for 10 popular APIs
    SUPPORTED_INTEGRATIONS = {
        "slack": {
            "provider": "slack",
            "base_url": "https://slack.com/api",
            "auth_url": "https://slack.com/oauth/v2/authorize",
            "token_url": "https://slack.com/api/oauth.v2.access",
            "scopes": ["chat:write", "channels:read", "users:read"],
            "endpoints": [
                {"name": "send_message", "method": "POST", "path": "/chat.postMessage"},
                {"name": "list_channels", "method": "GET", "path": "/conversations.list"},
                {"name": "get_user_info", "method": "GET", "path": "/users.info"}
            ]
        },
        "github": {
            "provider": "github",
            "base_url": "https://api.github.com",
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "scopes": ["repo", "user"],
            "endpoints": [
                {"name": "list_repos", "method": "GET", "path": "/user/repos"},
                {"name": "create_issue", "method": "POST", "path": "/repos/{owner}/{repo}/issues"},
                {"name": "get_user", "method": "GET", "path": "/user"}
            ]
        },
        "google_drive": {
            "provider": "google-drive",
            "base_url": "https://www.googleapis.com/drive/v3",
            "auth_url": "https://accounts.google.com/o/oauth2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "scopes": ["https://www.googleapis.com/auth/drive"],
            "endpoints": [
                {"name": "list_files", "method": "GET", "path": "/files"},
                {"name": "upload_file", "method": "POST", "path": "/files"},
                {"name": "download_file", "method": "GET", "path": "/files/{fileId}"}
            ]
        },
        "notion": {
            "provider": "notion",
            "base_url": "https://api.notion.com/v1",
            "auth_url": "https://api.notion.com/v1/oauth/authorize",
            "token_url": "https://api.notion.com/v1/oauth/token",
            "scopes": ["read", "update"],
            "endpoints": [
                {"name": "list_databases", "method": "GET", "path": "/databases"},
                {"name": "query_database", "method": "POST", "path": "/databases/{database_id}/query"},
                {"name": "create_page", "method": "POST", "path": "/pages"}
            ]
        },
        "hubspot": {
            "provider": "hubspot",
            "base_url": "https://api.hubapi.com",
            "auth_url": "https://app.hubspot.com/oauth/authorize",
            "token_url": "https://api.hubapi.com/oauth/v1/token",
            "scopes": ["contacts", "content"],
            "endpoints": [
                {"name": "get_contacts", "method": "GET", "path": "/crm/v3/objects/contacts"},
                {"name": "create_contact", "method": "POST", "path": "/crm/v3/objects/contacts"},
                {"name": "get_deals", "method": "GET", "path": "/crm/v3/objects/deals"}
            ]
        },
        "salesforce": {
            "provider": "salesforce",
            "base_url": "https://your-domain.salesforce.com",
            "auth_url": "https://login.salesforce.com/services/oauth2/authorize",
            "token_url": "https://login.salesforce.com/services/oauth2/token",
            "scopes": ["api", "refresh_token"],
            "endpoints": [
                {"name": "get_accounts", "method": "GET", "path": "/services/data/v52.0/sobjects/Account"},
                {"name": "create_lead", "method": "POST", "path": "/services/data/v52.0/sobjects/Lead"},
                {"name": "get_opportunities", "method": "GET", "path": "/services/data/v52.0/sobjects/Opportunity"}
            ]
        },
        "discord": {
            "provider": "discord",
            "base_url": "https://discord.com/api/v10",
            "auth_url": "https://discord.com/api/oauth2/authorize",
            "token_url": "https://discord.com/api/oauth2/token",
            "scopes": ["bot", "messages.read"],
            "endpoints": [
                {"name": "send_message", "method": "POST", "path": "/channels/{channel_id}/messages"},
                {"name": "get_guild", "method": "GET", "path": "/guilds/{guild_id}"},
                {"name": "get_user", "method": "GET", "path": "/users/@me"}
            ]
        },
        "shopify": {
            "provider": "shopify",
            "base_url": "https://{shop}.myshopify.com/admin/api/2023-04",
            "auth_url": "https://{shop}.myshopify.com/admin/oauth/authorize",
            "token_url": "https://{shop}.myshopify.com/admin/oauth/access_token",
            "scopes": ["read_products", "write_products"],
            "endpoints": [
                {"name": "get_products", "method": "GET", "path": "/products.json"},
                {"name": "create_product", "method": "POST", "path": "/products.json"},
                {"name": "get_orders", "method": "GET", "path": "/orders.json"}
            ]
        },
        "trello": {
            "provider": "trello",
            "base_url": "https://api.trello.com/1",
            "auth_url": "https://trello.com/1/authorize",
            "token_url": "https://trello.com/1/OAuthGetAccessToken",
            "scopes": ["read", "write"],
            "endpoints": [
                {"name": "get_boards", "method": "GET", "path": "/members/me/boards"},
                {"name": "create_card", "method": "POST", "path": "/cards"},
                {"name": "get_lists", "method": "GET", "path": "/boards/{board_id}/lists"}
            ]
        },
        "airtable": {
            "provider": "airtable",
            "base_url": "https://api.airtable.com/v0",
            "auth_url": "https://airtable.com/oauth2/v1/authorize",
            "token_url": "https://airtable.com/oauth2/v1/token",
            "scopes": ["data.records:read", "data.records:write"],
            "endpoints": [
                {"name": "list_records", "method": "GET", "path": "/{base_id}/{table_name}"},
                {"name": "create_record", "method": "POST", "path": "/{base_id}/{table_name}"},
                {"name": "update_record", "method": "PATCH", "path": "/{base_id}/{table_name}/{record_id}"}
            ]
        }
    }
    
    def __init__(self, nango_secret_key: str, nango_public_key: str, openai_api_key: str):
        self.nango_client = NangoClient(nango_secret_key, nango_public_key)
        self.code_generator = CodeGenerator(openai_api_key)
        self.output_dir = Path("generated_integrations")
        self.output_dir.mkdir(exist_ok=True)
    
    def display_available_integrations(self) -> None:
        """Display available integrations to the user"""
        print("\n🚀 Available Integrations:")
        print("=" * 50)
        for i, (key, config) in enumerate(self.SUPPORTED_INTEGRATIONS.items(), 1):
            print(f"{i:2d}. {key.title().replace('_', ' ')}")
            print(f"    Provider: {config['provider']}")
            print(f"    Endpoints: {len(config['endpoints'])} available")
            print()
    
    def get_user_selection(self) -> List[str]:
        """Get user's selection of integrations"""
        self.display_available_integrations()
        
        while True:
            try:
                selection = input("\nEnter integration numbers (comma-separated, e.g., 1,3,5): ").strip()
                indices = [int(x.strip()) for x in selection.split(',')]
                
                if not all(1 <= i <= len(self.SUPPORTED_INTEGRATIONS) for i in indices):
                    print("❌ Invalid selection. Please enter valid numbers.")
                    continue
                
                selected_keys = [list(self.SUPPORTED_INTEGRATIONS.keys())[i-1] for i in indices]
                return selected_keys
                
            except ValueError:
                print("❌ Invalid input. Please enter numbers separated by commas.")
    
    def get_credentials(self, integration_name: str) -> tuple[str, str]:
        """Get credentials for a specific integration"""
        print(f"\n🔐 Enter credentials for {integration_name.title().replace('_', ' ')}:")
        client_id = input("Client ID: ").strip()
        client_secret = input("Client Secret: ").strip()
        
        if not client_id or not client_secret:
            raise ValueError("Both Client ID and Client Secret are required")
        
        return client_id, client_secret
    
    async def create_integration(self, integration_key: str, client_id: str, client_secret: str) -> GeneratedIntegration:
        """Create a complete integration"""
        template = self.SUPPORTED_INTEGRATIONS[integration_key]
        
        # Create integration configuration
        config = IntegrationConfig(
            name=integration_key.replace('_', ' ').title(),
            provider=template["provider"],
            client_id=client_id,
            client_secret=client_secret,
            scopes=template["scopes"],
            base_url=template["base_url"],
            auth_url=template["auth_url"],
            token_url=template["token_url"],
            endpoints=template["endpoints"]
        )
        
        print(f"📝 Generating code for {config.name}...")
        
        # Generate all code components concurrently
        tasks = [
            self.code_generator.generate_client_code(config),
            self.code_generator.generate_server_code(config),
            self.code_generator.generate_middleware_code(config),
            self.code_generator.generate_usage_examples(config)
        ]
        
        client_code, server_code, middleware_code, usage_examples = await asyncio.gather(*tasks)
        
        # Create integration in Nango
        print(f"🔗 Creating integration in Nango...")
        try:
            await self.nango_client.create_integration(config)
        except Exception as e:
            logger.warning(f"Failed to create Nango integration: {e}")
            print(f"⚠️ Warning: Could not create integration in Nango: {e}")
        
        return GeneratedIntegration(
            config=config,
            client_code=client_code,
            server_code=server_code,
            middleware_code=middleware_code,
            usage_examples=usage_examples
        )
    
    def save_integration_files(self, integration: GeneratedIntegration) -> None:
        """Save generated files to disk"""
        integration_name = integration.config.name.lower().replace(' ', '_')
        integration_dir = self.output_dir / integration_name
        integration_dir.mkdir(exist_ok=True)
        
        # Save all generated files
        files = {
            "client.py": integration.client_code,
            "server.py": integration.server_code,
            "middleware.py": integration.middleware_code,
            "examples.py": integration.usage_examples,
            "config.json": json.dumps(asdict(integration.config), indent=2)
        }
        
        for filename, content in files.items():
            filepath = integration_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        print(f"📁 Files saved to: {integration_dir}")
    
    async def run(self) -> None:
        """Main execution method"""
        print("🤖 Integration Automation Agent")
        print("=" * 50)
        print("Automate API integrations with Nango + Code Generation")
        
        try:
            # Get user selections
            selected_integrations = self.get_user_selection()
            
            print(f"\n✅ Selected {len(selected_integrations)} integrations:")
            for integration in selected_integrations:
                print(f"  • {integration.title().replace('_', ' ')}")
            
            # Process each integration
            generated_integrations = []
            
            for integration_key in selected_integrations:
                print(f"\n{'='*60}")
                print(f"Processing: {integration_key.title().replace('_', ' ')}")
                print(f"{'='*60}")
                
                try:
                    client_id, client_secret = self.get_credentials(integration_key)
                    integration = await self.create_integration(integration_key, client_id, client_secret)
                    self.save_integration_files(integration)
                    generated_integrations.append(integration)
                    
                    print(f"✅ {integration_key.title().replace('_', ' ')} integration completed!")
                    
                except Exception as e:
                    print(f"❌ Failed to create integration for {integration_key}: {e}")
                    logger.error(f"Integration creation failed: {e}")
                    continue
            
            # Generate summary
            self.generate_summary(generated_integrations)
            
        except KeyboardInterrupt:
            print("\n\n👋 Integration process cancelled by user.")
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            logger.error(f"Application error: {e}")
    
    def generate_summary(self, integrations: List[GeneratedIntegration]) -> None:
        """Generate a summary of all created integrations"""
        summary_path = self.output_dir / "integration_summary.md"
        
        summary_content = f"""# Integration Summary
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Created Integrations ({len(integrations)})

"""
        
        for integration in integrations:
            config = integration.config
            summary_content += f"""### {config.name}
- **Provider**: {config.provider}
- **Base URL**: {config.base_url}
- **Scopes**: {', '.join(config.scopes)}
- **Endpoints**: {len(config.endpoints)} available
- **Files Generated**: client.py, server.py, middleware.py, examples.py, config.json

"""
        
        summary_content += """## Next Steps

1. **Setup Environment Variables**:
   ```bash
   export NANGO_SECRET_KEY="your_nango_secret_key"
   export NANGO_PUBLIC_KEY="your_nango_public_key"
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Individual Servers**:
   ```bash
   cd generated_integrations/[integration_name]
   python server.py
   ```

4. **Use the Client**:
   ```python
   from generated_integrations.[integration_name].client import [IntegrationName]Client
   
   client = [IntegrationName]Client()
   # Follow examples in examples.py
   ```

## Support
- Check individual integration directories for specific usage examples
- Refer to Nango documentation for OAuth flow details
- Each integration includes comprehensive error handling and rate limiting
"""
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"\n📋 Integration summary saved to: {summary_path}")
        print(f"\n🎉 Successfully generated {len(integrations)} integrations!")
        print("🚀 Check the generated_integrations/ directory for all files.")

async def main():
    """Main entry point"""
    # Load environment variables
    nango_secret_key = os.getenv("NANGO_SECRET_KEY")
    nango_public_key = os.getenv("NANGO_PUBLIC_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not all([nango_secret_key, nango_public_key, openai_api_key]):
        print("❌ Missing required environment variables:")
        print("   - NANGO_SECRET_KEY")
        print("   - NANGO_PUBLIC_KEY") 
        print("   - OPENAI_API_KEY")
        return
    
    # Initialize and run the agent
    agent = IntegrationAgent(nango_secret_key, nango_public_key, openai_api_key)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())