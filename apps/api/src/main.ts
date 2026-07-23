import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { loadEnv } from './env';

async function bootstrap(): Promise<void> {
  const env = loadEnv();
  const app = await NestFactory.create(AppModule);
  app.enableCors({ origin: env.webOrigin });
  app.enableShutdownHooks();
  await app.listen(env.port);
  console.log(`lokara-api listening on http://localhost:${env.port}`);
}

void bootstrap();
