FROM node:20-slim

WORKDIR /app

# Copy the full frontend directory first, then install.
# This avoids the COPY glob problem where a missing lockfile
# can cause the build to fail before reaching the RUN step.
COPY frontend/ ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
