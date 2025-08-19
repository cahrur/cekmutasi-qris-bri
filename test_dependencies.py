#!/usr/bin/env python3
"""
Test script to check if all dependencies are properly installed
"""
import sys
import subprocess

def check_and_install_dependencies():
    """Check and install missing dependencies"""
    
    required_packages = [
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0", 
        "httpx>=0.25.0",
        "tenacity>=8.2.0",
        "pytz>=2023.3",
        "python-dateutil>=2.8.2",
        "aiosqlite>=0.19.0",
        "beautifulsoup4>=4.12.0"
    ]
    
    print("🔍 Checking dependencies...")
    
    missing_packages = []
    
    # Check each package
    for package in required_packages:
        package_name = package.split(">=")[0]
        try:
            __import__(package_name.replace("-", "_"))
            print(f"✅ {package_name} - OK")
        except ImportError:
            print(f"❌ {package_name} - MISSING")
            missing_packages.append(package)
    
    # Special check for playwright browser
    try:
        from playwright.async_api import async_playwright
        print("✅ playwright.async_api - OK")
    except ImportError:
        print("❌ playwright.async_api - MISSING")
        missing_packages.append("playwright")
    
    if missing_packages:
        print(f"\n💡 Missing packages: {', '.join(missing_packages)}")
        print("📦 Installing missing packages...")
        
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"✅ Installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {package}: {e}")
                return False
        
        # Install playwright browsers if playwright was installed
        if any("playwright" in pkg for pkg in missing_packages):
            print("🎭 Installing Playwright browsers...")
            try:
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                print("✅ Playwright browsers installed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install Playwright browsers: {e}")
                return False
    
    print("\n🎉 All dependencies are installed!")
    return True

def test_imports():
    """Test all critical imports"""
    print("\n🧪 Testing imports...")
    
    try:
        from app.dependencies import check_dependencies
        check_dependencies()
        print("✅ All imports working correctly")
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 50)
    print("🚀 QRIS Scraper Dependency Checker")
    print("=" * 50)
    
    if not check_and_install_dependencies():
        print("\n❌ Dependency installation failed!")
        sys.exit(1)
    
    if not test_imports():
        print("\n❌ Import tests failed!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎯 Ready to run! You can now use:")
    print("   python -m app")
    print("=" * 50)

if __name__ == "__main__":
    main()
