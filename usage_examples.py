"""
Usage examples for API integrations
Demonstrates how to use the generated integration code
"""

import asyncio
import os
from typing import Dict, Any, List
from datetime import datetime

# Import the generated client and server (will be replaced by actual imports)
# from generated_integrations.slack.client import SlackClient
# from generated_integrations.slack.server import SlackServer

class IntegrationUsageExamples:
    """
    Comprehensive usage examples for API integrations
    """
    
    def __init__(self, connection_id: str, nango_public_key: str):
        self.connection_id = connection_id
        self.nango_public_key = nango_public_key
        
    # ==========================================
    # BASIC SETUP AND INITIALIZATION
    # ==========================================
    
    async def basic_setup_example(self):
        """
        Example: Basic client setup and initialization
        """
        print("🚀 Basic Setup Example")
        print("=" * 50)
        
        # Initialize client (replace with actual client class)
        # client = SlackClient(
        #     connection_id=self.connection_id,
        #     nango_public_key=self.nango_public_key,
        #     provider_config_key="slack"
        # )
        
        # Using async context manager (recommended)
        # async with client:
        #     # Test connection
        #     is_connected = await client.test_connection()
        #     print(f"✅ Connection test: {'Success' if is_connected else 'Failed'}")
        #     
        #     # Get client stats
        #     stats = client.get_stats()
        #     print(f"📊 Client stats: {stats}")
        
        print("Basic setup completed!\n")
    
    # ==========================================
    # AUTHENTICATION FLOW
    # ==========================================
    
    async def oauth_flow_example(self):
        """
        Example: Complete OAuth authentication flow
        """
        print("🔐 OAuth Flow Example")
        print("=" * 50)
        
        # Step 1: Initiate OAuth flow
        print("1. Initiating OAuth flow...")
        
        # In a web application, you would redirect user to this URL:
        oauth_initiate_url = f"http://localhost:8000/oauth/initiate?connection_id={self.connection_id}"
        print(f"   OAuth URL: {oauth_initiate_url}")
        
        # Step 2: User completes OAuth on provider's site
        print("2. User completes OAuth on provider's website...")
        
        # Step 3: Handle callback (automatically handled by server)
        print("3. OAuth callback handled by server")
        
        # Step 4: Verify connection
        print("4. Verifying connection...")
        
        # Test API call to verify OAuth success
        # async with SlackClient(...) as client:
        #     response = await client.get_user_info()
        #     if response.success:
        #         print("✅ OAuth flow completed successfully!")
        #         print(f"   User: {response.data.get('name', 'Unknown')}")
        #     else:
        #         print(f"❌ OAuth verification failed: {response.error_message}")
        
        print("OAuth flow example completed!\n")
    
    # ==========================================
    # BASIC API OPERATIONS
    # ==========================================
    
    async def basic_api_operations_example(self):
        """
        Example: Basic CRUD operations
        """
        print("📝 Basic API Operations Example")
        print("=" * 50)
        
        # Replace with actual client operations
        examples = {
            "Slack": {
                "send_message": {
                    "method": "POST",
                    "endpoint": "/chat.postMessage",
                    "data": {
                        "channel": "#general",
                        "text": "Hello from Integration Agent!",
                        "username": "Integration Bot"
                    }
                },
                "list_channels": {
                    "method": "GET",
                    "endpoint": "/conversations.list",
                    "params": {"types": "public_channel,private_channel"}
                },
                "get_user_info": {
                    "method": "GET",
                    "endpoint": "/users.info",
                    "params": {"user": "U1234567890"}
                }
            },
            "GitHub": {
                "list_repos": {
                    "method": "GET",
                    "endpoint": "/user/repos",
                    "params": {"sort": "updated", "per_page": 10}
                },
                "create_issue": {
                    "method": "POST",
                    "endpoint": "/repos/{owner}/{repo}/issues",
                    "data": {
                        "title": "Integration Test Issue",
                        "body": "This issue was created by the Integration Agent",
                        "labels": ["integration", "automated"]
                    }
                },
                "get_user": {
                    "method": "GET",
                    "endpoint": "/user"
                }
            }
        }
        
        for provider, operations in examples.items():
            print(f"\n{provider} Operations:")
            for operation_name, config in operations.items():
                print(f"  • {operation_name}:")
                print(f"    Method: {config['method']}")
                print(f"    Endpoint: {config['endpoint']}")
                if 'data' in config:
                    print(f"    Data: {config['data']}")
                if 'params' in config:
                    print(f"    Params: {config['params']}")
        
        print("\nBasic operations example completed!\n")
    
    # ==========================================
    # ERROR HANDLING
    # ==========================================
    
    async def error_handling_example(self):
        """
        Example: Comprehensive error handling
        """
        print("⚠️ Error Handling Example")
        print("=" * 50)
        
        error_scenarios = [
            {
                "name": "Rate Limit Exceeded",
                "description": "Handling 429 Too Many Requests",
                "code": """
# Rate limiting is handled automatically by the client
async with client:
    for i in range(100):  # Rapid requests
        response = await client.send_message(
            channel="#test",
            text=f"Message {i}"
        )
        
        if not response.success:
            if response.status_code == 429:
                print(f"Rate limited, waiting...")
                # Client automatically retries with backoff
            else:
                print(f"Error: {response.error_message}")
"""
            },
            {
                "name": "Invalid Authentication",
                "description": "Handling 401 Unauthorized",
                "code": """
# Token refresh is handled automatically
async with client:
    response = await client.get_user_info()
    
    if not response.success:
        if response.status_code == 401:
            print("Authentication failed - token may be invalid")
            # Client will attempt token refresh automatically
        else:
            print(f"Other error: {response.error_message}")
"""
            },
            {
                "name": "Network Errors",
                "description": "Handling connection issues",
                "code": """
import asyncio
from aiohttp import ClientError

async with client:
    try:
        response = await client.list_channels()
        print(f"Success: {response.data}")
        
    except ClientError as e:
        print(f"Network error: {e}")
        # Implement retry logic if needed
        
    except Exception as e:
        print(f"Unexpected error: {e}")
"""
            }
        ]
        
        for scenario in error_scenarios:
            print(f"\n{scenario['name']}:")
            print(f"Description: {scenario['description']}")
            print("Code example:")
            print(scenario['code'])
        
        print("Error handling examples completed!\n")
    
    # ==========================================
    # ADVANCED USAGE PATTERNS
    # ==========================================
    
    async def advanced_patterns_example(self):
        """
        Example: Advanced usage patterns
        """
        print("🚀 Advanced Usage Patterns")
        print("=" * 50)
        
        patterns = [
            {
                "name": "Batch Operations",
                "description": "Processing multiple items efficiently",
                "code": """
async def batch_send_messages(client, messages):
    tasks = []
    
    for message in messages:
        task = client.send_message(
            channel=message['channel'],
            text=message['text']
        )
        tasks.append(task)
    
    # Execute all requests concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successes = []
    failures = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failures.append({'index': i, 'error': str(result)})
        elif result.success:
            successes.append({'index': i, 'response': result.data})
        else:
            failures.append({'index': i, 'error': result.error_message})
    
    return {'successes': successes, 'failures': failures}
"""
            },
            {
                "name": "Webhook Handling",
                "description": "Processing incoming webhooks",
                "code": """
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

@app.post("/webhook/{connection_id}")
async def handle_webhook(
    connection_id: str,
    payload: dict,
    background_tasks: BackgroundTasks
):
    # Process webhook asynchronously
    background_tasks.add_task(process_webhook_data, connection_id, payload)
    return {"status": "accepted"}

async def process_webhook_data(connection_id: str, payload: dict):
    async with client:
        if payload['event'] == 'message':
            # Auto-respond to messages
            await client.send_message(
                channel=payload['channel'],
                text=f"Received: {payload['text']}"
            )
"""
            },
            {
                "name": "Data Synchronization",
                "description": "Syncing data between systems",
                "code": """
async def sync_data_between_systems(source_client, dest_client):
    # Get data from source
    source_response = await source_client.list_items()
    
    if not source_response.success:
        raise Exception(f"Failed to fetch source data: {source_response.error_message}")
    
    # Transform data for destination
    transformed_items = []
    for item in source_response.data.get('items', []):
        transformed_item = {
            'name': item['title'],
            'description': item['body'],
            'tags': item.get('labels', [])
        }
        transformed_items.append(transformed_item)
    
    # Batch create in destination
    for item in transformed_items:
        response = await dest_client.create_item(item)
        if not response.success:
            print(f"Failed to create item: {response.error_message}")
        else:
            print(f"Created item: {item['name']}")
"""
            }
        ]
        
        for pattern in patterns:
            print(f"\n{pattern['name']}:")
            print(f"Description: {pattern['description']}")
            print("Code example:")
            print(pattern['code'])
        
        print("Advanced patterns examples completed!\n")
    
    # ==========================================
    # PERFORMANCE OPTIMIZATION
    # ==========================================
    
    async def performance_optimization_example(self):
        """
        Example: Performance optimization techniques
        """
        print("⚡ Performance Optimization Example")
        print("=" * 50)
        
        optimizations = [
            {
                "name": "Connection Pooling",
                "description": "Reusing HTTP connections",
                "tip": "Always use async context managers to properly manage connections"
            },
            {
                "name": "Request Batching",
                "description": "Combining multiple requests",
                "tip": "Use asyncio.gather() for concurrent requests, but respect rate limits"
            },
            {
                "name": "Response Caching",
                "description": "Caching frequently accessed data",
                "tip": "Enable response caching for GET requests that don't change frequently"
            },
            {
                "name": "Rate Limit Optimization",
                "description": "Maximizing throughput within limits",
                "tip": "Monitor rate limit headers and adjust request timing accordingly"
            }
        ]
        
        for opt in optimizations:
            print(f"\n{opt['name']}:")
            print(f"Description: {opt['description']}")
            print(f"💡 Tip: {opt['tip']}")
        
        # Performance monitoring example
        print("\nPerformance Monitoring:")
        print("""
async def monitor_performance(client):
    start_time = time.time()
    
    # Make multiple requests
    tasks = [client.get_user_info() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Calculate metrics
    success_count = sum(1 for r in results if r.success)
    error_count = len(results) - success_count
    
    print(f"Total requests: {len(results)}")
    print(f"Successful: {success_count}")
    print(f"Errors: {error_count}")
    print(f"Duration: {duration:.2f}s")
    print(f"Requests/second: {len(results)/duration:.2f}")
    
    # Get client stats
    stats = client.get_stats()
    print(f"Client stats: {stats}")
""")
        
        print("Performance optimization examples completed!\n")
    
    # ==========================================
    # REAL-WORLD USE CASES
    # ==========================================
    
    async def real_world_use_cases_example(self):
        """
        Example: Real-world integration scenarios
        """
        print("🌟 Real-World Use Cases")
        print("=" * 50)
        
        use_cases = [
            {
                "name": "Automated Customer Support",
                "description": "Auto-respond to support tickets",
                "workflow": [
                    "1. Receive webhook when new ticket created",
                    "2. Analyze ticket content using AI",
                    "3. Generate appropriate response",
                    "4. Post response via API",
                    "5. Update ticket status"
                ]
            },
            {
                "name": "Content Synchronization",
                "description": "Sync content across platforms",
                "workflow": [
                    "1. Monitor for new content in source",
                    "2. Transform content for target platform",
                    "3. Upload/create content in destination",
                    "4. Update metadata and links",
                    "5. Log synchronization results"
                ]
            },
            {
                "name": "Notification Aggregation",
                "description": "Aggregate notifications from multiple sources",
                "workflow": [
                    "1. Fetch notifications from all sources",
                    "2. Deduplicate and prioritize",
                    "3. Format for unified dashboard",
                    "4. Send digest to users",
                    "5. Mark notifications as processed"
                ]
            },
            {
                "name": "Data Analytics Pipeline",
                "description": "Extract data for analytics",
                "workflow": [
                    "1. Extract data from APIs",
                    "2. Transform and clean data",
                    "3. Load into data warehouse",
                    "4. Generate reports",
                    "5. Send alerts on anomalies"
                ]
            }
        ]
        
        for use_case in use_cases:
            print(f"\n{use_case['name']}:")
            print(f"Description: {use_case['description']}")
            print("Workflow:")
            for step in use_case['workflow']:
                print(f"  {step}")
        
        print("\nReal-world use cases examples completed!\n")
    
    # ==========================================
    # MAIN EXECUTION
    # ==========================================
    
    async def run_all_examples(self):
        """
        Run all usage examples
        """
        print("🤖 Integration Usage Examples")
        print("=" * 60)
        print(f"Connection ID: {self.connection_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        examples = [
            self.basic_setup_example,
            self.oauth_flow_example,
            self.basic_api_operations_example,
            self.error_handling_example,
            self.advanced_patterns_example,
            self.performance_optimization_example,
            self.real_world_use_cases_example
        ]
        
        for example in examples:
            try:
                await example()
            except Exception as e:
                print(f"❌ Error running {example.__name__}: {e}")
        
        print("🎉 All examples completed!")

# ==========================================
# QUICK START GUIDE
# ==========================================

def print_quick_start_guide():
    """
    Print a quick start guide for users
    """
    print("""
    🚀 QUICK START GUIDE
    ==================
    
    1. Setup Environment:
       export NANGO_PUBLIC_KEY="your_public_key"
       export CONNECTION_ID="your_connection_id"
    
    2. Install Dependencies:
       pip install -r requirements.txt
    
    3. Run OAuth Flow:
       python -c "
       import asyncio
       from usage_examples import IntegrationUsageExamples
       examples = IntegrationUsageExamples('your_connection_id', 'your_nango_key')
       asyncio.run(examples.oauth_flow_example())
       "
    
    4. Test Basic Operations:
       python -c "
       import asyncio
       from usage_examples import IntegrationUsageExamples
       examples = IntegrationUsageExamples('your_connection_id', 'your_nango_key')
       asyncio.run(examples.basic_api_operations_example())
       "
    
    5. Start Server:
       python server.py
    
    6. Access API Documentation:
       http://localhost:8000/docs
    
    📚 For more examples, run:
       python usage_examples.py
    """)

# ==========================================
# TESTING UTILITIES
# ==========================================

class IntegrationTester:
    """
    Utility class for testing integrations
    """
    
    def __init__(self, client_class, connection_id: str, nango_public_key: str):
        self.client_class = client_class
        self.connection_id = connection_id
        self.nango_public_key = nango_public_key
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive integration tests
        """
        results = {
            'connection_test': False,
            'auth_test': False,
            'api_tests': {},
            'error_handling_tests': {},
            'performance_tests': {}
        }
        
        try:
            # Test connection
            # async with self.client_class(
            #     connection_id=self.connection_id,
            #     nango_public_key=self.nango_public_key
            # ) as client:
            #     results['connection_test'] = await client.test_connection()
            #     
            #     # Test API endpoints
            #     # Add specific API tests here
            #     
            #     # Test error scenarios
            #     # Add error handling tests here
            #     
            #     # Test performance
            #     # Add performance tests here
            
            pass
            
        except Exception as e:
            results['test_error'] = str(e)
        
        return results

# Main execution
if __name__ == "__main__":
    import sys
    
    # Get environment variables
    connection_id = os.getenv("CONNECTION_ID", "default_connection")
    nango_public_key = os.getenv("NANGO_PUBLIC_KEY")
    
    if not nango_public_key:
        print("❌ NANGO_PUBLIC_KEY environment variable is required")
        print_quick_start_guide()
        sys.exit(1)
    
    # Run examples
    examples = IntegrationUsageExamples(connection_id, nango_public_key)
    
    if len(sys.argv) > 1:
        # Run specific example
        example_name = sys.argv[1]
        example_method = getattr(examples, f"{example_name}_example", None)
        
        if example_method:
            asyncio.run(example_method())
        else:
            print(f"❌ Example '{example_name}' not found")
            print("Available examples:")
            methods = [method for method in dir(examples) if method.endswith('_example')]
            for method in methods:
                print(f"  • {method.replace('_example', '')}")
    else:
        # Run all examples
        asyncio.run(examples.run_all_examples())