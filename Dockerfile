# Use an official Python image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy all files from your repo to the container
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (Optional)
ENV TOKEN=${DISCORD_BOT_TOKEN}

# Run the bot
CMD ["python", "main.py"]
