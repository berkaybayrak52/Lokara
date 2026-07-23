import { Controller, Get } from '@nestjs/common';
import { Public } from '../auth/public.decorator';
import type { HealthResponse } from '../contract';

@Controller('health')
export class HealthController {
  @Public()
  @Get()
  health(): HealthResponse {
    return { status: 'ok', service: 'lokara-api', timestamp: new Date().toISOString() };
  }
}
