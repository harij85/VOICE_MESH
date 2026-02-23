import { describe, it, expect } from 'vitest'
import { DEFAULT_SCENE, mergeScene } from '../sceneSpec.js'

describe('DEFAULT_SCENE', () => {
  it('should have all required fields', () => {
    expect(DEFAULT_SCENE).toHaveProperty('object')
    expect(DEFAULT_SCENE).toHaveProperty('presentation')
    expect(DEFAULT_SCENE).toHaveProperty('shape_hint')
    expect(DEFAULT_SCENE).toHaveProperty('material')
    expect(DEFAULT_SCENE).toHaveProperty('camera')
    expect(DEFAULT_SCENE).toHaveProperty('lighting')
    expect(DEFAULT_SCENE).toHaveProperty('fx')
  })

  it('should have correct default values', () => {
    expect(DEFAULT_SCENE.object.name).toBe('demo object')
    expect(DEFAULT_SCENE.object.category).toBe('generic')
    expect(DEFAULT_SCENE.camera.orbit).toBe(true)
    expect(DEFAULT_SCENE.camera.distance).toBe(2.2)
    expect(DEFAULT_SCENE.fx.alpha).toBe(1.0)
  })

  // BUG-007: JS DEFAULT_SCENE was missing the `dimensions` key under shape_hint
  it('should have dimensions in shape_hint (BUG-007)', () => {
    expect(DEFAULT_SCENE.shape_hint).toHaveProperty('dimensions')
    expect(DEFAULT_SCENE.shape_hint.dimensions).not.toBeUndefined()
  })

  it('should have all expected dimension keys', () => {
    const { dimensions } = DEFAULT_SCENE.shape_hint
    expect(dimensions).toHaveProperty('width')
    expect(dimensions).toHaveProperty('height')
    expect(dimensions).toHaveProperty('depth')
    expect(dimensions).toHaveProperty('radius')
    expect(dimensions).toHaveProperty('segments')
  })

  it('should match Python DEFAULT_SCENE dimension values', () => {
    const { dimensions } = DEFAULT_SCENE.shape_hint
    expect(dimensions.width).toBe(0.5)
    expect(dimensions.height).toBe(1.0)
    expect(dimensions.depth).toBe(0.2)
    expect(dimensions.radius).toBe(0.05)
    expect(dimensions.segments).toBe(8)
  })

  it('should have rounded_box as default primitive', () => {
    expect(DEFAULT_SCENE.shape_hint.primitive).toBe('rounded_box')
  })

  it('should have rim and env_reflect defaults in fx', () => {
    expect(DEFAULT_SCENE.fx.rim).toBe(0.0)
    expect(DEFAULT_SCENE.fx.env_reflect).toBe(0.0)
  })
})

describe('mergeScene', () => {
  it('should merge simple top-level patch', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { object: { name: 'phone', category: 'electronics' } }
    const result = mergeScene(base, patch)

    expect(result.object.name).toBe('phone')
    expect(result.object.category).toBe('electronics')
  })

  it('should preserve unmodified fields', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { material: { color: '#ff0000' } }
    const result = mergeScene(base, patch)

    expect(result.material.color).toBe('#ff0000')
    expect(result.material.preset).toBe('plastic_gloss')
    expect(result.material.roughness).toBe(0.35)
  })

  it('should merge nested camera properties', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { camera: { distance: 5.0 } }
    const result = mergeScene(base, patch)

    expect(result.camera.distance).toBe(5.0)
    expect(result.camera.orbit).toBe(true)
    expect(result.camera.fov).toBe(35)
  })

  it('should merge nested FX properties', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { fx: { bloom: 0.8 } }
    const result = mergeScene(base, patch)

    expect(result.fx.bloom).toBe(0.8)
    expect(result.fx.outline).toBe(0.12)
    expect(result.fx.alpha).toBe(1.0)
  })

  it('should handle multiple nested patches', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = {
      material: { color: '#00ff00', roughness: 0.7 },
      camera: { orbit: false },
      fx: { alpha: 0.5 }
    }
    const result = mergeScene(base, patch)

    expect(result.material.color).toBe('#00ff00')
    expect(result.material.roughness).toBe(0.7)
    expect(result.material.preset).toBe('plastic_gloss')
    expect(result.camera.orbit).toBe(false)
    expect(result.camera.distance).toBe(2.2)
    expect(result.fx.alpha).toBe(0.5)
    expect(result.fx.bloom).toBe(0.15)
  })

  it('should not mutate base scene', () => {
    const base = { ...DEFAULT_SCENE }
    const originalColor = base.material.color
    const patch = { material: { color: '#123456' } }

    mergeScene(base, patch)

    expect(base.material.color).toBe(originalColor)
  })

  it('should handle empty patch', () => {
    const base = { ...DEFAULT_SCENE }
    const result = mergeScene(base, {})

    expect(result.object.name).toBe('demo object')
    expect(result.camera.distance).toBe(2.2)
  })

  it('should handle undefined nested objects in patch', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { material: { color: '#ffffff' } }
    const result = mergeScene(base, patch)

    expect(result.object).toBeDefined()
    expect(result.camera).toBeDefined()
    expect(result.fx).toBeDefined()
  })

  it('should merge presentation properties', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { presentation: { style: 'wireframe' } }
    const result = mergeScene(base, patch)

    expect(result.presentation.style).toBe('wireframe')
    expect(result.presentation.mode).toBe('hero_on_pedestal')
  })

  it('should merge shape_hint primitive without losing features', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { shape_hint: { primitive: 'cylinder' } }
    const result = mergeScene(base, patch)

    expect(result.shape_hint.primitive).toBe('cylinder')
    expect(result.shape_hint.features).toEqual([])
  })

  it('should merge lighting properties', () => {
    const base = { ...DEFAULT_SCENE }
    const patch = { lighting: { preset: 'dramatic' } }
    const result = mergeScene(base, patch)

    expect(result.lighting.preset).toBe('dramatic')
  })

  it('should handle sequential merges', () => {
    let scene = { ...DEFAULT_SCENE }

    scene = mergeScene(scene, { material: { color: '#ff0000' } })
    expect(scene.material.color).toBe('#ff0000')

    scene = mergeScene(scene, { material: { roughness: 0.9 } })
    expect(scene.material.color).toBe('#ff0000')
    expect(scene.material.roughness).toBe(0.9)

    scene = mergeScene(scene, { camera: { distance: 3.0 } })
    expect(scene.material.color).toBe('#ff0000')
    expect(scene.camera.distance).toBe(3.0)
  })

  it('should preserve rim and env_reflect when merging other fx', () => {
    let scene = { ...DEFAULT_SCENE }
    scene = mergeScene(scene, { fx: { rim: 0.6, env_reflect: 0.3 } })
    scene = mergeScene(scene, { fx: { bloom: 0.5 } })

    expect(scene.fx.rim).toBe(0.6)
    expect(scene.fx.env_reflect).toBe(0.3)
    expect(scene.fx.bloom).toBe(0.5)
  })

  // BUG-006: shape_hint.dimensions patch dropped all other dimension keys
  describe('shape_hint.dimensions deep merge (BUG-006)', () => {
    it('should preserve existing dimensions when patching only width', () => {
      const base = {
        ...DEFAULT_SCENE,
        shape_hint: {
          primitive: 'rounded_box',
          features: [],
          dimensions: { width: 0.5, height: 1.0, depth: 0.2, radius: 0.05, segments: 8 }
        }
      }
      const patch = { shape_hint: { dimensions: { width: 1.5 } } }
      const result = mergeScene(base, patch)

      expect(result.shape_hint.dimensions.width).toBe(1.5)
      // BUG: without fix these were dropped
      expect(result.shape_hint.dimensions.height).toBe(1.0)
      expect(result.shape_hint.dimensions.depth).toBe(0.2)
      expect(result.shape_hint.dimensions.radius).toBe(0.05)
      expect(result.shape_hint.dimensions.segments).toBe(8)
    })

    it('should preserve primitive when patching only dimensions', () => {
      const base = { ...DEFAULT_SCENE }
      const patch = { shape_hint: { dimensions: { height: 2.0 } } }
      const result = mergeScene(base, patch)

      expect(result.shape_hint.primitive).toBe('rounded_box')
      expect(result.shape_hint.dimensions.height).toBe(2.0)
      expect(result.shape_hint.dimensions.width).toBe(0.5) // preserved
    })

    it('should allow patching multiple dimensions independently', () => {
      let scene = { ...DEFAULT_SCENE }

      scene = mergeScene(scene, { shape_hint: { dimensions: { width: 1.0 } } })
      scene = mergeScene(scene, { shape_hint: { dimensions: { height: 2.0 } } })

      expect(scene.shape_hint.dimensions.width).toBe(1.0)   // preserved from first patch
      expect(scene.shape_hint.dimensions.height).toBe(2.0)  // from second patch
      expect(scene.shape_hint.dimensions.depth).toBe(0.2)   // from default
    })

    it('should work when base shape_hint has no dimensions', () => {
      const base = {
        ...DEFAULT_SCENE,
        shape_hint: { primitive: 'cylinder', features: [] }  // no dimensions key
      }
      const patch = { shape_hint: { dimensions: { radius: 0.5, height: 1.5 } } }
      const result = mergeScene(base, patch)

      expect(result.shape_hint.dimensions.radius).toBe(0.5)
      expect(result.shape_hint.dimensions.height).toBe(1.5)
    })

    it('should produce empty dimensions object when neither base nor patch has dimensions', () => {
      const base = {
        ...DEFAULT_SCENE,
        shape_hint: { primitive: 'sphere', features: [] }
      }
      const patch = { shape_hint: { primitive: 'cylinder' } }
      const result = mergeScene(base, patch)

      // dimensions should be an object (possibly empty), not undefined
      expect(result.shape_hint.dimensions).toBeDefined()
      expect(typeof result.shape_hint.dimensions).toBe('object')
    })
  })
})
