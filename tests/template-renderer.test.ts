import { RemotionClient, RenderParams } from '../src/remotion-client';

jest.mock('../src/remotion-client');

const MockedRemotionClient = RemotionClient as jest.MockedClass<typeof RemotionClient>;

describe('TemplateRenderer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('renderBatch', () => {
    it('should render multiple videos from template with different variables', async () => {
      const mockRender = jest.fn().mockResolvedValue({ renderId: 'r1', bucketName: 'b1' });
      MockedRemotionClient.prototype.render = mockRender;

      const { TemplateRenderer } = await import('../src/template-renderer');
      const renderer = new TemplateRenderer({
        client: new MockedRemotionClient({
          region: 'us-east-1',
          functionName: 'fn',
          serveUrl: 'https://serve.example.com',
        }),
        composition: 'MyComp',
        baseInputProps: { theme: 'dark' },
      });

      const items = [
        { id: '1', variables: { title: 'Video 1' } },
        { id: '2', variables: { title: 'Video 2' } },
      ];

      const results = await renderer.renderBatch(items);

      expect(mockRender).toHaveBeenCalledTimes(2);
      expect(mockRender).toHaveBeenNthCalledWith(1, {
        composition: 'MyComp',
        inputProps: { theme: 'dark', title: 'Video 1' },
      });
      expect(mockRender).toHaveBeenNthCalledWith(2, {
        composition: 'MyComp',
        inputProps: { theme: 'dark', title: 'Video 2' },
      });
      expect(results).toHaveLength(2);
      expect(results[0].id).toBe('1');
      expect(results[1].id).toBe('2');
    });

    it('should merge base inputProps with item variables', async () => {
      const mockRender = jest.fn().mockResolvedValue({ renderId: 'r1', bucketName: 'b1' });
      MockedRemotionClient.prototype.render = mockRender;

      const { TemplateRenderer } = await import('../src/template-renderer');
      const renderer = new TemplateRenderer({
        client: new MockedRemotionClient({
          region: 'us-east-1',
          functionName: 'fn',
          serveUrl: 'https://serve.example.com',
        }),
        composition: 'Comp',
        baseInputProps: { theme: 'dark', lang: 'en' },
      });

      await renderer.renderBatch([{ id: '1', variables: { title: 'T1' } }]);

      expect(mockRender).toHaveBeenCalledWith({
        composition: 'Comp',
        inputProps: { theme: 'dark', lang: 'en', title: 'T1' },
      });
    });

    it('should handle empty batch', async () => {
      const mockRender = jest.fn();
      MockedRemotionClient.prototype.render = mockRender;

      const { TemplateRenderer } = await import('../src/template-renderer');
      const renderer = new TemplateRenderer({
        client: new MockedRemotionClient({
          region: 'us-east-1',
          functionName: 'fn',
          serveUrl: 'https://serve.example.com',
        }),
        composition: 'Comp',
        baseInputProps: {},
      });

      const results = await renderer.renderBatch([]);

      expect(results).toEqual([]);
      expect(mockRender).not.toHaveBeenCalled();
    });
  });
});
