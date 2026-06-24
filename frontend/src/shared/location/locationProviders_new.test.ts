/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { requestBrowserLocation, startBrowserWatch, stopBrowserWatch } from './browserProvider'
import * as config from './config'
import { createSnapshot } from './snapshot'
import { requestTelegramLocation } from './telegramProvider'

const position = (latitude = 54.9, longitude = 20.4): GeolocationPosition => ({
  coords: {
    accuracy: 12, altitude: null, altitudeAccuracy: null,
    heading: null, latitude, longitude, speed: null,
    toJSON: () => ({}),
  },
  timestamp: Date.now(),
  toJSON: () => ({}),
})

describe('location providers', () => {
  afterEach(() => vi.restoreAllMocks())

  it('returns Telegram native coordinates with accuracy_new', async () => {
    const manager = {
      isInited: false, isLocationAvailable: true, isAccessRequested: true, isAccessGranted: true,
      init: vi.fn((callback?: () => void) => callback?.()),
      getLocation: vi.fn((callback) => callback({
        latitude: 54.9, longitude: 20.4, horizontal_accuracy: 8,
        altitude: 4, course: 20, speed: 1,
      })),
      openSettings: vi.fn(),
    }
    const result = await requestTelegramLocation({
      isVersionAtLeast: () => true, LocationManager: manager,
    })
    expect('source' in result && result.source).toBe('telegram_native')
    expect('coordinates' in result && result.coordinates.accuracy).toBe(8)
  })

  it('reports Telegram denial and unsupported old version_new', async () => {
    const denied = await requestTelegramLocation({
      isVersionAtLeast: () => true,
      LocationManager: {
        isInited: true, isLocationAvailable: true, isAccessRequested: true,
        isAccessGranted: false, init: vi.fn(), getLocation: (callback) => callback(null),
        openSettings: vi.fn(),
      },
    })
    expect('status' in denied && denied.status).toBe('denied')
    const old = await requestTelegramLocation({ isVersionAtLeast: () => false })
    expect('status' in old && old.status).toBe('unavailable')
  })

  it('handles browser granted, denied and timeout_new', async () => {
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      getCurrentPosition: (success: PositionCallback) => success(position()),
    } })
    expect('source' in await requestBrowserLocation()).toBe(true)
    const error = (code: number) => ({ code, PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 })
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      getCurrentPosition: (_success: PositionCallback, failure: PositionErrorCallback) => failure(error(1) as GeolocationPositionError),
    } })
    const denied = await requestBrowserLocation()
    expect('status' in denied ? denied.status : '').toBe('denied')
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      getCurrentPosition: (_success: PositionCallback, failure: PositionErrorCallback) => failure(error(3) as GeolocationPositionError),
    } })
    const timeout = await requestBrowserLocation()
    expect('status' in timeout ? timeout.status : '').toBe('timeout')
  })

  it('does not call browser geolocation in insecure context_new', async () => {
    const getCurrentPosition = vi.fn()
    vi.spyOn(config, 'isSecureLocationContext').mockReturnValue(false)
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { getCurrentPosition } })
    const result = await requestBrowserLocation()
    expect('status' in result && result.status).toBe('insecure')
    expect(getCurrentPosition).not.toHaveBeenCalled()
  })

  it('clears browser watcher_new', () => {
    const clearWatch = vi.fn()
    Object.defineProperty(window, 'isSecureContext', { configurable: true, value: true })
    Object.defineProperty(navigator, 'geolocation', { configurable: true, value: {
      watchPosition: (success: PositionCallback) => { success(position()); return 7 },
      clearWatch,
    } })
    const id = startBrowserWatch({ onLocation: vi.fn(), onError: vi.fn() })
    stopBrowserWatch(id)
    expect(clearWatch).toHaveBeenCalledWith(7)
  })

  it('marks old snapshots stale_new', () => {
    const snapshot = createSnapshot({
      latitude: 54.9, longitude: 20.4, accuracy: 10,
      altitude: null, course: null, speed: null,
    }, 'browser', 1)
    expect(snapshot.stale).toBe(true)
  })
})
