import axios from "axios";

// Flask dev server runs on :5000 by default (see backend/run.py).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

const client = axios.create({ baseURL: API_BASE_URL });

export async function classifyPosting({ text, sourcePlatform, userId }) {
  const response = await client.post("/classify", {
    text,
    source_platform: sourcePlatform,
    user_id: userId,
  });
  return response.data;
}

export async function getHistory({ userId, page = 1, perPage = 10 }) {
  const response = await client.get("/history", {
    params: { user_id: userId, page, per_page: perPage },
  });
  return response.data;
}

export default client;
