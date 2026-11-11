FROM python:3.12-slim
WORKDIR /app
COPY agent.py .
ENV PORT=10000
EXPOSE 10000
USER nobody
CMD ["python", "-u", "agent.py"]
