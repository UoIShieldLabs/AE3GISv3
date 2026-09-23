import type { ImagesSlice, SliceCreator } from '../types';

// Image statuses come from GET /images; features/images/imagePolling keeps
// them fresh. Components read them through `useImageStatus`.
export const createImagesSlice: SliceCreator<ImagesSlice> = (set) => ({
  images: null,
  imagesError: null,
  setImagesReport: (images, error = null) => set({ images, imagesError: error }, false, 'setImagesReport'),
});
