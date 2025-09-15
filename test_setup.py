# Simple test to verify file structure
import os

def test_setup():
    """Test that our file structure is correct"""
    required_files = [
        'main.py',
        'requirements.txt',
        'templates/index.html',
        'static/css/style.css',
        'static/js/main.js',
        'README.md'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"Missing files: {missing_files}")
        return False
    else:
        print("All required files are present!")
        return True

if __name__ == "__main__":
    test_setup()