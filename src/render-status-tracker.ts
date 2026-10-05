export enum RenderStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface RenderStatusEntry {
  renderId: string;
  bucketName: string;
  itemId: string;
  status: RenderStatus;
  progress: number;
  error?: string;
  createdAt: Date;
  updatedAt: Date;
}

export class RenderStatusTracker {
  private renders: Map<string, RenderStatusEntry> = new Map();

  register(renderId: string, bucketName: string, itemId: string): string {
    const now = new Date();
    this.renders.set(renderId, {
      renderId,
      bucketName,
      itemId,
      status: RenderStatus.PENDING,
      progress: 0,
      createdAt: now,
      updatedAt: now,
    });
    return renderId;
  }

  updateProgress(renderId: string, progress: number): void {
    const entry = this.renders.get(renderId);
    if (!entry) {
      throw new Error(`Render ${renderId} not found`);
    }

    entry.progress = progress;
    entry.updatedAt = new Date();

    if (progress >= 1.0) {
      entry.status = RenderStatus.COMPLETED;
    } else if (progress > 0) {
      entry.status = RenderStatus.IN_PROGRESS;
    }
  }

  markFailed(renderId: string, error: string): void {
    const entry = this.renders.get(renderId);
    if (!entry) {
      throw new Error(`Render ${renderId} not found`);
    }

    entry.status = RenderStatus.FAILED;
    entry.error = error;
    entry.updatedAt = new Date();
  }

  getStatus(renderId: string): RenderStatusEntry | undefined {
    return this.renders.get(renderId);
  }

  getByItem(itemId: string): RenderStatusEntry | undefined {
    for (const entry of this.renders.values()) {
      if (entry.itemId === itemId) {
        return entry;
      }
    }
    return undefined;
  }

  getAll(): RenderStatusEntry[] {
    return Array.from(this.renders.values());
  }

  getByStatus(status: RenderStatus): RenderStatusEntry[] {
    return this.getAll().filter((entry) => entry.status === status);
  }
}
