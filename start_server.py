import sys
import os

# Add user site-packages to sys.path if not present
user_site = r"C:\Users\brian\AppData\Roaming\Python\Python313\site-packages"
if user_site not in sys.path:
    sys.path.append(user_site)

try:
    import uvicorn
    from server.main import app
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    sys.exit(1)

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
