FROM python:3.11-slim-bookworm

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install python-telegram-bot[job-queue]

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD ["python", "bot.py"]
