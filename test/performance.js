import { check } from 'k6';
import http from 'k6/http';

export const options = {
  thresholds: {
    http_req_failed: ['rate<0.01'], // http errors should be less than 1%
    http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
  },
  scenarios: {
    root: {
      executor: 'constant-vus',
      exec: 'root',
      vus: 50,
      duration: '15s',
    }
  }
}


export function root() {
  if (__ENV.ENVIRONMENT_URL) {
    
    const res = http.get(`${__ENV.ENVIRONMENT_URL}`);
    check(res, {
      'Link status is 200': (r) => res.status === 307
    });
  } else {
    console.error('ENVIRONMENT_URL is not set');
  }
}
