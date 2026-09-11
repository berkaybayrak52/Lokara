import { describe, expect, it } from 'vitest';

import { MeterWorkspaceResponseSchema } from './contracts';
import { previewResponse } from './demo-preview';

describe('meter workspace preview', () => {
  it('satisfies the same response contract as the live meter workspace', () => {
    const response = previewResponse('/a/acc_demo_lokara/meter-workspace');

    expect(response).toBeDefined();
    const workspace = MeterWorkspaceResponseSchema.parse(response);
    const meters = workspace.buildings.flatMap((building) => [
      ...building.buildingMeters,
      ...building.units.flatMap((unit) => unit.meters),
    ]);
    expect(meters.length).toBeGreaterThan(0);
    for (const meter of meters) {
      if (meter.deviceType !== 'GAS_METER') {
        expect(meter.gasConversion).toBeNull();
      }
    }
  });
});
