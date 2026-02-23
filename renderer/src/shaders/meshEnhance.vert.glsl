// Enhanced mesh vertex shader — passes world-space data to fragment shader.
// Used with THREE.ShaderMaterial (not Raw), so Three.js injects:
//   modelMatrix, modelViewMatrix, projectionMatrix, normalMatrix, cameraPosition

varying vec3 vWorldNormal;
varying vec3 vWorldPosition;
varying vec3 vViewDir;

void main() {
  // World-space normal (not view-space — we need it for environment reflection)
  vWorldNormal = normalize(mat3(modelMatrix) * normal);

  // World-space position
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vWorldPosition = worldPos.xyz;

  // View direction (world-space, from surface to camera)
  vViewDir = normalize(cameraPosition - worldPos.xyz);

  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
