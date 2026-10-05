import {
  renderMediaOnLambda,
  getRenderProgress,
  type RenderMediaOnLambdaOutput,
  type RenderProgress,
  type AwsRegion,
} from '@remotion/lambda';

export interface RemotionClientConfig {
  region: AwsRegion;
  functionName: string;
  serveUrl: string;
  credentials?: {
    accessKeyId: string;
    secretAccessKey: string;
    endpoint: string;
  };
}

export interface RenderParams {
  composition: string;
  inputProps: Record<string, unknown>;
  codec?: 'h264' | 'h265' | 'vp8' | 'vp9' | 'prores' | 'gif';
  imageFormat?: 'png' | 'jpeg';
  jpegQuality?: number;
  crf?: number;
  scale?: number;
  frameRange?: [number, number];
  envVariables?: Record<string, string>;
  maxRetries?: number;
  timeoutInMilliseconds?: number;
  privacy?: 'public' | 'private';
  outName?: string;
}

export interface RenderResult {
  renderId: string;
  bucketName: string;
}

export class RemotionClient {
  private config: RemotionClientConfig;

  constructor(config: RemotionClientConfig) {
    this.config = config;
  }

  async render(params: RenderParams): Promise<RenderResult> {
    const result: RenderMediaOnLambdaOutput = await renderMediaOnLambda({
      region: this.config.region,
      functionName: this.config.functionName,
      serveUrl: this.config.serveUrl,
      composition: params.composition,
      inputProps: params.inputProps,
      codec: params.codec ?? 'h264',
      imageFormat: params.imageFormat,
      jpegQuality: params.jpegQuality,
      crf: params.crf,
      scale: params.scale,
      frameRange: params.frameRange,
      envVariables: params.envVariables,
      maxRetries: params.maxRetries,
      privacy: params.privacy,
      outName: params.outName,
      ...(this.config.credentials && {
        credentials: this.config.credentials,
      }),
    });

    return {
      renderId: result.renderId,
      bucketName: result.bucketName,
    };
  }

  async poll(renderId: string, bucketName: string): Promise<RenderProgress> {
    return getRenderProgress({
      renderId,
      bucketName,
      region: this.config.region,
      functionName: this.config.functionName,
      ...(this.config.credentials && {
        s3OutputProvider: this.config.credentials,
      }),
    });
  }

  async download(
    renderId: string,
    bucketName: string,
    outputPath: string
  ): Promise<string> {
    const progress = await this.poll(renderId, bucketName);

    if (progress.done && progress.outputFile) {
      const fs = await import('fs');
      const https = await import('https');
      const http = await import('http');
      const url = progress.outputFile;
      const mod = url.startsWith('https') ? https : http;

      return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(outputPath);
        mod.get(url, (response) => {
          response.pipe(file);
          file.on('finish', () => {
            file.close();
            resolve(outputPath);
          });
        }).on('error', (err) => {
          fs.unlink(outputPath, () => {});
          reject(err);
        });
      });
    }

    throw new Error(`Render not complete. Status: ${progress.overallProgress}`);
  }
}
