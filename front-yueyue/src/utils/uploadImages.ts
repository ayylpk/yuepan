export interface UploadFailure<T> {
  file: T
  error: unknown
}

export interface UploadBatchResult<T> {
  succeeded: T[]
  failed: UploadFailure<T>[]
}

/** Uploads a selection serially so the existing single-file API stays reliable. */
export async function uploadImagesSequentially<T>(
  files: readonly T[],
  upload: (file: T) => Promise<void>,
): Promise<UploadBatchResult<T>> {
  const succeeded: T[] = []
  const failed: UploadFailure<T>[] = []

  for (const file of files) {
    try {
      await upload(file)
      succeeded.push(file)
    } catch (error) {
      failed.push({ file, error })
    }
  }

  return { succeeded, failed }
}
