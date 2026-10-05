import { RemotionClient } from '../src/remotion-client';
import { renderMediaOnLambda, getRenderProgress } from '@remotion/lambda';

jest.mock('@remotion/lambda');

const mockRenderMediaOnLambda = renderMediaOnLambda as jest.MockedFunction<typeof renderMediaOnLambda>;
const mockGetRenderProgress = getRenderProgress as jest.MockedFunction<typeof getRenderProgress>;

describe('RemotionClient', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('render', () => {
    it('should call renderMediaOnLambda with correct parameters', async () => {
      mockRenderMediaOnLambda.mockResolvedValue({
        renderId: 'test-render-id',
        bucketName: 'test-bucket',
        cloudWatchLogs: 'https://logs.example.com',
        cloudWatchMainLogs: 'https://logs.example.com/main',
        lambdaInsightsLogs: 'https://logs.example.com/insights',
        folderInS3Console: 'https://console.aws.amazon.com/s3',
        progressJsonInConsole: 'https://console.aws.amazon.com/cloudwatch',
      });

      const client = new RemotionClient({
        region: 'us-east-1',
        functionName: 'test-function',
        serveUrl: 'https://test.remotion.dev',
      });

      const result = await client.render({
        composition: 'MyComp',
        inputProps: { title: 'Hello' },
      });

      expect(mockRenderMediaOnLambda).toHaveBeenCalledWith(
        expect.objectContaining({
          composition: 'MyComp',
          inputProps: { title: 'Hello' },
        })
      );
      expect(result.renderId).toBe('test-render-id');
      expect(result.bucketName).toBe('test-bucket');
    });

    it('should pass credentials when provided', async () => {
      mockRenderMediaOnLambda.mockResolvedValue({
        renderId: 'r1',
        bucketName: 'b1',
        cloudWatchLogs: 'https://logs.example.com',
        cloudWatchMainLogs: 'https://logs.example.com/main',
        lambdaInsightsLogs: 'https://logs.example.com/insights',
        folderInS3Console: 'https://console.aws.amazon.com/s3',
        progressJsonInConsole: 'https://console.aws.amazon.com/cloudwatch',
      });

      const client = new RemotionClient({
        region: 'us-east-1',
        functionName: 'fn',
        serveUrl: 'https://serve.example.com',
        credentials: {
          accessKeyId: 'AKID',
          secretAccessKey: 'SECRET',
          endpoint: 'https://s3.example.com',
        },
      });

      await client.render({ composition: 'C', inputProps: {} });

      expect(mockRenderMediaOnLambda).toHaveBeenCalledWith(
        expect.objectContaining({
          credentials: {
            accessKeyId: 'AKID',
            secretAccessKey: 'SECRET',
            endpoint: 'https://s3.example.com',
          },
        })
      );
    });
  });

  describe('poll', () => {
    it('should call getRenderProgress with correct parameters', async () => {
      const mockProgress = {
        overallProgress: 0.5,
        done: false,
        encodingStatus: null,
        outputFile: undefined,
        errors: [],
      } as any;

      mockGetRenderProgress.mockResolvedValue(mockProgress);

      const client = new RemotionClient({
        region: 'us-east-1',
        functionName: 'fn',
        serveUrl: 'https://serve.example.com',
      });

      const result = await client.poll('render-123', 'bucket-456');

      expect(mockGetRenderProgress).toHaveBeenCalledWith(
        expect.objectContaining({
          renderId: 'render-123',
          bucketName: 'bucket-456',
          region: 'us-east-1',
          functionName: 'fn',
        })
      );
      expect(result.overallProgress).toBe(0.5);
    });
  });

  describe('download', () => {
    it('should throw error when render is not complete', async () => {
      mockGetRenderProgress.mockResolvedValue({
        overallProgress: 0.3,
        done: false,
        encodingStatus: null,
        outputFile: undefined,
        errors: [],
      } as any);

      const client = new RemotionClient({
        region: 'us-east-1',
        functionName: 'fn',
        serveUrl: 'https://serve.example.com',
      });

      await expect(
        client.download('r1', 'b1', '/tmp/out.mp4')
      ).rejects.toThrow('Render not complete');
    });
  });
});
