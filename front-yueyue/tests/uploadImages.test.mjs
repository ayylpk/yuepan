import test from 'node:test'
import assert from 'node:assert/strict'
import { uploadImagesSequentially } from '../src/utils/uploadImages.ts'

test('uploads selected images one at a time in selection order', async () => {
  const files = ['one.png', 'two.png', 'three.png']
  const calls = []
  let active = 0
  let maxActive = 0

  const result = await uploadImagesSequentially(files, async (file) => {
    active += 1
    maxActive = Math.max(maxActive, active)
    calls.push(file)
    await Promise.resolve()
    active -= 1
  })

  assert.deepEqual(calls, files)
  assert.equal(maxActive, 1)
  assert.deepEqual(result, { succeeded: files, failed: [] })
})

test('continues uploading remaining images after one upload fails', async () => {
  const files = ['one.png', 'two.png', 'three.png']
  const calls = []
  const failure = new Error('network error')

  const result = await uploadImagesSequentially(files, async (file) => {
    calls.push(file)
    if (file === 'two.png') throw failure
  })

  assert.deepEqual(calls, files)
  assert.deepEqual(result.succeeded, ['one.png', 'three.png'])
  assert.deepEqual(result.failed, [{ file: 'two.png', error: failure }])
})
