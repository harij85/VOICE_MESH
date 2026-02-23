import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

/**
 * Default dimensions per primitive type
 * These ensure sensible visuals when dimensions aren't specified
 */
const DEFAULT_DIMENSIONS = {
  // BUG-003 FIX: rounded_slab is the primitive returned by nlu.py for phones
  // (CATEGORY_HINTS).  Without this entry createGeometry() fell through to the
  // default branch, logged a warning, and rendered with rounded_box dimensions
  // — producing the wrong shape proportions for a smartphone screen.
  rounded_slab: {
    width: 0.35,
    height: 0.75,
    depth: 0.08,
    radius: 0.04,
    segments: 8
  },
  rounded_box: {
    width: 0.5,
    height: 1.0,
    depth: 0.2,
    radius: 0.05,
    segments: 8
  },
  cylinder: {
    radius: 0.3,
    height: 1.2,
    segments: 32
  },
  sphere: {
    radius: 0.5,
    segments: 32
  },
  capsule: {
    radius: 0.25,
    height: 1.0,
    segments: 16
  },
  torus: {
    radius: 0.5,
    thickness: 0.15,
    segments: 32
  }
};

/**
 * Creates Three.js geometry from primitive type and dimensions
 * @param {string} primitive - Primitive type (rounded_box, cylinder, sphere, capsule, torus)
 * @param {object} dimensions - Optional dimension overrides
 * @returns {THREE.BufferGeometry} Generated geometry
 */
export function createGeometry(primitive = 'rounded_box', dimensions = {}) {
  const defaults = DEFAULT_DIMENSIONS[primitive] || DEFAULT_DIMENSIONS.rounded_box;
  const dims = { ...defaults, ...dimensions };

  switch (primitive) {
    case 'rounded_slab':  // BUG-003 FIX: phone/tablet slab shape
      return createRoundedBox(dims);
    case 'rounded_box':
      return createRoundedBox(dims);
    case 'cylinder':
      return createCylinder(dims);
    case 'sphere':
      return createSphere(dims);
    case 'capsule':
      return createCapsule(dims);
    case 'torus':
      return createTorus(dims);
    default:
      console.warn(`Unknown primitive: ${primitive}, falling back to rounded_box`);
      return createRoundedBox(dims);
  }
}

/**
 * Creates a rounded box (smartphone, tablet, etc.)
 */
function createRoundedBox(dims) {
  return new RoundedBoxGeometry(
    dims.width,
    dims.height,
    dims.depth,
    dims.segments || 8,
    dims.radius || 0.05
  );
}

/**
 * Creates a cylinder (bottle, can, tube, etc.)
 */
function createCylinder(dims) {
  return new THREE.CylinderGeometry(
    dims.radius,
    dims.radius,
    dims.height,
    dims.segments || 32
  );
}

/**
 * Creates a sphere (ball, globe, etc.)
 */
function createSphere(dims) {
  return new THREE.SphereGeometry(
    dims.radius,
    dims.segments || 32,
    dims.segments || 32
  );
}

/**
 * Creates a capsule (pill, rounded cylinder)
 */
function createCapsule(dims) {
  return new THREE.CapsuleGeometry(
    dims.radius,
    dims.height,
    dims.segments || 16,
    dims.segments || 16
  );
}

/**
 * Creates a torus (ring, donut, etc.)
 */
function createTorus(dims) {
  return new THREE.TorusGeometry(
    dims.radius,
    dims.thickness,
    dims.segments || 32,
    dims.segments || 32
  );
}

/**
 * Gets default dimensions for a primitive (useful for testing/debugging)
 */
export function getDefaultDimensions(primitive) {
  return DEFAULT_DIMENSIONS[primitive] || DEFAULT_DIMENSIONS.rounded_box;
}
