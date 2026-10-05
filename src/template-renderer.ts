import { RemotionClient, RenderParams } from './remotion-client';

export interface TemplateRendererConfig {
  client: RemotionClient;
  composition: string;
  baseInputProps: Record<string, unknown>;
}

export interface BatchItem {
  id: string;
  variables: Record<string, unknown>;
}

export interface BatchResult {
  id: string;
  renderId: string;
  bucketName: string;
}

export class TemplateRenderer {
  private client: RemotionClient;
  private composition: string;
  private baseInputProps: Record<string, unknown>;

  constructor(config: TemplateRendererConfig) {
    this.client = config.client;
    this.composition = config.composition;
    this.baseInputProps = config.baseInputProps;
  }

  async renderBatch(items: BatchItem[]): Promise<BatchResult[]> {
    const results: BatchResult[] = [];

    for (const item of items) {
      const inputProps = { ...this.baseInputProps, ...item.variables };
      const result = await this.client.render({
        composition: this.composition,
        inputProps,
      });

      results.push({
        id: item.id,
        renderId: result.renderId,
        bucketName: result.bucketName,
      });
    }

    return results;
  }
}
