precision highp float;

uniform float u_time;
uniform vec2  u_resolution;
uniform vec3  u_color;
uniform float u_roughness;
uniform float u_distance;
uniform float u_orbit;
uniform float u_cameraAngle;
uniform float u_cameraElevation;
uniform float u_shapeType; // 0=box, 1=cylinder, 2=sphere, 3=capsule, 4=torus
uniform float u_outline;
uniform float u_bloom;
uniform float u_alpha;

// ---- SDF helpers ----
float sdRoundBox(vec3 p, vec3 b, float r) {
  vec3 q = abs(p) - b;
  return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}

float sdCylinder(vec3 p, float h, float r) {
  vec2 d = abs(vec2(length(p.xz), p.y)) - vec2(r, h);
  return min(max(d.x, d.y), 0.0) + length(max(d, 0.0));
}

float sdSphere(vec3 p, float r) {
  return length(p) - r;
}

float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
  vec3 pa = p - a, ba = b - a;
  float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
  return length(pa - ba * h) - r;
}

float sdTorus(vec3 p, vec2 t) {
  vec2 q = vec2(length(p.xz) - t.x, p.y);
  return length(q) - t.y;
}

// Scene distance function - returns distance based on shape type
float sceneSDF(vec3 p) {
  if (u_shapeType < 0.5) {
    // Rounded box (phone/remote)
    return sdRoundBox(p, vec3(0.55, 0.12, 0.03), 0.06);
  } else if (u_shapeType < 1.5) {
    // Cylinder (bottle)
    return sdCylinder(p, 0.5, 0.15);
  } else if (u_shapeType < 2.5) {
    // Sphere
    return sdSphere(p, 0.3);
  } else if (u_shapeType < 3.5) {
    // Capsule (headset)
    return sdCapsule(p, vec3(0.0, -0.3, 0.0), vec3(0.0, 0.3, 0.0), 0.15);
  } else {
    // Torus
    return sdTorus(p, vec2(0.3, 0.1));
  }
}

vec3 calcNormal(vec3 p) {
  vec2 e = vec2(0.001, 0.0);
  float d = sceneSDF(p);
  vec3 n = d - vec3(
    sceneSDF(p - vec3(e.x, e.y, e.y)),
    sceneSDF(p - vec3(e.y, e.x, e.y)),
    sceneSDF(p - vec3(e.y, e.y, e.x))
  );
  return normalize(n);
}

float raymarch(vec3 ro, vec3 rd, out vec3 pHit) {
  float t = 0.0;
  for (int i = 0; i < 96; i++) {
    vec3 p = ro + rd * t;
    float d = sceneSDF(p);
    if (d < 0.001) { pHit = p; return t; }
    t += d * 0.8;
    if (t > 10.0) break;
  }
  pHit = ro + rd * t;
  return -1.0;
}

float softShadow(vec3 ro, vec3 rd) {
  float res = 1.0;
  float t = 0.02;
  for (int i = 0; i < 48; i++) {
    vec3 p = ro + rd * t;
    float d = sceneSDF(p);
    res = min(res, 10.0 * d / t);
    t += clamp(d, 0.02, 0.2);
    if (res < 0.01 || t > 6.0) break;
  }
  return clamp(res, 0.0, 1.0);
}

void main() {
  vec2 uv = (2.0 * gl_FragCoord.xy - u_resolution.xy) / min(u_resolution.x, u_resolution.y);

  // Camera
  float ang = u_orbit > 0.5 ? (u_time * 0.35) : u_cameraAngle;
  float elev = u_cameraElevation;
  vec3 ro = vec3(
    cos(ang) * cos(elev) * u_distance,
    sin(elev) * u_distance,
    sin(ang) * cos(elev) * u_distance
  );
  vec3 ta = vec3(0.0, 0.0, 0.0);

  vec3 ww = normalize(ta - ro);
  vec3 uu = normalize(cross(vec3(0.0, 1.0, 0.0), ww));
  vec3 vv = cross(ww, uu);
  vec3 rd = normalize(uv.x * uu + uv.y * vv + 1.7 * ww);

  vec3 pHit;
  float t = raymarch(ro, rd, pHit);

  if (t <= 0.0) {
    gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
    return;
  }

  // Background
  vec3 col = vec3(0.02, 0.02, 0.03) + 0.08 * vec3(uv.y + 0.4);

  if (t > 0.0) {
    vec3 n = calcNormal(pHit);

    // Lighting
    vec3 ldir = normalize(vec3(0.6, 1.0, 0.2));
    float ndl = max(dot(n, ldir), 0.0);
    float sh  = softShadow(pHit + n * 0.01, ldir);

    vec3 diff = u_color * ndl * sh;

    // Simple spec controlled by roughness
    vec3 h = normalize(ldir - rd);
    float specPow = mix(128.0, 16.0, clamp(u_roughness, 0.0, 1.0));
    float spec = pow(max(dot(n, h), 0.0), specPow) * sh;

    col = diff + spec;

    // Outline (edge based on view-normal)
    float rim = 1.0 - max(dot(n, -rd), 0.0);
    col += u_outline * pow(rim, 2.2);

    // Fake bloom
    col += u_bloom * vec3(spec) * 0.8;
  }

  // Tonemap-ish
  col = col / (col + vec3(1.0));
  gl_FragColor = vec4(col, clamp(u_alpha, 0.0, 1.0));
}