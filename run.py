"""QueueCloud WSGI entry point for local development and Gunicorn."""
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from app import app


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
