import { getHeaders } from './index.mjs';
import assert from 'node:assert';

function verifyDynamicHeaders() {
  console.log('Verifying dynamic header generation...');

  const headers1 = getHeaders();
  const headers2 = getHeaders();

  const apps1 = JSON.parse(headers1.apps);
  const apps2 = JSON.parse(headers2.apps);

  const deviceId1 = apps1.device_id;
  const deviceId2 = apps2.device_id;

  const correlationId1 = headers1['x-correlation-id'];
  const correlationId2 = headers2['x-correlation-id'];

  console.log('Run 1 Device ID:', deviceId1);
  console.log('Run 2 Device ID:', deviceId2);
  console.log('Run 1 Correlation ID:', correlationId1);
  console.log('Run 2 Correlation ID:', correlationId2);

  assert.notStrictEqual(deviceId1, deviceId2, 'Device IDs should be different');
  assert.notStrictEqual(correlationId1, correlationId2, 'Correlation IDs should be different');

  // Also verify they are valid UUIDs (basic check)
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  assert.ok(uuidRegex.test(deviceId1), 'Device ID 1 is not a valid UUID');
  assert.ok(uuidRegex.test(correlationId1), 'Correlation ID 1 is not a valid UUID');

  console.log('✅ Verification successful: Headers are dynamically generated and use valid UUIDs.');
}

try {
  verifyDynamicHeaders();
} catch (error) {
  console.error('❌ Verification failed:', error.message);
  process.exit(1);
}
