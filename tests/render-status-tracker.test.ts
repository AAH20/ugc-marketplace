import { RenderStatusTracker, RenderStatus } from '../src/render-status-tracker';

describe('RenderStatusTracker', () => {
  let tracker: RenderStatusTracker;

  beforeEach(() => {
    tracker = new RenderStatusTracker();
  });

  describe('register', () => {
    it('should register a new render with pending status', () => {
      const id = tracker.register('render-1', 'bucket-1', 'item-1');

      expect(id).toBe('render-1');
      const status = tracker.getStatus('render-1');
      expect(status).toEqual({
        renderId: 'render-1',
        bucketName: 'bucket-1',
        itemId: 'item-1',
        status: RenderStatus.PENDING,
        progress: 0,
        createdAt: expect.any(Date),
        updatedAt: expect.any(Date),
      });
    });
  });

  describe('updateProgress', () => {
    it('should update render progress', () => {
      tracker.register('r1', 'b1', 'item-1');
      tracker.updateProgress('r1', 0.5);

      const status = tracker.getStatus('r1');
      expect(status?.status).toBe(RenderStatus.IN_PROGRESS);
      expect(status?.progress).toBe(0.5);
    });

    it('should mark as completed when progress reaches 1.0', () => {
      tracker.register('r1', 'b1', 'item-1');
      tracker.updateProgress('r1', 1.0);

      const status = tracker.getStatus('r1');
      expect(status?.status).toBe(RenderStatus.COMPLETED);
    });

    it('should throw for unknown render', () => {
      expect(() => tracker.updateProgress('unknown', 0.5)).toThrow(
        'Render unknown not found'
      );
    });
  });

  describe('markFailed', () => {
    it('should mark render as failed with error', () => {
      tracker.register('r1', 'b1', 'item-1');
      tracker.markFailed('r1', 'Connection timeout');

      const status = tracker.getStatus('r1');
      expect(status?.status).toBe(RenderStatus.FAILED);
      expect(status?.error).toBe('Connection timeout');
    });
  });

  describe('getByItem', () => {
    it('should find render by item id', () => {
      tracker.register('r1', 'b1', 'item-1');
      tracker.register('r2', 'b2', 'item-2');

      const status = tracker.getByItem('item-2');
      expect(status?.renderId).toBe('r2');
    });
  });

  describe('getAll', () => {
    it('should return all tracked renders', () => {
      tracker.register('r1', 'b1', 'item-1');
      tracker.register('r2', 'b2', 'item-2');

      const all = tracker.getAll();
      expect(all).toHaveLength(2);
    });
  });

  describe('getByStatus', () => {
    it('should filter renders by status', () => {
      tracker.register('r1', 'b1', 'item-1');
      tracker.register('r2', 'b2', 'item-2');
      tracker.updateProgress('r1', 1.0);

      const completed = tracker.getByStatus(RenderStatus.COMPLETED);
      expect(completed).toHaveLength(1);
      expect(completed[0].renderId).toBe('r1');
    });
  });
});
