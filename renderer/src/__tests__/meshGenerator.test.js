/**
 * Tests for meshGenerator.js
 *
 * BUG-003: `rounded_slab` primitive was missing — nlu.py returns it for phones
 * but createGeometry() fell through to the default branch and silently rendered
 * a rounded_box with wrong proportions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Hoisted mock state ───────────────────────────────────────────────────────
// vi.mock factories are hoisted to the top of the file by the compiler, so
// they cannot reference variables declared with const/let in the module scope.
// Use vi.hoisted() to define state that is available at hoist time.

const { mockInstances } = vi.hoisted(() => {
  return { mockInstances: [] }
})

vi.mock('three', () => ({
  CylinderGeometry: class {
    constructor(...args) { mockInstances.push({ name: 'CylinderGeometry', args }) }
  },
  SphereGeometry: class {
    constructor(...args) { mockInstances.push({ name: 'SphereGeometry', args }) }
  },
  CapsuleGeometry: class {
    constructor(...args) { mockInstances.push({ name: 'CapsuleGeometry', args }) }
  },
  TorusGeometry: class {
    constructor(...args) { mockInstances.push({ name: 'TorusGeometry', args }) }
  }
}))

vi.mock('three/examples/jsm/geometries/RoundedBoxGeometry.js', () => ({
  RoundedBoxGeometry: class {
    constructor(...args) { mockInstances.push({ name: 'RoundedBoxGeometry', args }) }
  }
}))

import { createGeometry, getDefaultDimensions } from '../meshGenerator.js'

// ── Helper ───────────────────────────────────────────────────────────────────

function lastInstance() {
  return mockInstances[mockInstances.length - 1]
}

beforeEach(() => {
  mockInstances.length = 0
})

// ── Tests ────────────────────────────────────────────────────────────────────

describe('createGeometry', () => {
  describe('rounded_box', () => {
    it('creates a RoundedBoxGeometry', () => {
      createGeometry('rounded_box')
      expect(lastInstance().name).toBe('RoundedBoxGeometry')
    })

    it('uses default dimensions when none provided', () => {
      createGeometry('rounded_box')
      const [w, h, d] = lastInstance().args
      expect(w).toBe(0.5)
      expect(h).toBe(1.0)
      expect(d).toBe(0.2)
    })

    it('accepts dimension overrides', () => {
      createGeometry('rounded_box', { width: 1.0, height: 2.0, depth: 0.5 })
      const [w, h, d] = lastInstance().args
      expect(w).toBe(1.0)
      expect(h).toBe(2.0)
      expect(d).toBe(0.5)
    })
  })

  // BUG-003: rounded_slab was missing from the switch statement
  describe('rounded_slab (BUG-003)', () => {
    it('creates a RoundedBoxGeometry (phone slab shape)', () => {
      createGeometry('rounded_slab')
      expect(lastInstance().name).toBe('RoundedBoxGeometry')
    })

    it('uses phone-appropriate default dimensions (portrait, thin)', () => {
      const defaults = getDefaultDimensions('rounded_slab')
      // Phone slab should be portrait: width < height
      expect(defaults.width).toBeLessThan(defaults.height)
      // Should be thin (depth much less than height)
      expect(defaults.depth).toBeLessThan(defaults.height * 0.5)
    })

    it('rounded_slab defaults differ from rounded_box defaults', () => {
      const slabDims = getDefaultDimensions('rounded_slab')
      const boxDims  = getDefaultDimensions('rounded_box')
      // Phone slab should have different proportions than generic rounded box
      expect(slabDims.width).not.toBe(boxDims.width)
      expect(slabDims.depth).not.toBe(boxDims.depth)
    })

    it('accepts dimension overrides', () => {
      createGeometry('rounded_slab', { width: 0.4, height: 0.8, depth: 0.1 })
      const [w, h, d] = lastInstance().args
      expect(w).toBe(0.4)
      expect(h).toBe(0.8)
      expect(d).toBe(0.1)
    })

    it('does NOT trigger the unknown-primitive console.warn branch', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      createGeometry('rounded_slab')
      expect(consoleSpy).not.toHaveBeenCalled()
      consoleSpy.mockRestore()
    })
  })

  describe('cylinder', () => {
    it('creates a CylinderGeometry', () => {
      createGeometry('cylinder')
      expect(lastInstance().name).toBe('CylinderGeometry')
    })

    it('uses default radius and height', () => {
      createGeometry('cylinder')
      const defaults = getDefaultDimensions('cylinder')
      const [topR, botR, h] = lastInstance().args
      expect(topR).toBe(defaults.radius)
      expect(botR).toBe(defaults.radius)
      expect(h).toBe(defaults.height)
    })
  })

  describe('sphere', () => {
    it('creates a SphereGeometry', () => {
      createGeometry('sphere')
      expect(lastInstance().name).toBe('SphereGeometry')
    })

    it('uses default radius', () => {
      createGeometry('sphere')
      const defaults = getDefaultDimensions('sphere')
      const [r] = lastInstance().args
      expect(r).toBe(defaults.radius)
    })
  })

  describe('capsule', () => {
    it('creates a CapsuleGeometry', () => {
      createGeometry('capsule')
      expect(lastInstance().name).toBe('CapsuleGeometry')
    })
  })

  describe('torus', () => {
    it('creates a TorusGeometry', () => {
      createGeometry('torus')
      expect(lastInstance().name).toBe('TorusGeometry')
    })

    it('uses default radius and thickness', () => {
      createGeometry('torus')
      const defaults = getDefaultDimensions('torus')
      const [r, t] = lastInstance().args
      expect(r).toBe(defaults.radius)
      expect(t).toBe(defaults.thickness)
    })
  })

  describe('unknown primitive fallback', () => {
    it('falls back to RoundedBoxGeometry with a console warning', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      createGeometry('not_a_real_primitive')
      expect(lastInstance().name).toBe('RoundedBoxGeometry')
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Unknown primitive')
      )
      consoleSpy.mockRestore()
    })
  })

  describe('default primitive', () => {
    it('defaults to rounded_box when no primitive provided', () => {
      createGeometry()
      expect(lastInstance().name).toBe('RoundedBoxGeometry')
    })
  })
})

describe('getDefaultDimensions', () => {
  it('returns rounded_box defaults for unknown primitive', () => {
    const result = getDefaultDimensions('not_real')
    const boxDefaults = getDefaultDimensions('rounded_box')
    expect(result).toEqual(boxDefaults)
  })

  it('returns rounded_slab defaults (BUG-003)', () => {
    const result = getDefaultDimensions('rounded_slab')
    expect(result).toBeDefined()
    expect(result.width).toBeDefined()
    expect(result.height).toBeDefined()
    expect(result.depth).toBeDefined()
  })

  it('returns cylinder defaults', () => {
    const result = getDefaultDimensions('cylinder')
    expect(result.radius).toBeDefined()
    expect(result.height).toBeDefined()
    expect(result.segments).toBeDefined()
  })

  it('returns torus defaults with thickness', () => {
    const result = getDefaultDimensions('torus')
    expect(result.thickness).toBeDefined()
    expect(result.radius).toBeDefined()
  })

  it('all primitives have segment counts', () => {
    for (const prim of ['rounded_box', 'rounded_slab', 'cylinder', 'sphere', 'capsule', 'torus']) {
      const dims = getDefaultDimensions(prim)
      expect(dims.segments).toBeGreaterThanOrEqual(8)
    }
  })
})
