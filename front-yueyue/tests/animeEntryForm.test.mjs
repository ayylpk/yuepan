import test from 'node:test'
import assert from 'node:assert/strict'
import { getNextSeasonNumber, getNextEpisodeNumber, isValidPositiveInteger } from '../src/utils/animeEntryForm.ts'

test('suggests the next season number from the highest existing season', () => {
  assert.equal(getNextSeasonNumber([]), 1)
  assert.equal(getNextSeasonNumber([{ season_number: 1 }, { season_number: 3 }]), 4)
})

test('suggests the next episode number from the highest existing episode', () => {
  assert.equal(getNextEpisodeNumber([]), 1)
  assert.equal(getNextEpisodeNumber([{ episode_number: 1 }, { episode_number: 4 }]), 5)
})

test('accepts only positive integer episode numbers', () => {
  assert.equal(isValidPositiveInteger(1), true)
  assert.equal(isValidPositiveInteger('12'), true)
  assert.equal(isValidPositiveInteger(0), false)
  assert.equal(isValidPositiveInteger('-1'), false)
  assert.equal(isValidPositiveInteger('2.5'), false)
  assert.equal(isValidPositiveInteger(''), false)
})
