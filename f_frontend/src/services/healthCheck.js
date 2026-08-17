import axios from 'axios';
import logger from '../utils/logger';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

/**
 * Checks the backend health endpoint /health
 * @returns {Promise<{ status: string, details: object }>}
 */
export async function checkBackendHealth() {
  try {
    const response = await axios.get(`${API_BASE_URL}/health`, {
      timeout: 5000,
    });
    logger.info('Health check response received', response.data);
    return {
      isHealthy: response.data.status === 'healthy',
      data: response.data,
    };
  } catch (error) {
    logger.error('Failed to reach backend health endpoint', error);
    return {
      isHealthy: false,
      error: error.message || 'Service Unavailable',
      data: error.response?.data || null,
    };
  }
}
