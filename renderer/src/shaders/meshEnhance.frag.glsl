// Enhanced mesh fragment shader — Fresnel rim glow + fake environment reflection.
// Matches existing scene lighting (key at 5,5,5 + fill at -3,2,4).

uniform vec3  u_color;
uniform float u_roughness;
uniform float u_alpha;
uniform float u_rimIntensity;
uniform vec3  u_rimColor;
uniform float u_envReflect;

varying vec3 vWorldNormal;
varying vec3 vWorldPosition;
varying vec3 vViewDir;

// Fake sky gradient for environment reflection
vec3 fakeEnvMap(vec3 dir) {
  float y = dir.y * 0.5 + 0.5; // remap -1..1 to 0..1
  vec3 sky    = vec3(0.6, 0.7, 0.9);
  vec3 ground = vec3(0.15, 0.12, 0.1);
  return mix(ground, sky, smoothstep(0.0, 1.0, y));
}

void main() {
  vec3 N = normalize(vWorldNormal);
  vec3 V = normalize(vViewDir);

  // --- Lighting ---
  // Key light (5, 5, 5)
  vec3 L1 = normalize(vec3(5.0, 5.0, 5.0) - vWorldPosition);
  float diff1 = max(dot(N, L1), 0.0);
  vec3 H1 = normalize(L1 + V);
  float spec1 = pow(max(dot(N, H1), 0.0), mix(8.0, 128.0, 1.0 - u_roughness));

  // Fill light (-3, 2, 4)
  vec3 L2 = normalize(vec3(-3.0, 2.0, 4.0) - vWorldPosition);
  float diff2 = max(dot(N, L2), 0.0);
  vec3 H2 = normalize(L2 + V);
  float spec2 = pow(max(dot(N, H2), 0.0), mix(8.0, 128.0, 1.0 - u_roughness));

  // Combine lighting
  float ambient = 0.15;
  vec3 diffuse = u_color * (ambient + 1.0 * diff1 + 0.5 * diff2);
  vec3 specular = vec3(1.0) * (0.6 * spec1 + 0.3 * spec2) * (1.0 - u_roughness);

  vec3 col = diffuse + specular;

  // --- Fresnel rim glow ---
  float fresnel = pow(1.0 - max(dot(V, N), 0.0), 3.0);
  col += fresnel * u_rimIntensity * u_rimColor;

  // --- Fake environment reflection ---
  vec3 reflDir = reflect(-V, N);
  vec3 envColor = fakeEnvMap(reflDir);
  col = mix(col, envColor, fresnel * u_envReflect);

  // --- Reinhard tonemap (matches raymarch shader) ---
  col = col / (col + vec3(1.0));

  gl_FragColor = vec4(col, clamp(u_alpha, 0.0, 1.0));
}
