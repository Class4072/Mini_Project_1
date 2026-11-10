import axios from 'axios';
import { env } from '../config/env';

// apiBaseUrl 이 비어 있으면 상대경로(/api/...)로 요청 → 개발 시 Vite proxy 를 탄다.
export const apiClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});
