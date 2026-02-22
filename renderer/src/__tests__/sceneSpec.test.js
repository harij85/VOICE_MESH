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

  it('should merge shape_hint properties', () => {
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
})
