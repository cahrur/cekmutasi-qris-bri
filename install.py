#!/usr/bin/env python3
"""
Easy installation script for QRIS Mutation Scraper
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ required, found {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def create_venv():
    """Create virtual environment"""
    venv_path = Path(".venv")
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    return run_command(f"{sys.executable} -m venv .venv", "Creating virtual environment")

def get_venv_python():
    """Get path to Python in virtual environment"""
    if os.name == 'nt':  # Windows
        return ".venv\\Scripts\\python.exe"
    else:  # Unix/Linux/Mac
        return ".venv/bin/python"

def get_venv_pip():
    """Get path to pip in virtual environment"""
    if os.name == 'nt':  # Windows
        return ".venv\\Scripts\\pip.exe"
    else:  # Unix/Linux/Mac
        return ".venv/bin/pip"

def install_dependencies():
    """Install Python dependencies"""
    pip_cmd = get_venv_pip()
    
    # Upgrade pip first
    if not run_command(f"{pip_cmd} install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installing Python packages"):
        return False
    
    # Install Playwright browsers
    python_cmd = get_venv_python()
    return run_command(f"{python_cmd} -m playwright install chromium", "Installing Playwright browsers")

def setup_environment():
    """Setup environment file"""
    env_example = Path("env.example")
    env_file = Path(".env")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    if not env_example.exists():
        print("❌ env.example file not found")
        return False
    
    try:
        shutil.copy(env_example, env_file)
        print("✅ Created .env file from template")
        print("📝 Please edit .env file with your credentials")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def create_data_directory():
    """Create data directory"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print("✅ Data directory created")
    return True

def test_installation():
    """Test if installation was successful"""
    python_cmd = get_venv_python()
    return run_command(f"{python_cmd} test_dependencies.py", "Testing installation")

def print_instructions():
    """Print usage instructions"""
    activate_cmd = ".venv\\Scripts\\activate" if os.name == 'nt' else "source .venv/bin/activate"
    
    print("\n" + "="*60)
    print("🎉 Installation completed successfully!")
    print("="*60)
    print("\n📋 Next steps:")
    print(f"1. Activate virtual environment: {activate_cmd}")
    print("2. Edit .env file with your credentials")
    print("3. Run the scraper:")
    print("   - Continuous mode: python -m app")
    print("   - Single run: python -m app once")
    print("\n📁 Important files:")
    print("   - .env: Configuration file (edit with your credentials)")
    print("   - data/: Runtime data (cache, session, debug files)")
    print("   - README.md: Complete documentation")
    print("\n🔧 Test commands:")
    print("   - Test dependencies: python test_dependencies.py")
    print("   - Run tests: pytest tests/")
    print("="*60)

def main():
    """Main installation function"""
    print("🚀 QRIS Mutation Scraper - Easy Installation")
    print("="*60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create virtual environment
    if not create_venv():
        print("❌ Failed to create virtual environment")
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        print("❌ Failed to setup environment")
        sys.exit(1)
    
    # Create data directory
    if not create_data_directory():
        print("❌ Failed to create data directory")
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        print("⚠️  Installation completed but tests failed")
        print("   You may need to check dependencies manually")
    
    print_instructions()

if __name__ == "__main__":
    main()
