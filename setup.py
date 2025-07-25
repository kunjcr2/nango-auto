#!/usr/bin/env python3
"""
Setup script for Integration Automation Agent
Handles installation, configuration, and initialization
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
import argparse

class IntegrationSetup:
    """Setup manager for the integration automation system"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.config_path = self.project_root / "config.json"
        self.env_path = self.project_root / ".env"
        
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            print("❌ Python 3.8 or higher is required")
            print(f"Current version: {sys.version}")
            return False
        print(f"✅ Python version: {sys.version.split()[0]}")
        return True
    
    def create_virtual_environment(self) -> bool:
        """Create Python virtual environment"""
        try:
            if self.venv_path.exists():
                print("📁 Virtual environment already exists")
                return True
            
            print("🔧 Creating virtual environment...")
            subprocess.run([
                sys.executable, "-m", "venv", str(self.venv_path)
            ], check=True)
            
            print("✅ Virtual environment created")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    def get_pip_command(self) -> str:
        """Get the correct pip command for the virtual environment"""
        if sys.platform == "win32":
            return str(self.venv_path / "Scripts" / "pip")
        else:
            return str(self.venv_path / "bin" / "pip")
    
    def install_dependencies(self) -> bool:
        """Install required dependencies"""
        try:
            pip_cmd = self.get_pip_command()
            requirements_file = self.project_root / "requirements.txt"
            
            if not requirements_file.exists():
                print("❌ requirements.txt not found")
                return False
            
            print("📦 Installing dependencies...")
            subprocess.run([
                pip_cmd, "install", "-r", str(requirements_file)
            ], check=True)
            
            print("✅ Dependencies installed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def create_project_structure(self) -> bool:
        """Create necessary project directories"""
        try:
            directories = [
                "generated_integrations",
                "logs",
                "templates",
                "tests",
                "config"
            ]
            
            for directory in directories:
                dir_path = self.project_root / directory
                dir_path.mkdir(exist_ok=True)
                print(f"📁 Created directory: {directory}")
            
            # Create __init__.py files for Python packages
            init_files = [
                "generated_integrations/__init__.py",
                "tests/__init__.py"
            ]
            
            for init_file in init_files:
                init_path = self.project_root / init_file
                if not init_path.exists():
                    init_path.touch()
                    print(f"📄 Created: {init_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create project structure: {e}")
            return False
    
    def setup_configuration(self) -> bool:
        """Setup configuration files"""
        try:
            # Create default configuration
            default_config = {
                "version": "1.0.0",
                "project_name": "Integration Automation Agent",
                "default_settings": {
                    "cache_ttl": 300,
                    "rate_limit_per_minute": 60,
                    "max_retries": 3,
                    "timeout_seconds": 30
                },
                "supported_providers": [
                    "slack", "github", "google_drive", "notion", 
                    "hubspot", "salesforce", "discord", "shopify", 
                    "trello", "airtable"
                ],
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "file": "logs/integration_agent.log"
                }
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            print("✅ Configuration file created")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup configuration: {e}")
            return False
    
    def setup_environment_file(self) -> bool:
        """Setup environment variables file"""
        try:
            if self.env_path.exists():
                print("📄 .env file already exists")
                return True
            
            # Copy from .env.example
            env_example = self.project_root / ".env.example"
            if env_example.exists():
                shutil.copy(env_example, self.env_path)
                print("✅ Environment file created from template")
            else:
                # Create basic .env file
                env_content = """# Nango Configuration
NANGO_SECRET_KEY=your_nango_secret_key_here
NANGO_PUBLIC_KEY=your_nango_public_key_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
"""
                with open(self.env_path, 'w') as f:
                    f.write(env_content)
                print("✅ Basic environment file created")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup environment file: {e}")
            return False
    
    def install_development_tools(self) -> bool:
        """Install additional development tools"""
        try:
            pip_cmd = self.get_pip_command()
            
            dev_packages = [
                "black",      # Code formatting
                "flake8",     # Linting
                "pytest",     # Testing
                "mypy",       # Type checking
                "pre-commit"  # Git hooks
            ]
            
            print("🛠️ Installing development tools...")
            subprocess.run([
                pip_cmd, "install"
            ] + dev_packages, check=True)
            
            print("✅ Development tools installed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install development tools: {e}")
            return False
    
    def setup_git_hooks(self) -> bool:
        """Setup pre-commit git hooks"""
        try:
            # Create .pre-commit-config.yaml
            pre_commit_config = """repos:
  - repo: https://github.com/psf/black
    rev: '23.9.1'
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/pycqa/flake8
    rev: '6.1.0'
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: 'v1.6.1'
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
"""
            
            pre_commit_path = self.project_root / ".pre-commit-config.yaml"
            with open(pre_commit_path, 'w') as f:
                f.write(pre_commit_config)
            
            # Install pre-commit hooks
            if shutil.which("git") and (self.project_root / ".git").exists():
                python_cmd = str(self.venv_path / "bin" / "python") if sys.platform != "win32" else str(self.venv_path / "Scripts" / "python")
                subprocess.run([
                    python_cmd, "-m", "pre_commit", "install"
                ], cwd=self.project_root, check=True)
                print("✅ Git hooks installed")
            else:
                print("⚠️ Git repository not found, skipping git hooks")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup git hooks: {e}")
            return False
    
    def create_startup_scripts(self) -> bool:
        """Create startup scripts for easy execution"""
        try:
            # Create startup script for Unix-like systems
            if sys.platform != "win32":
                startup_script = self.project_root / "start.sh"
                script_content = f"""#!/bin/bash
# Integration Automation Agent Startup Script

set -e

echo "🚀 Starting Integration Automation Agent"

# Activate virtual environment
source {self.venv_path}/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the application
python main.py "$@"
"""
                with open(startup_script, 'w') as f:
                    f.write(script_content)
                
                # Make executable
                startup_script.chmod(0o755)
                print("✅ Unix startup script created")
            
            # Create startup script for Windows
            windows_script = self.project_root / "start.bat"
            bat_content = f"""@echo off
REM Integration Automation Agent Startup Script

echo 🚀 Starting Integration Automation Agent

REM Activate virtual environment
call "{self.venv_path}\\Scripts\\activate.bat"

REM Start the application
python main.py %*
"""
            with open(windows_script, 'w') as f:
                f.write(bat_content)
            
            print("✅ Windows startup script created")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create startup scripts: {e}")
            return False
    
    def validate_setup(self) -> bool:
        """Validate the setup"""
        try:
            print("🔍 Validating setup...")
            
            # Check virtual environment
            if not self.venv_path.exists():
                print("❌ Virtual environment not found")
                return False
            
            # Check dependencies
            pip_cmd = self.get_pip_command()
            result = subprocess.run([
                pip_cmd, "list", "--format=json"
            ], capture_output=True, text=True, check=True)
            
            installed_packages = {pkg['name'].lower() for pkg in json.loads(result.stdout)}
            required_packages = {
                'fastapi', 'uvicorn', 'aiohttp', 'langchain', 
                'openai', 'structlog', 'pydantic'
            }
            
            missing_packages = required_packages - installed_packages
            if missing_packages:
                print(f"❌ Missing packages: {missing_packages}")
                return False
            
            # Check configuration files
            required_files = [self.config_path, self.env_path]
            for file_path in required_files:
                if not file_path.exists():
                    print(f"❌ Missing file: {file_path}")
                    return False
            
            print("✅ Setup validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Setup validation failed: {e}")
            return False
    
    def print_next_steps(self):
        """Print next steps for the user"""
        print("\n" + "="*60)
        print("🎉 SETUP COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n📋 Next Steps:")
        print("1. Edit the .env file with your API keys")
        print("   - Add your Nango secret and public keys")
        print("   - Add your OpenAI API key")
        print("\n2. Test the installation:")
        if sys.platform == "win32":
            print("   start.bat --help")
        else:
            print("   ./start.sh --help")
        
        print("\n3. Run the integration agent:")
        if sys.platform == "win32":
            print("   start.bat")
        else:
            print("   ./start.sh")
        
        print("\n4. Access the documentation:")
        print("   - Check the generated_integrations/ directory")
        print("   - Read usage_examples.py for code examples")
        print("   - API docs at http://localhost:8000/docs (when server is running)")
        
        print("\n📚 Additional Resources:")
        print("   - Nango Documentation: https://docs.nango.dev")
        print("   - FastAPI Documentation: https://fastapi.tiangolo.com")
        print("   - LangChain Documentation: https://docs.langchain.com")
        
        print("\n🔧 Development Commands:")
        print("   - Format code: python -m black .")
        print("   - Lint code: python -m flake8 .")
        print("   - Run tests: python -m pytest")
        print("   - Type check: python -m mypy .")
    
    def run_full_setup(self, install_dev_tools: bool = False) -> bool:
        """Run the complete setup process"""
        print("🚀 Integration Automation Agent Setup")
        print("="*50)
        
        steps = [
            ("Checking Python version", self.check_python_version),
            ("Creating virtual environment", self.create_virtual_environment),
            ("Installing dependencies", self.install_dependencies),
            ("Creating project structure", self.create_project_structure),
            ("Setting up configuration", self.setup_configuration),
            ("Setting up environment file", self.setup_environment_file),
            ("Creating startup scripts", self.create_startup_scripts),
        ]
        
        if install_dev_tools:
            steps.extend([
                ("Installing development tools", self.install_development_tools),
                ("Setting up git hooks", self.setup_git_hooks),
            ])
        
        steps.append(("Validating setup", self.validate_setup))
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if not step_func():
                print(f"❌ Setup failed at: {step_name}")
                return False
        
        self.print_next_steps()
        return True

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup Integration Automation Agent")
    parser.add_argument(
        "--dev", 
        action="store_true", 
        help="Install development tools and setup git hooks"
    )
    parser.add_argument(
        "--clean", 
        action="store_true", 
        help="Clean existing setup before installing"
    )
    
    args = parser.parse_args()
    
    setup = IntegrationSetup()
    
    # Clean existing setup if requested
    if args.clean:
        print("🧹 Cleaning existing setup...")
        if setup.venv_path.exists():
            shutil.rmtree(setup.venv_path)
            print("✅ Removed virtual environment")
    
    # Run setup
    success = setup.run_full_setup(install_dev_tools=args.dev)
    
    if success:
        print("\n🎉 Setup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()