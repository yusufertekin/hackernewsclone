FROM node:12
# Create app directory
RUN apt-get update && apt-get install -y \
  vim \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /web
COPY package*.json ./
RUN npm install
COPY . .
